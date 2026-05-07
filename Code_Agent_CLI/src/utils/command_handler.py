"""
命令处理器 - 统一管理 REPL 特殊命令

设计模式：命令模式 + 注册模式
- 使用装饰器 @register 注册命令
- 支持命令别名
- 自动生成帮助信息
- 可扩展，不污染 main.py
"""
from typing import Dict, Callable, List
from dataclasses import dataclass

from utils.console import Console
from skills import SkillRegistry
from mcp_client import mcp_manager


@dataclass
class Command:
    """命令定义"""
    name: str                    # 命令名称（如 "stats"）
    handler: Callable            # 处理函数
    description: str = ""       # 描述（用于帮助）
    aliases: List[str] = None   # 别名列表

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class CommandHandler:
    """命令处理器 - 管理所有特殊命令"""

    def __init__(self):
        self._commands: Dict[str, Command] = {}  # name -> Command
        self._alias_map: Dict[str, str] = {}     # alias -> command name

    def register(self, name: str, description: str = "", aliases: List[str] = None):
        """
        装饰器：注册一个命令

        使用示例:
            @handler.register("stats", "显示上下文 Token 使用统计")
            def cmd_stats(agent):
                agent.show_context_stats()
        """
        def decorator(func: Callable) -> Callable:
            cmd = Command(
                name=name,
                handler=func,
                description=description,
                aliases=aliases or []
            )
            self._commands[name] = cmd

            # 注册别名
            for alias in cmd.aliases:
                self._alias_map[alias] = name

            return func
        return decorator

    def is_command(self, user_input: str) -> bool:
        """判断输入是不是命令（以 / 开头）"""
        return user_input.strip().startswith("/")

    def handle(self, agent, user_input: str) -> bool:
        """
        处理用户输入的命令（支持带参数）

        Args:
            agent: Agent 实例
            user_input: 用户输入（如 "/stats" 或 "/recall 1"）

        Returns:
            bool: 是否成功处理了命令
                - True: 命令已处理，不需要传给 Agent
                - False: 不是命令 / 未知命令，需要传给 Agent
        """
        input_stripped = user_input.strip()
        if not input_stripped.startswith("/"):
            return False  # 不是命令，传给 Agent

        # 分割命令名和参数
        parts = input_stripped[1:].split(maxsplit=1)  # 只分割一次，保留参数中的空格
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # 解析别名
        if cmd_name in self._alias_map:
            cmd_name = self._alias_map[cmd_name]

        # 特殊处理需要参数的命令
        if cmd_name == "recall":
            return self._handle_recall(agent, args)
        if cmd_name == "compression":
            return self._handle_compression_toggle(agent, args)

        # 查找并执行无参数命令
        if cmd_name in self._commands:
            cmd = self._commands[cmd_name]
            cmd.handler(agent)
            return True  # 已处理，不传给 Agent
        else:
            # 未知命令，显示提示
            available = ", ".join(f"/{name}" for name in self._commands.keys())
            Console.warning(f"未知命令 '{input_stripped}'，可用命令：{available}")
            Console.info("输入 /help 查看详细帮助")
            return True  # 虽然是未知命令，但也不传给 Agent（避免 LLM 幻觉）

    def _handle_recall(self, agent, args: str) -> bool:
        """处理 /recall 命令"""
        if not agent.context.enable_compression:
            Console.warning("智能压缩功能未启用，无法召回内容")
            return True

        items = agent.context.list_compressed_items()
        if not items:
            Console.info("  暂无被压缩的内容")
            return True

        try:
            # 支持按序号或 ID 召回
            if args.isdigit():
                idx = int(args) - 1
                if 0 <= idx < len(items):
                    content_id = items[idx]
                else:
                    Console.warning(f"无效的序号，请输入 1~{len(items)} 之间的数字")
                    return True
            else:
                content_id = args
                if content_id not in items:
                    Console.warning(f"找不到 ID 为 '{content_id}' 的压缩内容")
                    return True

            # 召回完整内容
            full_content = agent.context.recall_content(content_id)
            if full_content:
                print()
                Console.section(f"🔍 召回内容：{content_id}")
                print()
                print(full_content)
                print()
                Console.info(f"完整内容已显示，共 {len(full_content)} 字符")
            else:
                Console.warning(f"召回失败，找不到内容：{content_id}")

        except Exception as e:
            Console.error(f"召回内容出错: {e}")

        return True

    def _handle_compression_toggle(self, agent, args: str) -> bool:
        """处理 /compression 命令"""
        if not args or args.lower() == "status":
            # 显示当前状态
            status = "已启用" if agent.context.enable_compression else "已禁用"
            print()
            Console.section("✨ 智能压缩状态")
            print()
            print(f"   当前状态: {status}")
            if agent.context.compression:
                stats = agent.context.compression.stats
                print(f"   已压缩项数: {stats.total_compressed}")
                print(f"   节省字符数: {stats.total_saved_chars:,}")
                print(f"   节省率: {stats.overall_ratio:.1f}%")
            print()
            return True

        if args.lower() in ("on", "enable"):
            agent.context.enable_compression = True
            Console.success("✅ 智能压缩功能已启用")
            return True

        if args.lower() in ("off", "disable"):
            agent.context.enable_compression = False
            Console.warning("⚠️  智能压缩功能已禁用")
            return True

        # 无效参数
        Console.warning("用法: /compression on|off|status")
        return True

    def get_help_text(self) -> str:
        """生成帮助文本"""
        lines = ["📖 可用命令："]
        for name, cmd in self._commands.items():
            alias_str = f"（别名: {'/'.join(cmd.aliases)}）" if cmd.aliases else ""
            lines.append(f"   /{name}{alias_str} - {cmd.description}")
        return "\n".join(lines)


