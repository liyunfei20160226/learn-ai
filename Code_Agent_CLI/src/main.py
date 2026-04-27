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


async def main():
    """程序主入口"""

    # ========== 系统初始化 ==========

    # 0. 加载环境变量（从 .env 文件）
    # 必须在创建 LLM Provider 之前加载
    load_dotenv()

    # 1. 注册所有可用工具
    register_all_tools()

    # 2. 打印已注册的工具（调试用）
    print_registered_tools()
    print()

    # 3. 创建 LLM Provider（工厂模式）
    # 根据 .env 中的 LLM_PROVIDER 配置自动选择
    print("正在初始化 LLM Provider...")
    llm = get_llm_provider()
    print(f"✅ 已连接: {llm.provider_name} - 模型: {llm.model}")
    print()

    # 4. 创建 Agent 实例（整个会话共用一个 Agent，保留上下文）
    # 依赖注入：把 LLM Provider 传给 Agent，而不是 Agent 内部创建
    max_iterations = int(os.getenv("MAX_ITERATIONS", "20"))  # 默认 20 次
    agent = Agent(llm_provider=llm, max_iterations=max_iterations)

    # 欢迎信息
    print("=" * 60)
    print("🤖 Code Agent - 基于 LLM 的智能编程助手")
    print("=" * 60)
    print("支持的能力:")
    print("  - 列出目录内容")
    print("  - 读取文件内容")
    print("  - 写入文件")
    print("  - 搜索文件内容")
    print("\n输入 'exit' 或 'quit' 退出\n")

    # REPL 循环
    while True:
        # 1. Read - 读取用户输入
        user_input = input("👤 你: ").strip()

        # 处理退出命令
        if user_input.lower() in ["exit", "quit", "退出"]:
            print("👋 再见！")
            break

        # 空输入不处理
        if not user_input:
            continue

        # 2. Eval - Agent 处理（思考-行动循环）
        await agent.run(user_input)

        # 3. Print - 换行分隔（流式输出已在 Agent.think() 中打印）
        print()

    # 4. Loop - 回到循环开头


if __name__ == "__main__":
    # 因为 Agent.run 是异步的，所以要用 asyncio.run
    asyncio.run(main())
