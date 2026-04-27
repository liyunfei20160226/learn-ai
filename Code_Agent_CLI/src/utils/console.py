"""
控制台输出工具 - 统一管理颜色和格式
"""
import asyncio
import io
import json
import os
import sys
import time
from colorama import init, Fore, Style

# 修复 Windows 终端编码问题 - 强制使用 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

# 初始化 colorama（Windows 自动启用 ANSI 支持）
init(autoreset=True)

# 配置文件路径（项目根目录下 .config）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(PROJECT_ROOT, ".config")
THEME_FILE = os.path.join(CONFIG_DIR, "theme.json")

# 颜色主题定义 - 增强版，配色差异更明显
THEMES = {
    "dark": {
        "name": "Dark (默认)",
        "description": "经典深色 - 青色高亮",
        "colors": {
            "agent": Fore.LIGHTCYAN_EX,
            "tool": Fore.LIGHTYELLOW_EX,
            "success": Fore.LIGHTGREEN_EX,
            "error": Fore.LIGHTRED_EX,
            "thinking": Fore.LIGHTBLUE_EX,
            "info": Fore.LIGHTBLACK_EX,
            "accent": Fore.LIGHTCYAN_EX,
        }
    },
    "dracula": {
        "name": "Dracula (吸血鬼风)",
        "description": "紫色基调 - 潮流高对比",
        "colors": {
            "agent": Fore.LIGHTMAGENTA_EX,
            "tool": Fore.LIGHTYELLOW_EX,
            "success": Fore.LIGHTGREEN_EX,
            "error": Fore.LIGHTRED_EX,
            "thinking": Fore.MAGENTA,
            "info": Fore.LIGHTBLACK_EX,
            "accent": Fore.LIGHTMAGENTA_EX,
        }
    },
    "monokai": {
        "name": "Monokai (经典 IDE)",
        "description": "橙色+粉色 - Sublime 经典",
        "colors": {
            "agent": Fore.LIGHTGREEN_EX,
            "tool": Fore.LIGHTMAGENTA_EX,
            "success": Fore.GREEN,
            "error": Fore.LIGHTRED_EX,
            "thinking": Fore.LIGHTYELLOW_EX,
            "info": Fore.LIGHTBLACK_EX,
            "accent": Fore.LIGHTGREEN_EX,
        }
    },
    "nord": {
        "name": "Nord (北欧风)",
        "description": "冰雪蓝 - 现代极简",
        "colors": {
            "agent": Fore.CYAN,
            "tool": Fore.LIGHTCYAN_EX,
            "success": Fore.GREEN,
            "error": Fore.RED,
            "thinking": Fore.BLUE,
            "info": Fore.LIGHTBLACK_EX,
            "accent": Fore.CYAN,
        }
    },
    "solarized": {
        "name": "Solarized (日光色)",
        "description": "黄蓝配色 - 护眼低对比",
        "colors": {
            "agent": Fore.YELLOW,
            "tool": Fore.MAGENTA,
            "success": Fore.GREEN,
            "error": Fore.RED,
            "thinking": Fore.BLUE,
            "info": Fore.LIGHTBLACK_EX,
            "accent": Fore.YELLOW,
        }
    },
    "ocean": {
        "name": "Ocean (深海)",
        "description": "蓝色基调 - 沉稳深邃",
        "colors": {
            "agent": Fore.BLUE,
            "tool": Fore.CYAN,
            "success": Fore.LIGHTGREEN_EX,
            "error": Fore.LIGHTRED_EX,
            "thinking": Fore.LIGHTBLUE_EX,
            "info": Fore.LIGHTBLACK_EX,
            "accent": Fore.BLUE,
        }
    },
}


