"""
MCP 客户端 - 管理 MCP Server 进程和工具调用

负责：
1. 启动/停止 MCP Server 进程
2. 获取 Server 提供的所有工具
3. 调用 MCP 工具
4. 状态追踪和错误处理
"""
import asyncio
import json
import os
from typing import Any

from tools.base import BaseTool
from utils.console import Console


class MCPTool(BaseTool):
    """
    MCP 工具适配器 - 把 MCP Server 提供的工具包装成 BaseTool 接口

    这样 LLM 调用 MCP 工具就和调用普通工具完全一样了。
    """

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        server_name: str,
        client: "MCPClient",
    ):
        self._name = name
        self._description = description
        self._input_schema = input_schema
        self._server_name = server_name
        self._client = client

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"[MCP:{self._server_name}] {self._description}"

    @property
    def input_schema(self) -> dict[str, Any]:
        return self._input_schema

    @property
    def client(self) -> "MCPClient":
        return self._client

    async def run(self, args: dict[str, Any]) -> str:
        """执行 MCP 工具调用"""
        try:
            result = await self._client.call_tool(self._name, args)
            return result
        except Exception as e:
            return f"MCP 工具执行失败: {type(e).__name__}: {e}"

    def __str__(self) -> str:
        return f"<MCPTool {self._name} ({self._server_name})>"

    def __repr__(self) -> str:
        return self.__str__()


class MCPClient:
    """
    MCP Server 客户端 - 管理一个 MCP Server 进程的生命周期
    """

    def __init__(self, name: str, command: str, args: list[str] | None = None):
        """
        初始化 MCP 客户端

        Args:
            name: Server 名称（如 "filesystem"）
            command: 启动命令（如 "npx"）
            args: 命令参数（如 ["@modelcontextprotocol/server-filesystem", "."]）
        """
        self.name = name
        self.command = command
        self.args = args or []
        self.process: asyncio.subprocess.Process | None = None
        self._connected = False
        self._tools: dict[str, MCPTool] = {}
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}

    @property
    def is_connected(self) -> bool:
        return self._connected and self.process is not None

    @property
    def tools(self) -> list[MCPTool]:
        return list(self._tools.values())

    async def connect(self) -> bool:
        """
        启动 MCP Server 进程并建立连接

        Returns:
            bool: 是否连接成功
        """
        try:
            Console.info(f"正在启动 MCP Server: {self.name}...")

            # 启动子进程
            # 强制所有输出用 UTF-8 编码，避免 Windows GBK 编码问题
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
            env["LANG"] = "en_US.UTF-8"

            if os.name == "nt":
                # Windows：使用 shell=True 来处理 .cmd/.bat 文件
                cmd_line = " ".join([self.command] + self.args)
                self.process = await asyncio.create_subprocess_shell(
                    cmd_line,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
            else:
                # Linux/Mac：直接执行
                self.process = await asyncio.create_subprocess_exec(
                    self.command,
                    *self.args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )

            # 等待进程启动
            await asyncio.sleep(0.5)

            if self.process.returncode is not None:
                stderr = await self.process.stderr.read() if self.process.stderr else b""
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                Console.error(f"MCP Server {self.name} 启动失败: {error_msg}")
                return False

            # 发送初始化请求
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "code-agent-cli",
                    "version": "0.1.0"
                }
            })

            # 等待初始化响应
            await asyncio.sleep(0.5)

            # 发送 initialized 通知
            await self._send_notification("notifications/initialized", {})

            await asyncio.sleep(0.5)

            # 获取工具列表
            tools_response = await self._send_request("tools/list", {})
            if tools_response and "tools" in tools_response:
                for tool_info in tools_response["tools"]:
                    # 转换为 MCPTool
                    mcp_tool = MCPTool(
                        name=tool_info["name"],
                        description=tool_info.get("description", ""),
                        input_schema=tool_info.get("inputSchema", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }),
                        server_name=self.name,
                        client=self
                    )
                    self._tools[mcp_tool.name] = mcp_tool

            self._connected = True
            Console.success(f"✅ MCP Server {self.name} 连接成功，提供 {len(self._tools)} 个工具")
            return True

        except Exception as e:
            Console.error(f"连接 MCP Server {self.name} 失败: {type(e).__name__}: {e}")
            return False

    async def disconnect(self) -> None:
        """断开连接并清理进程"""
        if self.process:
            try:
                # 先关闭所有管道（Windows 特别需要）
                for pipe in [self.process.stdin, self.process.stdout, self.process.stderr]:
                    if pipe and not pipe.is_closing():
                        pipe.close()

                # 终止进程
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=3)
            except asyncio.TimeoutError:
                # 不配合就强杀
                self.process.kill()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=2)
                except Exception:
                    pass
            except Exception:
                # 清理阶段出错也没关系，反正程序要退出了
                pass
            self.process = None
        self._connected = False
        self._tools.clear()
        Console.info(f"MCP Server {self.name} 已断开")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果字符串
        """
        if not self._connected:
            return f"错误: MCP Server {self.name} 未连接"

        try:
            response = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })

            if "content" in response:
                # MCP 返回的 content 是数组，每个元素有 type/text
                content_parts = []
                for item in response["content"]:
                    if item.get("type") == "text":
                        content_parts.append(item.get("text", ""))
                    else:
                        content_parts.append(str(item))
                return "\n".join(content_parts)
            else:
                return str(response)

        except Exception as e:
            return f"工具调用失败: {type(e).__name__}: {e}"

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """发送 JSON-RPC 请求并等待响应"""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("进程未启动或流不可用")

        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }

        # 发送请求
        request_bytes = (json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8")
        self.process.stdin.write(request_bytes)
        await self.process.stdin.drain()

        # 等待响应（简单实现，后续可以优化为真正的异步响应匹配）
        return await self._read_response(request_id)

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """发送 JSON-RPC 通知（不需要响应）"""
        if not self.process or not self.process.stdin:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }

        notification_bytes = (json.dumps(notification, ensure_ascii=False) + "\n").encode("utf-8")
        self.process.stdin.write(notification_bytes)
        await self.process.stdin.drain()

    async def _read_response(self, request_id: int) -> dict[str, Any]:
        """读取响应（简化版实现）"""
        if not self.process or not self.process.stdout:
            return {}

        try:
            # 读取一行
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout=30)
            if not line:
                return {}

            response = json.loads(line.decode("utf-8"))
            return response.get("result", {})
        except asyncio.TimeoutError:
            return {"error": "请求超时"}
        except json.JSONDecodeError:
            return {"error": "响应解析失败"}
        except Exception as e:
            return {"error": str(e)}
