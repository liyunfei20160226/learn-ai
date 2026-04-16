"""主生成引擎 - 控制整个生成流程"""

import os
from typing import Optional, List
from config import Config
from core.prd_loader import PRD, load_prd
from core.story_manager import StoryManager, StoryState
from core.progress_tracker import ProgressTracker
from core.ai_backend import AIBackend
from core.claude_cli import ClaudeCLIBackend
from core.openai_api import OpenAIBackend
from core.quality_checker import QualityChecker, QualityCheckResult
from core.git_manager import GitManager
from utils.logger import get_logger
from utils.file_utils import read_file, ensure_dir
from prompts import get_implementation_prompt


logger = get_logger()


class GenerationEngine:
    """主生成引擎"""

    def __init__(
        self,
        config: Config,
        prd_path: str,
        target_dir: str,
        max_stories: Optional[int] = None,
        dry_run: bool = False
    ):
        self.config = config
        self.prd_path = prd_path
        self.target_dir = target_dir
        self.max_stories = max_stories
        self.dry_run = dry_run

        # 初始化组件
        self.prd: Optional[PRD] = None
        self.story_manager: Optional[StoryManager] = None
        self.progress_tracker: Optional[ProgressTracker] = None
        self.ai_backend: Optional[AIBackend] = None
        self.quality_checker: Optional[QualityChecker] = None
        self.git_manager: Optional[GitManager] = None

    def initialize(self) -> bool:
        """初始化引擎"""
        logger.info("Initializing generation engine")

        # 确保目标目录存在
        ensure_dir(self.target_dir)

        # 加载PRD
        self.prd = load_prd(self.prd_path)
        if self.prd is None:
            logger.error("Failed to load PRD")
            return False

        # 初始化故事管理器
        self.story_manager = StoryManager(self.prd)

        # 初始化进度跟踪器
        self.progress_tracker = ProgressTracker(
            output_dir=self.target_dir,
            project_name=self.prd.project_name,
            branch_name=self.prd.branch_name,
            ai_backend=self.config.ai_backend
        )

        # 尝试恢复进度
        if self.progress_tracker.has_progress():
            logger.info("Found existing progress file, attempting to resume")
            progress_data = self.progress_tracker.load()
            if progress_data:
                self.story_manager.load_from_progress(progress_data)

        # 初始化AI后端
        if not self._init_ai_backend():
            return False

        # 初始化质量检查器
        # 如果配置为空，QualityChecker会自动探测项目语言并设置默认命令
        self.quality_checker = QualityChecker(
            quality_check_cmd=self.config.quality_check_cmd,
            type_check_cmd=self.config.type_check_cmd,
            test_cmd=self.config.test_cmd,
            working_dir=self.target_dir
        )

        # 初始化Git管理器
        self.git_manager = GitManager(
            working_dir=self.target_dir,
            auto_commit=self.config.git_auto_commit
        )

        # 准备git和分支
        if not self.git_manager.is_git_repo():
            # 目标目录不是git仓库，自动初始化
            logger.info("Target directory is not a git repository, initializing...")
            if not self.git_manager.init_repo():
                logger.warning("Failed to initialize git repository, Git operations disabled")
            else:
                logger.info("Git repository initialized, creating branch...")
                self.git_manager.create_branch(self.prd.branch_name)
        else:
            logger.info("Target directory is already a git repository")
            self.git_manager.create_branch(self.prd.branch_name)

        logger.info("Generation engine initialized successfully")
        return True

    def _init_ai_backend(self) -> bool:
        """初始化AI后端"""
        if self.config.ai_backend == "claude":
            self.ai_backend = ClaudeCLIBackend(
                claude_cmd=self.config.claude_cmd,
                working_dir=self.target_dir
            )
        elif self.config.ai_backend == "openai":
            if not self.config.openai_api_key:
                logger.error("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
                return False
            self.ai_backend = OpenAIBackend(
                api_key=self.config.openai_api_key,
                model=self.config.openai_model,
                base_url=self.config.openai_base_url,
                working_dir=self.target_dir
            )
        else:
            logger.error(f"Unknown AI tool: {self.config.ai_backend}. Expected 'claude' or 'openai'")
            return False

        if not self.ai_backend.is_available():
            logger.error(f"AI tool {self.config.ai_backend} is not available")
            return False

        logger.info(f"AI tool initialized: {self.config.ai_backend}")
        return True

    def run(self) -> dict:
        """运行生成流程"""
        if not self.initialize():
            return {"success": False, "error": "Initialization failed"}

        if self.dry_run:
            logger.info("Dry run mode enabled, exiting without actual generation")
            return self._get_summary()

        completed_count = 0
        stories_processed = 0

        while True:
            # 检查是否所有故事都完成
            if self.story_manager.is_all_completed():
                logger.info("All user stories completed!")
                break

            # 检查是否达到max_stories限制
            if self.max_stories and stories_processed >= self.max_stories:
                logger.info(f"Reached max stories limit ({self.max_stories}), stopping")
                break

            # 获取下一个故事
            story = self.story_manager.get_next_story()
            if story is None:
                logger.info("No more pending stories")
                break

            stories_processed += 1
            self._process_story(story)
            self.progress_tracker.save(self.story_manager)

            if story.status == "completed":
                completed_count += 1

        # 最终总结
        summary = self._get_summary()
        logger.info("Generation completed")
        logger.info(f"Total: {summary['total_stories']}, Completed: {summary['completed_stories']}, Failed: {summary['failed_stories']}")

        return summary

    def _process_story(self, story: StoryState):
        """处理单个用户故事"""
        logger.info(f"Processing story: {story.id} - {story.title}")
        self.story_manager.mark_in_progress(story)

        # 构建prompt
        prompt = get_implementation_prompt(
            story=story,
            project_description=self.prd.description,
            lessons_learned=self.progress_tracker.lessons_learned,
            target_dir=self.target_dir
        )

        try:
            # 调用AI实现
            logger.info(f"Calling {self.config.ai_backend} to implement story...")
            if self.dry_run:
                return

            output = self.ai_backend.implement_story(prompt)

            # 运行质量检查
            if self.quality_checker.is_enabled():
                result = self.quality_checker.run_all(working_dir=self.target_dir)

                # 如果不通过，尝试修复
                fix_attempts = 0
                while not result.passed and fix_attempts < self.config.max_fix_attempts:
                    logger.warning(f"Quality check failed, attempt {fix_attempts + 1}/{self.config.max_fix_attempts} to fix")
                    output = self.ai_backend.fix_errors(prompt, result.errors)
                    result = self.quality_checker.run_all(working_dir=self.target_dir)
                    fix_attempts += 1

                if not result.passed:
                    # 修复失败
                    error_messages = [f"Fix attempt {i + 1}: " + "\n".join(e for e in result.errors)
                                     for i, result in enumerate([result])]
                    self.story_manager.mark_failed(story, result.errors)
                    self.progress_tracker.add_lesson(f"{story.id} {story.title} failed quality check after {fix_attempts} fix attempts")
                    return

            # 质量检查通过，提交
            commit_hash = None
            if self.git_manager:
                commit_hash = self.git_manager.commit(story.id, story.title)

            # 标记完成
            self.story_manager.mark_completed(story, commit_hash)
            logger.info(f"Story {story.id} completed successfully")

        except Exception as e:
            logger.error(f"Failed to process story {story.id}: {str(e)}")
            self.story_manager.mark_failed(story, [str(e)])
            self.progress_tracker.add_lesson(f"{story.id} {story.title} failed with error: {str(e)}")

    def _get_summary(self) -> dict:
        """获取生成总结"""
        counts = self.story_manager.count_by_status()
        return {
            "success": True,
            "project_name": self.prd.project_name,
            "total_stories": len(self.story_manager.get_all_stories()),
            "completed_stories": counts['completed'],
            "failed_stories": counts['failed'],
            "pending_stories": counts['pending'],
            "lessons_learned": self.progress_tracker.lessons_learned,
            "target_dir": self.target_dir
        }