# ============= 创建全局实例并注册所有命令 =============

handler = CommandHandler()


# -------- 注册 /stats 命令 --------
@handler.register("stats", "显示上下文 Token 使用统计")
def cmd_stats(agent):
    agent.show_context_stats()


# -------- 注册 /clear 命令 --------
@handler.register("clear", "清空当前上下文（开始新对话）")
def cmd_clear(agent):
    agent.clear_context()
    Console.success("✅ 上下文已清空")


# -------- 注册 /help 命令 --------
@handler.register("help", "显示命令帮助", aliases=["?"])
def cmd_help(_agent):
    print()
    print(handler.get_help_text())
    print()


# -------- 注册 /skills 命令 --------
@handler.register("skills", "显示所有已加载的 Skill 列表")
def cmd_skills(_agent):
    print()
    print(Console.color("thinking") + "📦 已加载的 Skill 列表" + Console.RESET)
    print()

    skill_names = SkillRegistry.list_names()

    if not skill_names:
        print(Console.color("info") + "   没有加载任何 Skill" + Console.RESET)
        print()
        return

    for name in skill_names:
        # 直接从注册表获取 Skill 实例的 description
        skill = SkillRegistry.get(name)
        description = skill.description if skill else ""

        # 截取前 80 个字符的描述
        short_desc = description[:80] + "..." if len(description) > 80 else description

        print(f"   {Console.color('success')}✅{Console.RESET} {name}")
        if short_desc:
            print(f"      {Console.color('info')}{short_desc}{Console.RESET}")
        print()

    print(f"   共 {len(skill_names)} 个 Skill")
    print()


# -------- 注册 /mcps 命令 --------
@handler.register("mcps", "显示 MCP Server 连接状态和可用工具列表")
def cmd_mcps(_agent):
    mcp_manager.print_status()


# -------- 注册 /recall 命令（Phase 6：Compression） --------
@handler.register("recall", "召回被压缩内容的完整版本（用法：/recall <content_id>）")
def cmd_recall(agent, *args):
    # 注意：*args 只是占位，实际在 handle 方法中处理参数
    pass


# -------- 注册 /compression 命令（Phase 6：Compression） --------
@handler.register("compression", "开关压缩功能（用法：/compression on/off）")
def cmd_compression(agent, *args):
    pass


# -------- 注册 /compressed 命令（Phase 6：Compression） --------
@handler.register("compressed", "列出所有被压缩的内容")
def cmd_compressed(agent):
    if not agent.context.enable_compression:
        Console.info("  智能压缩功能未启用")
        return

    items = agent.context.list_compressed_items()
    if not items:
        Console.info("  暂无被压缩的内容")
        return

    print()
    Console.section(f"📦 被压缩的内容（共 {len(items)} 项）")
    print()
    for idx, item in enumerate(items, 1):
        print(f"   {idx}. {item}")
    print()
    Console.info("  输入 /recall <序号> 查看完整内容")
    print()