class Console:
    """控制台输出工具类"""

    # 当前主题
    _current_theme = "dark"

    # 旋转动画字符
    SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    _spinner_task = None
    _spinner_running = False
    _spinner_text = ""
    _spinner_start_time = 0.0

    # 用户输入颜色固定
    WHITE = Fore.LIGHTWHITE_EX
    RESET = Style.RESET_ALL

    @classmethod
    def color(cls, color_name: str) -> str:
        """获取当前主题的指定颜色"""
        return THEMES[cls._current_theme]["colors"][color_name]

    @classmethod
    def set_theme(cls, theme_name: str) -> None:
        """设置颜色主题"""
        if theme_name in THEMES:
            cls._current_theme = theme_name

    @classmethod
    def save_theme(cls) -> None:
        """保存主题设置到配置文件"""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(THEME_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme": cls._current_theme}, f, indent=2)

    @classmethod
    def load_theme(cls) -> bool:
        """从配置文件加载主题设置

        Returns:
            bool: 是否成功加载了已保存的主题
        """
        if os.path.exists(THEME_FILE):
            try:
                with open(THEME_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    theme = config.get("theme")
                    if theme in THEMES:
                        cls._current_theme = theme
                        return True
            except (json.JSONDecodeError, IOError):
                pass
        return False

    @classmethod
    def show_theme_selector(cls) -> None:
        """显示主题选择菜单（输入数字，实时预览）"""
        print()
        print(Fore.LIGHTCYAN_EX + "🎨 请选择颜色主题（输入数字预览效果，回车确认）" + Fore.RESET)
        print()

        theme_keys = list(THEMES.keys())

        # 先列出所有选项
        for i, key in enumerate(theme_keys, 1):
            theme = THEMES[key]
            default_mark = " ⭐ 默认" if key == "dark" else ""
            print(f"   {i}. {theme['name']}{default_mark}")

        print()

        # 让用户输入选择，支持预览
        while True:
            choice = input(Fore.LIGHTBLACK_EX + "   输入序号确认，或先输入预览效果（直接回车用默认）: " + Fore.RESET).strip()

            if not choice:
                selected = "dark"
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(theme_keys):
                    selected = theme_keys[idx]

                    # 临时切换显示预览效果
                    old_theme = cls._current_theme
                    cls._current_theme = selected

                    print()
                    print(f"   {cls.color('accent')}▶ 预览主题: {THEMES[selected]['name']}{cls.RESET}")
                    print(f"   {cls.color('agent')}🤖 Agent回答  {cls.color('thinking')}🧠思考中  {cls.color('tool')}🔧工具  {cls.color('success')}✅成功  {cls.color('error')}❌错误{cls.RESET}")
                    print()

                    confirm = input(Fore.LIGHTBLACK_EX + "   确认使用这个主题？(Y/n) " + Fore.RESET).strip().lower()
                    if confirm in ("", "y", "yes"):
                        break
                    else:
                        cls._current_theme = old_theme
                        print()
                        continue
                else:
                    print(f"   请输入 1-{len(theme_keys)} 之间的数字")
            except ValueError:
                print("   请输入有效的数字")

        # 应用并保存主题
        cls.set_theme(selected)
        cls.save_theme()

        # 显示确认信息（用新主题的颜色）
        print()
        print(cls.color("success") + f"   ✅ 已设置主题: {THEMES[selected]['name']}" + cls.RESET)
        print()

    @classmethod
    def hr(cls, width: int = 60) -> None:
        """打印水平分隔线"""
        print(cls.color("info") + "─" * width + cls.RESET)

    @classmethod
    def section(cls, title: str) -> None:
        """打印章节标题"""
        print()
        print(cls.color("thinking") + f"═══ {title} " + "═" * max(0, 50 - len(title)) + cls.RESET)

    @classmethod
    def think(cls, iteration: int = 1) -> None:
        """打印思考状态"""
        print()
        print(cls.color("thinking") + f"🧠 思考中... 第 {iteration} 轮" + cls.RESET)

    @classmethod
    def answer_prefix(cls) -> None:
        """打印 Agent 回答前缀（流式输出用）"""
        print()
        print(cls.color("agent") + "🤖 Agent: " + cls.RESET, end="", flush=True)

    @classmethod
    def answer_text(cls, text: str, end: str = "") -> None:
        """打印回答文本片段（流式输出用）"""
        print(cls.color("agent") + text + cls.RESET, end=end, flush=True)

    @classmethod
    def answer_end(cls) -> None:
        """流式回答结束换行"""
        print()

    @classmethod
    def tool_call(cls, tool_name: str, arguments: dict) -> None:
        """打印工具调用信息"""
        print()
        print(cls.color("tool") + "─────────────────────────────────────────────────────────────" + cls.RESET)
        print(cls.color("tool") + f"🔧 调用工具: {tool_name}" + cls.RESET)

        if arguments:
            for key, value in arguments.items():
                value_str = str(value)
                # 超长截断
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                print(cls.color("tool") + f"    {key}: {value_str}" + cls.RESET)
        else:
            print(cls.color("tool") + "    (无参数)" + cls.RESET)

        print(cls.color("tool") + "─────────────────────────────────────────────────────────────" + cls.RESET)

    @classmethod
    def tool_success(cls, result_length: int, elapsed: float = 0.0) -> None:
        """打印工具执行成功"""
        elapsed_str = f" 耗时: {elapsed:.2f}s" if elapsed > 0 else ""
        print(cls.color("success") + f"   ✅ 工具执行完成 - 结果长度: {result_length} 字符{elapsed_str}" + cls.RESET)

    @classmethod
    def tool_error(cls, error_msg: str) -> None:
        """打印工具执行错误"""
        print(cls.color("error") + f"   ❌ {error_msg}" + cls.RESET)

    @classmethod
    def tool_warning(cls, warning_msg: str) -> None:
        """打印工具警告"""
        print(cls.color("tool") + f"   ⚠️  {warning_msg}" + cls.RESET)

    @classmethod
    def info(cls, message: str) -> None:
        """打印普通信息"""
        print(cls.color("info") + message + cls.RESET)

    @classmethod
    def success(cls, message: str) -> None:
        """打印成功信息"""
        print(cls.color("success") + message + cls.RESET)

    @classmethod
    def error(cls, message: str) -> None:
        """打印错误信息"""
        print(cls.color("error") + message + cls.RESET)

    @classmethod
    def warning(cls, message: str) -> None:
        """打印警告信息"""
        print(cls.color("tool") + "⚠️  " + message + cls.RESET)

    @classmethod
    def user_prompt(cls) -> str:
        """获取用户输入"""
        print()
        user_input = input(cls.WHITE + "👤 你: " + cls.RESET).strip()
        return user_input

    @classmethod
    def welcome(cls, provider_name: str, model: str, tools: list[str]) -> None:
        """打印欢迎信息"""
        print()
        print(cls.color("accent") + "=" * 60 + cls.RESET)
        print(cls.color("accent") + "🤖 Code Agent - 基于 LLM 的智能编程助手" + cls.RESET)
        print(cls.color("accent") + "=" * 60 + cls.RESET)
        print()
        print(cls.color("info") + f"   LLM: {provider_name} ({model})" + cls.RESET)
        print(cls.color("info") + f"   可用工具: {', '.join(tools)}" + cls.RESET)
        print()
        print(cls.color("info") + "   输入 'exit' 或 'quit' 退出" + cls.RESET)
        print()

    @classmethod
    def goodbye(cls) -> None:
        """打印再见信息"""
        print()
        print(cls.color("agent") + "👋 再见！" + cls.RESET)
        print()

    @classmethod
    async def _spinner_loop(cls) -> None:
        """旋转动画循环"""
        i = 0
        while cls._spinner_running:
            elapsed = time.time() - cls._spinner_start_time
            spinner_char = cls.SPINNER_CHARS[i % len(cls.SPINNER_CHARS)]
            print(
                f"\r   {spinner_char}  {cls._spinner_text} (已运行 {elapsed:.1f}s)",
                end="",
                flush=True,
                file=sys.stderr,
            )
            i += 1
            await asyncio.sleep(0.1)

    @classmethod
    async def start_spinner(cls, text: str = "工具执行中...") -> None:
        """启动旋转进度动画"""
        if cls._spinner_running:
            return

        cls._spinner_running = True
        cls._spinner_text = text
        cls._spinner_start_time = time.time()
        cls._spinner_task = asyncio.create_task(cls._spinner_loop())

    @classmethod
    async def stop_spinner(cls, success: bool = True, result_length: int = 0) -> float:
        """停止旋转进度动画"""
        if not cls._spinner_running or cls._spinner_task is None:
            return 0.0

        cls._spinner_running = False
        await cls._spinner_task
        cls._spinner_task = None

        elapsed = time.time() - cls._spinner_start_time

        # 清除动画行
        print("\r" + " " * 70, end="\r", flush=True, file=sys.stderr)

        # 打印结果状态
        if success:
            cls.tool_success(result_length, elapsed)
        else:
            cls.tool_error("工具执行失败")

        return elapsed
