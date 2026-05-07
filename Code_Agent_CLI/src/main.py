"""
Code Agent - 命令行入口

这是整个程序的入口点，实现了最基本的 REPL 循环：
Read（读取输入） → Eval（Agent 处理） → Print（输出） → Loop（循环）

集成了可插拔的 LLM Provider 架构，通过 .env 配置切换不同的 LLM。
集成了 MCP (Model Context Protocol) 支持标准化工具调用。
"""
import os
import sys
import asyncio
import atexit
import warnings
from dotenv import load_dotenv

# Windows asyncio 子进程清理时会产生烦人的 "unclosed transport" 警告
# 这是 Python 已知 Bug，无害但难看，主动抑制
if sys.platform == "win32":
    warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed transport")
    warnings.filterwarnings("ignore", category=UserWarning, message="unclosed transport")

from agent.core import Agent
from tools.loader import register_all_tools, print_registered_tools
from llm.factory import get_llm_provider
from utils.console import Console
from utils.command_handler import handler  # 命令处理器
from mcp_client import mcp_manager  # MCP Server 管理器


async def main():
    """程序主入口"""

    # ========== 系统初始化 ==========

    # 0. 加载环境变量（从 .env 文件）
    # 必须在创建 LLM Provider 之前加载
    load_dotenv()

    # 1. 注册所有可用工具
    register_all_tools()

    # 2. 配置 MCP Servers（从环境变量读取）
    mcp_manager.configure_from_env()

    # 3. 连接所有 MCP Servers
    await mcp_manager.connect_all()

    # 4. Windows 终极防警告：最后阶段静默 stderr
    # 注意：atexit 是后进先出，所以先注册的会后运行
    if sys.platform == "win32":

        @atexit.register
        def swallow_asyncio_bug_warnings():
            """
            Python Windows asyncio 已知 Bug：子进程 transport GC 时会打印丑陋的错误信息。
            这是无害但难看的，我们在最后阶段把 stderr 吞掉。
            """
            import gc
            from io import StringIO

            # 替换 stderr，所有后续错误都进黑洞（不打算恢复）
            sys.stderr = StringIO()

            try:
                # 强制 GC，让 Transport __del__ 现在就被调用
                gc.collect()
            except Exception:
                pass  # GC 时发生任何错误都忽略
            finally:
                # 注意：这里不恢复 stderr 了，因为程序马上就要退出了
                # 这样最后阶段的任何其他输出也会被吞掉
                pass

    # 5. 注册退出时自动清理 MCP 进程（兜底用，正常退出会在 break 前主动清理）
    # 注意：这个后注册，所以会先运行（断开 MCP），然后才运行上面的防警告函数
    def cleanup_mcp():
        """程序退出时清理 MCP 进程（兜底，静默失败）"""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(mcp_manager.disconnect_all())
            finally:
                loop.close()
        except Exception:
            # 退出阶段，清理失败也没关系，静默忽略
            pass

    atexit.register(cleanup_mcp)
    cleanup_mcp_handler = cleanup_mcp

    # 5. 颜色主题选择
    has_saved_theme = Console.load_theme()
    if not has_saved_theme:
        Console.show_theme_selector()

    # 6. 打印已注册的工具（调试用，默认关闭）
    # print_registered_tools()

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

    # 5. 读取上下文管理配置
    context_config = {
        "total_budget": int(os.getenv("CONTEXT_TOTAL_BUDGET", "150000")),
        "working_window_size": int(os.getenv("CONTEXT_WORKING_WINDOW_SIZE", "10")),
        "working_max_tokens": int(os.getenv("CONTEXT_WORKING_MAX_TOKENS", "50000")),
        "tool_buffer_max_tokens": int(os.getenv("CONTEXT_TOOL_BUFFER_MAX_TOKENS", "80000")),
        "tool_small_threshold": int(os.getenv("CONTEXT_TOOL_SMALL_THRESHOLD", "1000")),
        "tool_large_threshold": int(os.getenv("CONTEXT_TOOL_LARGE_THRESHOLD", "5000")),
        # Skill 阈值 - 操作手册需要尽量完整 ✨
        "skill_small_threshold": int(os.getenv("CONTEXT_SKILL_SMALL_THRESHOLD", "100000")),
        "skill_large_threshold": int(os.getenv("CONTEXT_SKILL_LARGE_THRESHOLD", "100000")),
    }

    # 6. 创建 Agent 实例（整个会话共用一个 Agent，保留上下文）
    # 依赖注入：把 LLM Provider 传给 Agent，而不是 Agent 内部创建
    max_iterations = int(os.getenv("MAX_ITERATIONS", "20"))  # 默认 20 次
    agent = Agent(
        llm_provider=llm,
        max_iterations=max_iterations,
        context_config=context_config,
    )

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
            # 在事件循环还在时，先正常断开 MCP 连接（避免 Windows atexit 问题）
            await mcp_manager.disconnect_all()
            # 主动断开成功，注销 atexit 兜底，避免二次断开
            atexit.unregister(cleanup_mcp_handler)

            break

        # 空输入不处理
        if not user_input:
            continue

        # ===== 特殊命令：在 REPL 层面拦截，不传给 Agent =====
        # 所有命令逻辑都封装在 command_handler 中
        if handler.handle(agent, user_input):
            continue
        # ==================================================

        # 2. Eval - Agent 处理（思考-行动循环）
        await agent.run(user_input)

    # 3. Loop - 回到循环开头


if __name__ == "__main__":
    # 因为 Agent.run 是异步的，所以要用 asyncio.run
    asyncio.run(main())
