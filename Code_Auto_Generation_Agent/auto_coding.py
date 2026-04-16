#!/usr/bin/env python3
"""
auto_coding.py - 全自动代码生成Agent命令行入口
根据prd.json自动调用AI逐个实现用户故事
"""

import argparse
import sys
import os
from config import get_config, Config
from core.generator import GenerationEngine
from utils.logger import setup_logger
from utils.logger import get_logger


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Auto Coding Agent - Generate code from PRD JSON'
    )
    parser.add_argument(
        'prd_path',
        help='Path to prd.json file'
    )
    parser.add_argument(
        '--target-dir',
        help='Target directory where code will be generated (default: output/<prd-filename>)'
    )
    parser.add_argument(
        '--tool',
        choices=['claude', 'openai'],
        help='AI tool to use (overrides .env config, same as Requirements_Analysis_Agent)'
    )
    parser.add_argument(
        '--max-stories',
        type=int,
        help='Maximum number of stories to process (stop after N stories for testing)'
    )
    parser.add_argument(
        '--retries',
        type=int,
        help='Maximum retries per story (default: from .env)'
    )
    parser.add_argument(
        '--fix-attempts',
        type=int,
        help='Maximum fix attempts per story (default: from .env)'
    )
    parser.add_argument(
        '--no-git',
        action='store_true',
        help='Disable git auto commit'
    )
    parser.add_argument(
        '--no-quality-check',
        action='store_true',
        help='Disable quality checking (lint, type check, test)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from existing progress file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only print plan, do not actually generate code'
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    logger = setup_logger()

    # 加载配置
    config = get_config()

    # 命令行参数覆盖配置
    if args.tool:
        config.ai_backend = args.tool
    if args.retries:
        config.max_retries = args.retries
    if args.fix_attempts:
        config.max_fix_attempts = args.fix_attempts
    if args.no_git:
        config.git_auto_commit = False
    if args.no_quality_check:
        config.quality_check_cmd = None
        config.type_check_cmd = None
        config.test_cmd = None

    # 验证prd文件存在
    if not os.path.exists(args.prd_path):
        logger.error(f"PRD file not found: {args.prd_path}")
        sys.exit(1)

    # 如果没有指定target-dir，自动生成默认路径
    if not args.target_dir:
        # 获取prd文件名（不含扩展名）作为目录名
        prd_basename = os.path.basename(args.prd_path)
        # 去掉扩展名 .json
        dir_name = os.path.splitext(prd_basename)[0]
        # 默认放在 output/ 目录下
        target_dir = os.path.join("output", dir_name)
        logger.info(f"No target directory specified, using default: {target_dir}")
    else:
        target_dir = args.target_dir

    # 确保目标目录存在
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Created target directory: {target_dir}")

    # 创建并运行生成引擎
    engine = GenerationEngine(
        config=config,
        prd_path=args.prd_path,
        target_dir=target_dir,
        max_stories=args.max_stories,
        dry_run=args.dry_run
    )

    logger.info(f"Starting auto coding with AI tool: {config.ai_backend}")
    summary = engine.run()

    if not summary['success']:
        logger.error(f"Generation failed: {summary.get('error', 'Unknown error')}")
        sys.exit(1)

    # 打印总结
    logger.info("=" * 60)
    logger.info("Generation Complete!")
    logger.info(f"Project: {summary['project_name']}")
    logger.info(f"Total stories: {summary['total_stories']}")
    logger.info(f"Completed: {summary['completed_stories']}")
    logger.info(f"Failed: {summary['failed_stories']}")
    logger.info(f"Output directory: {summary['target_dir']}")

    if summary['lessons_learned']:
        logger.info("Lessons learned:")
        for lesson in summary['lessons_learned'][-5:]:
            logger.info(f"  {lesson}")

    logger.info("=" * 60)

    if summary['failed_stories'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
