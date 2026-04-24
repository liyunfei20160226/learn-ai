"""
Code Agent - 命令行入口

这是整个程序的入口点，实现了最基本的 REPL 循环：
Read（读取输入） → Eval（处理） → Print（输出） → Loop（循环）
"""


def main():
    """程序主入口"""

    # 欢迎信息
    print("=" * 50)
    print("🤖 Code Agent")
    print("=" * 50)
    print("输入 'exit' 或 'quit' 退出")
    print("输入任意文字，我会原样回应")
    print()

    # REPL 循环 - 这就是 CLI 的核心
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

        # 2. Eval - 处理输入（现在先简单回应，后面加 Agent）
        # 3. Print - 输出结果
        print(f"🤖 Agent: 你说的是「{user_input}」")
        print()

    # 4. Loop - 回到循环开头，等待下一次输入


if __name__ == "__main__":
    main()
