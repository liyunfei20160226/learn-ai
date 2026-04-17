"""进度跟踪器 - 保存progress.json学习经验"""

import os
from datetime import datetime
from typing import Dict, List, Optional

from core.story_manager import StoryManager
from utils.file_utils import read_json, write_json
from utils.logger import get_logger

logger = get_logger()


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, output_dir: str, project_name: str, branch_name: str, ai_backend: str):
        self.output_dir = output_dir
        self.project_name = project_name
        self.branch_name = branch_name
        self.ai_backend = ai_backend
        self.progress_file = os.path.join(output_dir, "progress.json")
        self.lessons_learned: List[str] = []
        # 保存AI动态决定的构建和检查命令
        self.build_commands: Optional[Dict[str, List[str]]] = None
        self.started_at = datetime.now().isoformat()

    def load(self) -> Optional[dict]:
        """加载现有进度"""
        data = read_json(self.progress_file)
        if data is None:
            return None

        # 加载经验教训
        if 'lessons_learned' in data:
            self.lessons_learned = data['lessons_learned']
        # 加载构建/检查命令
        if 'build_commands' in data:
            self.build_commands = data['build_commands']

        logger.info(f"已从 {self.progress_file} 加载现有进度")
        return data

    def save(self, story_manager: StoryManager):
        """保存当前进度"""
        counts = story_manager.count_by_status()
        data = {
            'project_name': self.project_name,
            'branch_name': self.branch_name,
            'ai_backend': self.ai_backend,
            'started_at': self.started_at,
            'last_updated': datetime.now().isoformat(),
            'total_stories': len(story_manager.get_all_stories()),
            'completed_stories': counts['completed'],
            'failed_stories': counts['failed'],
            'stories': story_manager.to_dict_list(),
            'lessons_learned': self.lessons_learned,
            'build_commands': self.build_commands
        }

        success = write_json(self.progress_file, data)
        if success:
            logger.debug(f"进度已保存到 {self.progress_file}")
        else:
            logger.error(f"保存进度到 {self.progress_file} 失败")

        return success

    def add_lesson(self, lesson: str):
        """添加经验教训"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lessons_learned.append(f"[{timestamp}] {lesson}")

    def set_build_commands(self, install: List[str], quality_check: List[str], type_check: List[str], test: List[str]):
        """保存AI决定的构建和检查命令"""
        self.build_commands = {
            'install': install,
            'quality_check': quality_check,
            'type_check': type_check,
            'test': test
        }

    def get_build_commands(self) -> Optional[Dict[str, List[str]]]:
        """获取构建和检查命令"""
        return self.build_commands

    def has_progress(self) -> bool:
        """是否已有进度文件"""
        return os.path.exists(self.progress_file)

    def get_summary(self) -> dict:
        """获取进度总结"""
        return {
            'project_name': self.project_name,
            'started_at': self.started_at,
            'lessons_count': len(self.lessons_learned),
            'lessons_learned': self.lessons_learned,
            'build_commands': self.build_commands
        }
