"""
Code Agent - 命令行入口

这是整个程序的入口点，实现了最基本的 REPL 循环：
Read（读取输入） → Eval（Agent 处理） → Print（输出） → Loop（循环）

现在集成了完整的 Agent 思考-行动循环！
"""
import asyncio
from agent.core import Agent


async def main():
    """程序主入口 - 现在是异步的，因为 Agent 要调用异步工具"""

    # 创建 Agent 实例（整个会话共用一个 Agent，保留上下文）
    agent = Agent()

    # 欢迎信息
    print("=" * 60)
    print("🤖 Code Agent - 带思考-行动循环")
    print("=" * 60)
    print("试试这些关键词:")
    print("  - 「读」、「read」、「看一下」 → 触发读文件工具")
    print("  - 「列表」、「list」、「文件」 → 触发列目录工具")
    print("  - 其他文字 → 直接回应")
    print("输入 'exit' 或 'quit' 退出")
    print()

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
        answer = await agent.run(user_input)

        # 3. Print - 输出最终回答
        print()
        print(f"🤖 Agent: {answer}")
        print()

    # 4. Loop - 回到循环开头


if __name__ == "__main__":
    # 因为 Agent.run 是异步的，所以要用 asyncio.run
    asyncio.run(main())