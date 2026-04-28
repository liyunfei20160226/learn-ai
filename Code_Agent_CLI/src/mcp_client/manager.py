"""
MCP Server 管理器

负责：
1. 从配置中加载所有 MCP Server
2. 统一启动/停止所有 Server
3. 把所有 MCP 工具注册到 ToolRegistry
4. 提供状态查询接口
"""
import os
from typing import Optional

from .client import MCPClient
from tools.registry import ToolRegistry
from utils.console import Console


class MCPManager:
    """
    MCP Server 全局管理器

    使用单例模式，确保只有一个实例
    """

    _instance: Optional["MCPManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.servers: dict[str, MCPClient] = {}
        self._initialized = True

    def configure_from_env(self) -> None:
        """
        从环境变量配置 MCP Servers

        支持的配置格式：
        MCP_SERVER_FILESYSTEM="npx @modelcontextprotocol/server-filesystem ."
        MCP_SERVER_GITHUB="npx @modelcontextprotocol/server-github"

        命名规则：MCP_SERVER_<大写名称>="命令 参数1 参数2 ..."
        """
        for key, value in os.environ.items():
            if key.startswith("MCP_SERVER_"):
                # 提取 server 名称
                server_name = key[11:].lower()  # 去掉 "MCP_SERVER_" 前缀

                # 解析命令和参数
                parts = value.split()
                if not parts:
                    continue

                command = parts[0]
                args = parts[1:]

                # 创建客户端（暂时不连接，在 connect_all 时连接）
                self.servers[server_name] = MCPClient(
                    name=server_name,
                    command=command,
                    args=args
                )

                Console.info(f"已配置 MCP Server: {server_name}")

    async def connect_all(self) -> int:
        """
        连接所有已配置的 MCP Server

        Returns:
            成功连接的 Server 数量
        """
        success_count = 0

        for name, server in self.servers.items():
            if await server.connect():
                success_count += 1
                # 把该 Server 提供的所有工具注册到 ToolRegistry
                for tool in server.tools:
                    # 动态创建工具类并注册
                    self._register_mcp_tool(tool)

        if success_count == 0 and self.servers:
            Console.warning("没有成功连接任何 MCP Server，请检查配置")
        elif success_count > 0:
            Console.success(f"成功连接 {success_count}/{len(self.servers)} 个 MCP Server")

        return success_count

    async def disconnect_all(self) -> None:
        """断开所有 MCP Server 连接"""
        for server in self.servers.values():
            await server.disconnect()
        Console.info("所有 MCP Server 已断开")

    def _register_mcp_tool(self, tool) -> None:
        """
        把 MCP 工具注册到 ToolRegistry

        直接存储 MCPTool 实例（单例模式，MCP 工具不需要创建多个实例）
        """
        tool_name = tool.name
        # 直接存储实例（跳过 ToolRegistry 的类注册机制，直接存入内部字典）
        # 注意：这里用一个 hack 方式绕过 ToolRegistry 的类注册机制
        if tool_name not in ToolRegistry._tools:
            # MCP 工具是单例的，直接存储实例
            # 创建一个包装类，它的构造函数返回同一个实例
            tool_instance = tool

            class DynamicMCPToolWrapper:
                _instance = tool_instance

                def __new__(cls):
                    return cls._instance

            # 把包装类注册进去
            # 因为 __new__ 返回的是已有的 MCPTool 实例，name 和 tool_type 都正确
            ToolRegistry.register(DynamicMCPToolWrapper)

    def get_status(self) -> dict[str, dict]:
        """
        获取所有 MCP Server 的状态信息

        Returns:
            {server_name: {"connected": bool, "tools_count": int}}
        """
        status = {}
        for name, server in self.servers.items():
            status[name] = {
                "connected": server.is_connected,
                "tools_count": len(server.tools),
                "tools": [t.name for t in server.tools]
            }
        return status

    def print_status(self) -> None:
        """打印所有 MCP Server 的状态到控制台"""
        print()
        Console.section("📦 MCP Server 状态")
        print()

        if not self.servers:
            Console.info("  没有配置任何 MCP Server")
            Console.info("  请在 .env 文件中添加配置，例如：")
            Console.info('  MCP_SERVER_FILESYSTEM="npx @modelcontextprotocol/server-filesystem ."')
            print()
            return

        for name, server in self.servers.items():
            status_icon = "✅" if server.is_connected else "❌"
            status_text = "已连接" if server.is_connected else "未连接"
            print(f"  {status_icon} {name}: {status_text}")

            if server.tools:
                for tool in server.tools:
                    print(f"      - {tool.name}: {tool.description[:60]}..." if len(tool.description) > 60 else f"      - {tool.name}: {tool.description}")
            print()


# 全局单例实例
mcp_manager = MCPManager()
