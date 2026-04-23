#!/usr/bin/env python3
"""代码自动生成 Agent CLI 入口"""

import argparse
import atexit
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# 修复 Windows 控制台编码问题（支持 emoji 和 UTF-8 输出）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from core import CodegenCoordinator
from core.config import get_config

# 日志文件放在 log 目录（自动创建）
PROJECT_ROOT = Path(__file__).parent
LOG_DIR = PROJECT_ROOT / "log"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "codegen_agent.log"

# 清除默认配置（避免重复输出）
root_logger = logging.getLogger()
root_logger.handlers.clear()

# 统一日志格式
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# ========== 控制台输出（给用户看：简洁，只输出 INFO+，过滤第三方库日志） ==========
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# 控制台日志 Filter：只显示业务日志，不输出异常堆栈
class UserLogFilter(logging.Filter):
    def filter(self, record):
        # 只显示我们代码的日志
        if not record.name.startswith(("__main__", "core.", "prompts.")):
            return False
        # 不输出异常堆栈到控制台（只写到文件）
        if record.exc_info is not None:
            return False
        return True

console_handler.addFilter(UserLogFilter())
root_logger.addHandler(console_handler)

# ========== 文件输出（给排查用：详细，DEBUG+，包含所有日志） ==========
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)  # 文件记录更详细
root_logger.addHandler(file_handler)

root_logger.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.info(f"日志文件位置: {LOG_FILE}")


def _cleanup_temp_files() -> None:
    """程序退出时清理临时文件"""
    logger.info("执行清理...")


def _validate_file_path(file_path: str | Path, file_desc: str) -> Path:
    """验证文件路径是否存在且可读

    Args:
        file_path: 文件路径
        file_desc: 文件描述（用于错误消息）

    Returns:
        解析后的 Path 对象

    Raises:
        ValueError: 文件不存在或不可读
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise ValueError(f"{file_desc} 不存在: {path}")
    if not path.is_file():
        raise ValueError(f"{file_desc} 不是文件: {path}")
    return path


def _validate_positive_int(value: int | None, name: str) -> int | None:
    """验证正整数"""
    if value is None:
        return None
    if value <= 0:
        raise ValueError(f"{name} 必须是正整数: {value}")
    return value


def main():
    # 注册清理函数
    atexit.register(_cleanup_temp_files)

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="AI-powered code generation agent with ReAct pattern",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "prd_path",
        type=str,
        help="PRD 需求文档 JSON 路径",
    )
    parser.add_argument(
        "--architecture",
        "-a",
        type=str,
        required=True,
        help="架构设计文档 JSON 路径",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="输出目录 (默认: 从配置或环境变量读取)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM 模型 (默认: 从配置或环境变量读取)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="OpenAI API Base URL",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API Key (默认从环境变量 OPENAI_API_KEY 读取)",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="环境变量配置文件路径 (默认: .env)",
    )
    parser.add_argument(
        "--max-stories",
        type=int,
        default=None,
        help="最多执行 N 个任务（用于调试）",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="从上次中断的位置继续执行",
    )

    args = parser.parse_args()

    try:
        # 验证参数
        prd_path = _validate_file_path(args.prd_path, "PRD 文件")
        arch_path = _validate_file_path(args.architecture, "架构文件")
        _validate_positive_int(args.max_stories, "--max-stories")

        # 加载配置
        config = get_config(args.env_file)

        # 优先级：CLI 参数 > 配置文件 > 环境变量 > 默认值
        api_key = args.api_key or config.openai_api_key
        if not api_key:
            print("❌ 请提供 API Key (--api-key 或环境变量 OPENAI_API_KEY)")
            logger.error("API Key 未提供")
            return 1

        base_url = args.base_url or config.openai_base_url
        model = args.model or config.openai_model
        output_dir = args.output_dir or config.working_dir

        output_dir = Path(output_dir).resolve()

        print("=" * 60)
        print("🚀 代码自动生成 Agent (ReAct Mode)")
        print("=" * 60)
        print(f"📄 PRD: {prd_path}")
        print(f"🏗️  架构: {arch_path}")
        print(f"📂 输出: {output_dir}")
        print(f"🤖 模型: {model}")
        print(f"⏱️  超时: {config.openai_timeout}s")
        print(f"🔄 重试: {config.openai_max_retries} 次")
        print(f"🔢 最大Tokens: {config.openai_max_tokens or '默认'}")
        print(f"🌡️  Temperature: {config.openai_temperature}")
        print(f"🔁 最大迭代: {config.max_iterations}")
        print()

        logger.info("开始代码生成流程, PRD: %s, 架构: %s", prd_path, arch_path)

        coordinator = CodegenCoordinator(
            api_key=api_key,
            base_url=base_url,
            model=model,
            working_dir=str(output_dir),
            config=config,
        )

        try:
            result = coordinator.process_codegen(
                prd_path=str(prd_path),
                architecture_path=str(arch_path),
                max_stories=args.max_stories,
            )

            print()
            print("=" * 60)
            print("✅ 生成完成!")
            print(f"   会话 ID: {result['session_id']}")
            print(f"   总任务: {result['total_tasks']}")
            print(f"   已完成: {result['completed_tasks']}")
            print("=" * 60)

            logger.info("生成完成, 会话ID: %s, 总任务: %d, 已完成: %d",
                        result['session_id'], result['total_tasks'], result['completed_tasks'])

            return 0

        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断，进度已保存，可以使用相同参数继续执行")
            logger.info("用户中断执行")
            return 130
        except Exception as e:
            print(f"\n\n❌ 执行失败: {e}")
            # 堆栈只输出到日志文件（console_handler 的 Filter 会过滤掉），用于排查问题
            logger.exception("执行失败详情")
            return 1

    except ValueError as e:
        print(f"❌ 参数错误: {e}")
        logger.error("参数验证失败: %s", e)
        return 1


if __name__ == "__main__":
    exit(main())
