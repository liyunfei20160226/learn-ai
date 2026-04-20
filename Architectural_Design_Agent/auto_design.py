#!/usr/bin/env python3
"""
auto_design.py - 全自动架构设计Agent命令行入口
根据prd.json自动调用AI生成architecture.json
"""

import argparse
import os
import sys

# 强制设置标准输出编码为UTF-8，解决Windows控制台中文乱码问题
if sys.version_info >= (3, 7):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from config import get_config
from core.architecture_generator import ArchitectureGenerator
from core.prd_loader import load_prd
from utils.logger import setup_logger


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Automatic Architecture Design Agent - Generate architecture.json from PRD'
    )
    parser.add_argument(
        'prd_path',
        help='Path to prd.json file'
    )
    parser.add_argument(
        '--output-dir',
        help='Output directory for architecture.json (default: {OUTPUT_BASE_DIR}/{prd-filename})'
    )
    parser.add_argument(
        '--tool',
        choices=['claude', 'openai'],
        help='AI tool to use (overrides .env config)'
    )
    parser.add_argument(
        '--retries',
        type=int,
        help='Maximum retries if generation fails (default: from .env)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only print plan, do not actually call AI'
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

    # 验证prd文件存在
    if not os.path.exists(args.prd_path):
        logger.error(f"PRD文件不存在: {args.prd_path}")
        sys.exit(1)

    # 获取PRD文件名前缀（去掉.prd.json扩展名）
    prd_basename = os.path.basename(args.prd_path)
    # 处理 .prd.json 扩展名
    if prd_basename.endswith('.prd.json'):
        prd_filename_prefix = prd_basename[:-9]
    else:
        prd_filename_prefix = os.path.splitext(prd_basename)[0]

    # 如果没有指定输出目录，自动生成默认路径
    if not args.output_dir:
        output_dir = os.path.join(config.output_base_dir, prd_filename_prefix)
        logger.info(f"未指定输出目录，使用默认路径: {output_dir}")
    else:
        output_dir = args.output_dir

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"已创建输出目录: {output_dir}")

    # 加载PRD
    logger.info(f"加载PRD: {args.prd_path}")
    prd = load_prd(args.prd_path)
    if prd is None:
        logger.error("加载PRD失败")
        sys.exit(1)

    logger.info(f"项目: {prd.project}")
    logger.info(f"用户故事数量: {len(prd.user_stories)}")

    # 创建并运行生成引擎
    engine = ArchitectureGenerator(
        config=config,
        prd=prd,
        output_dir=output_dir,
        prd_filename_prefix=prd_filename_prefix,
        max_retries=args.retries,
        dry_run=args.dry_run
    )

    logger.info("开始架构设计...")
    architecture, error = engine.generate()

    if architecture is None:
        logger.error(f"架构生成失败: {error}")
        sys.exit(1)

    # 保存结果
    output_path = engine.save(architecture)
    if not output_path:
        logger.error("保存架构失败")
        sys.exit(1)

    # 打印总结
    logger.info("=" * 60)
    logger.info("架构设计完成!")
    logger.info(f"项目: {prd.project}")
    logger.info(f"输出文件: {output_path}")
    logger.info(f"接下来可以将 {prd_filename_prefix}.architecture.json 复制到 Code_Auto_Generation_Agent 项目目录进行自动化开发")
    logger.info("=" * 60)

    sys.exit(0)


if __name__ == '__main__':
    main()
