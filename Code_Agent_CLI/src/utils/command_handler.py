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
        处理用户输入的命令

        Args:
            agent: Agent 实例
            user_input: 用户输入（如 "/stats"）

        Returns:
            bool: 是否成功处理了命令
                - True: 命令已处理，不需要传给 Agent
                - False: 不是命令 / 未知命令，需要传给 Agent
        """
        input_lower = user_input.strip().lower()

        if not input_lower.startswith("/"):
            return False  # 不是命令，传给 Agent

        # 提取命令名（去掉 /）
        cmd_name = input_lower[1:]

        # 解析别名
        if cmd_name in self._alias_map:
            cmd_name = self._alias_map[cmd_name]

        # 查找并执行命令
        if cmd_name in self._commands:
            cmd = self._commands[cmd_name]
            cmd.handler(agent)
            return True  # 已处理，不传给 Agent
        else:
            # 未知命令，显示提示
            available = ", ".join(f"/{name}" for name in self._commands.keys())
            Console.warning(f"未知命令 '{user_input}'，可用命令：{available}")
            Console.info("输入 /help 查看详细帮助")
            return True  # 虽然是未知命令，但也不传给 Agent（避免 LLM 幻觉）

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
