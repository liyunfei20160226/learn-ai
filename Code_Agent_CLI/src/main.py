"""
Code Agent - 命令行入口

这是整个程序的入口点，实现了最基本的 REPL 循环：
Read（读取输入） → Eval（Agent 处理） → Print（输出） → Loop（循环）

集成了可插拔的 LLM Provider 架构，通过 .env 配置切换不同的 LLM。
"""
import os
import asyncio
from dotenv import load_dotenv

from agent.core import Agent
from tools.loader import register_all_tools, print_registered_tools
from llm.factory import get_llm_provider
from utils.console import Console


async def main():
    """程序主入口"""

    # ========== 系统初始化 ==========

    # 0. 加载环境变量（从 .env 文件）
    # 必须在创建 LLM Provider 之前加载
    load_dotenv()

    # 1. 注册所有可用工具
    register_all_tools()

    # 2. 颜色主题选择
    has_saved_theme = Console.load_theme()
    if not has_saved_theme:
        Console.show_theme_selector()

    # 3. 打印已注册的工具（调试用）
    print_registered_tools()

    # 4. 创建 LLM Provider（工厂模式）
    # 根据 .env 中的 LLM_PROVIDER 配置自动选择
    Console.info("正在初始化 LLM Provider...")
    llm = get_llm_provider()

    # Ollama 本地模型警告
    if llm.provider_name == "Ollama":
        print()
        print(Console.color("tool") + "⚠️  重要提示：当前使用的是 Ollama 本地模型" + Console.RESET)
        print(Console.color("info") + "   本地小模型目前对工具调用（tool use）的支持还不够完善" + Console.RESET)
        print(Console.color("info") + "   可能会影响 Agent 的工具使用功能，如文件读取、搜索等" + Console.RESET)
        print(Console.color("info") + "   我们将在后续版本中针对本地小模型进行专门优化" + Console.RESET)
        print()

    # 5. 创建 Agent 实例（整个会话共用一个 Agent，保留上下文）
    # 依赖注入：把 LLM Provider 传给 Agent，而不是 Agent 内部创建
    max_iterations = int(os.getenv("MAX_ITERATIONS", "20"))  # 默认 20 次
    agent = Agent(llm_provider=llm, max_iterations=max_iterations)

    # 欢迎信息
    tool_names = [tool["name"] for tool in agent.get_tool_descriptions()]
    Console.welcome(llm.provider_name, llm.model, tool_names)

    # REPL 循环
    while True:
        Console.hr()

        # 1. Read - 读取用户输入
        user_input = Console.user_prompt()

        # 处理退出命令
        if user_input.lower() in ["exit", "quit", "退出"]:
            Console.goodbye()
            break

        # 空输入不处理
        if not user_input:
            continue

        # 2. Eval - Agent 处理（思考-行动循环）
        await agent.run(user_input)

    # 3. Loop - 回到循环开头


if __name__ == "__main__":
    # 因为 Agent.run 是异步的，所以要用 asyncio.run
    asyncio.run(main())
