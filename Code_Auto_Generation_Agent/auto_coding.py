#!/usr/bin/env python3
"""代码自动生成 Agent CLI 入口"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

from core import CodegenCoordinator
from core.config import get_config


def main():
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

    # 加载配置
    config = get_config(args.env_file)

    # 优先级：CLI 参数 > 配置文件 > 环境变量 > 默认值
    api_key = args.api_key or config.openai_api_key
    if not api_key:
        print("❌ 请提供 API Key (--api-key 或环境变量 OPENAI_API_KEY)")
        return 1

    base_url = args.base_url or config.openai_base_url
    model = args.model or config.openai_model
    output_dir = args.output_dir or config.working_dir

    prd_path = Path(args.prd_path)
    arch_path = Path(args.architecture)
    output_dir = Path(output_dir)

    if not prd_path.exists():
        print(f"❌ PRD 文件不存在: {prd_path}")
        return 1

    if not arch_path.exists():
        print(f"❌ 架构文件不存在: {arch_path}")
        return 1

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

        return 0

    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断，进度已保存，可以使用相同参数继续执行")
        return 130
    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
