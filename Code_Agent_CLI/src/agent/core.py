"""
Agent 核心 - 实现思考-行动循环

这是整个 Agent 系统的核心！
主要职责：
1. 维护消息历史（上下文）
2. 实现思考-行动循环
3. 调度工具调用
"""
from typing import List, Dict, Any
from tools.registry import ToolRegistry
from tools.base import ToolError


class Agent:
    """
    Agent 核心类

    负责：
    - 保存对话历史
    - 思考：分析用户输入，决定怎么做
    - 行动：如果需要，调用工具
    - 循环：直到得出最终答案
    """

    def __init__(self):
        # 消息历史 - 记录所有对话，Agent 思考的依据
        # 格式: [{"role": "user", "type": "user_input", "content": "xxx"}, ...]
        self.messages: List[Dict[str, Any]] = []

    def add_user_message(self, content: str):
        """
        添加用户消息到历史

        Args:
            content: 用户说的话
        """
        self.messages.append({
            "role": "user",
            "type": "user_input",  # 标记：这是用户输入
            "content": content
        })

    def add_tool_result_message(self, content: str):
        """
        添加工具结果到历史

        Args:
            content: 工具返回的结果
        """
        self.messages.append({
            "role": "user",
            "type": "tool_result",  # 标记：这是工具结果
            "content": content
        })

    def add_assistant_message(self, content: str):
        """
        添加 Assistant 消息到历史

        Args:
            content: Agent 说的话
        """
        self.messages.append({
            "role": "assistant",
            "content": content
        })

    def get_last_user_input(self) -> str:
        """
        找到最后一条真正的用户输入（不是工具结果）

        Returns:
            最后一条用户输入的内容
        """
        # 从后往前找，找到第一个 type 是 user_input 的消息
        for msg in reversed(self.messages):
            if msg.get("type") == "user_input":
                return msg["content"]
        return ""

    async def think(self) -> Dict[str, Any]:
        """
        🧠 思考阶段 - 分析历史，决定下一步做什么

        这是 Agent 的大脑！
        现在先用硬编码逻辑，后面换成真正的 LLM。

        Returns:
            决定结果:
            {
                "action": "tool" 或 "answer",  # 要行动还是直接回答
                "tool_name": "read",           # 如果是行动，调用哪个工具
                "tool_args": {"path": "xxx"},  # 工具参数
                "content": "最终回答"          # 如果直接回答，回答内容
            }
        """
        # ========== 关键判断：先看有没有工具结果 ==========
        # 如果上一条消息是工具结果，说明工具已经调用完了
        # 这时候应该直接回答，不要再调用工具了！
        # （这是防止死循环的核心逻辑）
        last_msg = self.messages[-1]
        if last_msg.get("type") == "tool_result":
            return {
                "action": "answer",
                "content": f"工具执行完成，结果：\n{last_msg['content']}"
            }

        # ========== 还没有工具结果，继续判断要不要调用工具 ==========
        last_user_message = self.get_last_user_input().lower()

        # 关键词：读文件、read、看一下
        if any(keyword in last_user_message for keyword in ["读", "read", "看一下", "打开"]):
            return {
                "action": "tool",
                "tool_name": "read",
                "tool_args": {
                    "path": last_user_message.split()[-1]  # 简单提取最后一个词当文件名
                }
            }

        # 关键词：文件列表、list、有什么
        elif any(keyword in last_user_message for keyword in ["列表", "list", "文件", "目录"]):
            return {
                "action": "tool",
                "tool_name": "list",
                "tool_args": {
                    "path": "."
                }
            }

        # 其他情况：直接回答
        else:
            return {
                "action": "answer",
                "content": f"我收到了你的消息：「{last_user_message}」"
            }

    async def execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        """
        🔧 行动阶段 - 执行工具调用

        通过 ToolRegistry 查找工具，真正执行！

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            工具执行结果
        """
        print(f"   [工具调用] 名称: {tool_name}, 参数: {tool_args}")

        try:
            # 1. 从注册表找到工具类，创建实例
            tool = ToolRegistry.get(tool_name)

            # 2. 执行工具（异步调用）
            result = await tool.run(tool_args)

            print(f"   [工具执行成功] 结果长度: {len(result)} 字符")
            return result

        except ToolError as e:
            # 工具自己抛出的已知错误
            error_msg = f"工具执行失败：{e}"
            print(f"   [工具错误] {error_msg}")
            return error_msg

        except Exception as e:
            # 意料之外的错误
            error_msg = f"工具执行发生未知错误：{type(e).__name__}: {e}"
            print(f"   [工具异常] {error_msg}")
            return error_msg

    async def run(self, user_input: str) -> str:
        """
        🚀 运行一次完整的思考-行动循环

        这是对外的主接口，main.py 会调用这个方法。

        Args:
            user_input: 用户最新的输入

        Returns:
            Agent 的最终回答
        """
        # 1. 把用户的最新输入加入历史
        self.add_user_message(user_input)

        # 2. 思考-行动循环
        while True:
            print("\n[Agent 正在思考...]")

            # 🧠 第一步：思考（异步调用，将来这里会调用 LLM API）
            decision = await self.think()

            # 情况 A：不需要工具，直接给出最终答案
            if decision["action"] == "answer":
                final_answer = decision["content"]
                self.add_assistant_message(final_answer)
                return final_answer

            # 情况 B：需要调用工具
            elif decision["action"] == "tool":
                tool_name = decision["tool_name"]
                tool_args = decision["tool_args"]

                # 🔧 第二步：执行工具（异步调用）
                tool_result = await self.execute_tool(tool_name, tool_args)

                # 📝 第三步：把工具结果加到消息历史
                # 关键修复：用专门的 add_tool_result_message，而不是 add_user_message
                self.add_tool_result_message(tool_result)

                # 🔄 第四步：循环回去，继续思考
                # （while True 会自动回到 loop 开头）

            # 其他情况：出错了
            else:
                error_msg = f"不知道要做什么: {decision}"
                self.add_assistant_message(error_msg)
                return error_msg
