"""主生成引擎 - 控制整个生成流程"""

from typing import Dict, List, Optional

from config import Config
from core.ai_backend import AIBackend
from core.architecture_loader import ArchitectureDocument, load_architecture
from core.claude_cli import ClaudeCLIBackend
from core.git_manager import GitManager
from core.openai_api import OpenAIBackend
from core.prd_loader import PRD, load_prd
from core.progress_tracker import ProgressTracker
from core.quality_checker import QualityChecker
from core.scaffold_generator import ScaffoldGenerator
from core.story_manager import StoryManager, StoryState
from core.toolcall_agent import ToolCallingAgent
from prompts import get_implementation_prompt
from utils.file_utils import ensure_dir
from utils.logger import get_logger

logger = get_logger()


class GenerationEngine:
    """主生成引擎"""

    def __init__(
        self,
        config: Config,
        prd_path: str,
        target_dir: str,
        architecture_path: Optional[str] = None,
        max_stories: Optional[int] = None,
        dry_run: bool = False
    ):
        self.config = config
        self.prd_path = prd_path
        self.architecture_path = architecture_path
        self.target_dir = target_dir
        self.max_stories = max_stories
        self.dry_run = dry_run

        # 初始化组件
        self.prd: Optional[PRD] = None
        self.architecture: Optional[ArchitectureDocument] = None
        self.story_manager: Optional[StoryManager] = None
        self.progress_tracker: Optional[ProgressTracker] = None
        self.ai_backend: Optional[AIBackend] = None
        self.quality_checker: Optional[QualityChecker] = None
        self.git_manager: Optional[GitManager] = None
        self.scaffold_generator: Optional[ScaffoldGenerator] = None

        # 任务级代码缓存：{story_id: [{"file_path": "...", "content": "..."}]}
        # 用于确保后续任务与依赖任务接口完全一致
        self.generated_code_cache: Dict[str, List[Dict[str, str]]] = {}

    def initialize(self) -> bool:
        """初始化引擎"""
        logger.info("正在初始化生成引擎")

        # 确保目标目录存在
        ensure_dir(self.target_dir)

        # 加载PRD
        self.prd = load_prd(self.prd_path)
        if self.prd is None:
            logger.error("加载PRD失败")
            return False

        # 加载架构文档
        if self.architecture_path:
            self.architecture = load_architecture(self.architecture_path)
            if self.architecture is None:
                logger.error("加载架构文档失败")
                return False
            logger.info("架构文档加载完成")

        # 初始化故事管理器
        self.story_manager = StoryManager(self.prd, self.config)

        # 初始化进度跟踪器
        self.progress_tracker = ProgressTracker(
            output_dir=self.target_dir,
            project_name=self.prd.project_name,
            branch_name=self.prd.branch_name,
            ai_backend=self.config.ai_backend
        )

        # 尝试恢复进度
        if self.progress_tracker.has_progress():
            logger.info("发现现有进度文件，尝试恢复")
            progress_data = self.progress_tracker.load()
            if progress_data:
                self.story_manager.load_from_progress(progress_data)
                # 如果进度中已有AI生成的构建命令，加载到质量检查器
                build_commands = self.progress_tracker.get_build_commands()
                if build_commands and self.quality_checker:
                    # 将保存的命令注入到quality_checker
                    self.quality_checker.ai_commands = build_commands

        # 初始化AI后端
        if not self._init_ai_backend():
            return False

        # 初始化质量检查器
        # 所有命令完全由AI动态决定，不需要用户配置
        self.quality_checker = QualityChecker(
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
            logger.info("目标目录不是Git仓库，正在初始化...")
            if not self.git_manager.init_repo():
                logger.warning("初始化Git仓库失败，Git操作已禁用")
            else:
                logger.info("Git仓库初始化完成，正在创建分支...")
                self.git_manager.create_branch(self.prd.branch_name)
        else:
            logger.info("目标目录已经是Git仓库")
            self.git_manager.create_branch(self.prd.branch_name)

        # 生成项目骨架（如果有架构文档）
        if self.architecture and not self.dry_run:
            logger.info("开始生成项目骨架...")
            self.scaffold_generator = ScaffoldGenerator(
                architecture=self.architecture,
                target_dir=self.target_dir,
                ai_backend=self.ai_backend
            )
            scaffold_success = self.scaffold_generator.generate_all()
            if not scaffold_success:
                logger.warning("项目骨架生成有警告，但继续处理用户故事")
            else:
                logger.info("项目骨架生成完成")

        logger.info("生成引擎初始化成功")
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
                logger.error("OpenAI API key 未配置，请在 .env 中设置 OPENAI_API_KEY")
                return False

            # 根据 use_agent_mode 选择不同的后端
            if getattr(self.config, 'use_agent_mode', False):
                logger.info("使用 ReAct Agent 模式（工具调用模式）")
                self.ai_backend = ToolCallingAgent(
                    api_key=self.config.openai_api_key,
                    model=self.config.openai_model,
                    base_url=self.config.openai_base_url,
                    working_dir=self.target_dir,
                )
            else:
                logger.info("使用传统单次调用模式")
                self.ai_backend = OpenAIBackend(
                    api_key=self.config.openai_api_key,
                    model=self.config.openai_model,
                    base_url=self.config.openai_base_url,
                    working_dir=self.target_dir,
                    max_tokens=self.config.max_tokens,
                    max_retries=self.config.max_retries,
                )
        else:
            logger.error(f"未知AI工具: {self.config.ai_backend}，应为 'claude' 或 'openai'")
            return False

        if not self.ai_backend.is_available():
            logger.error(f"AI工具 {self.config.ai_backend} 不可用")
            return False

        logger.info(f"AI工具已初始化: {self.config.ai_backend}")
        return True

    def run(self) -> dict:
        """运行生成流程"""
        if not self.initialize():
            return {"success": False, "error": "初始化失败"}

        if self.dry_run:
            logger.info("干运行模式，不实际生成，直接退出")
            return self._get_summary()

        completed_count = 0
        stories_processed = 0

        while True:
            # 检查是否所有故事都完成
            if self.story_manager.is_all_completed():
                logger.info("所有用户故事已完成!")
                break

            # 检查是否达到max_stories限制
            if self.max_stories and stories_processed >= self.max_stories:
                logger.info(f"已达到最大故事数量限制 ({self.max_stories})，停止")
                break

            # 获取下一个故事
            story = self.story_manager.get_next_story()
            if story is None:
                logger.info("没有更多待处理故事")
                break

            stories_processed += 1
            self._process_story(story)
            self.progress_tracker.save(self.story_manager)

            if story.status == "completed":
                completed_count += 1

        # 最终总结
        summary = self._get_summary()
        logger.info("生成完成")
        logger.info(f"总计: {summary['total_stories']}, 已完成: {summary['completed_stories']}, 失败: {summary['failed_stories']}")

        return summary

    def _process_story(self, story: StoryState):
        """处理单个用户故事"""
        logger.info(f"正在处理故事: {story.id} - {story.title}")
        self.story_manager.mark_in_progress(story)

        # 收集依赖任务的已生成代码（确保接口一致性）
        dependency_context = []
        if story.dependencies:
            logger.info(f"收集 {len(story.dependencies)} 个依赖任务的代码上下文")
            for dep_id in story.dependencies:
                if dep_id in self.generated_code_cache:
                    files = self.generated_code_cache[dep_id]
                    dependency_context.append(f"## 依赖任务 {dep_id} 已生成代码\n")
                    for f in files:
                        dependency_context.append(f"--- {f['file_path']} ---")
                        dependency_context.append(f["content"])
                        dependency_context.append("")
                    logger.info(f"  - {dep_id}: {len(files)} 个文件")
                else:
                    logger.warning(f"  - {dep_id}: 未在缓存中找到")

        # 构建prompt（注入依赖代码）
        prompt = get_implementation_prompt(
            story=story,
            project_description=self.prd.description,
            lessons_learned=self.progress_tracker.lessons_learned,
            target_dir=self.target_dir,
            architecture=self.architecture,
            dependency_code="\n".join(dependency_context)
        )

        try:
            # 调用AI实现
            logger.info(f"调用 {self.config.ai_backend} 实现故事...")
            if self.dry_run:
                return

            self.ai_backend.implement_story(prompt)

            # 如果是 ToolCallingAgent，缓存生成的文件供后续任务使用
            if hasattr(self.ai_backend, 'get_generated_files'):
                generated_files = self.ai_backend.get_generated_files()
                self.generated_code_cache[story.id] = generated_files
                logger.info(f"已缓存 {len(generated_files)} 个生成文件供后续任务使用")

            # 运行质量检查（如果启用）
            if self.config.quality_check_enabled and self.quality_checker.is_enabled():
                result = self.quality_checker.run_all(
                    working_dir=self.target_dir,
                    ai_backend=self.ai_backend,
                    project_description=self.prd.description
                )

                # 如果AI生成了构建命令，保存到进度跟踪器
                ai_commands = self.quality_checker.get_ai_commands()
                if ai_commands and self.progress_tracker:
                    self.progress_tracker.set_build_commands(
                        install=ai_commands.get('install', []),
                        quality_check=ai_commands.get('quality_check', []),
                        type_check=ai_commands.get('type_check', []),
                        test=ai_commands.get('test', [])
                    )

                # 如果不通过，尝试修复
                fix_attempts = 0
                while not result.passed and fix_attempts < self.config.max_fix_attempts:
                    # 打印当前错误信息
                    logger.warning(f"质量检查失败，第 {fix_attempts + 1}/{self.config.max_fix_attempts} 次修复尝试，当前错误：")
                    for i, err in enumerate(result.errors, 1):
                        logger.warning(f"[错误 {i}/{len(result.errors)}]\n{err}\n")
                    logger.warning("正在调用AI修复...")

                    # 核心设计理念：把完整错误信息发给AI，让AI自己决定需要改什么
                    # 不需要猜测是命令问题还是代码问题，AI有完整上下文能做正确判断
                    logger.info("调用AI修复代码...")
                    self.ai_backend.fix_errors(prompt, result.errors, self.target_dir)

                    # 决定从哪个阶段开始重试
                    start_from_stage = 1
                    need_restart_install = False

                    # 如果错误包含"command not found"/"No module named"，说明新增了依赖但没安装
                    # 需要强制从头安装，不能从失败阶段继续
                    for err in result.errors:
                        if ("command not found" in err.lower()
                            or "program not found" in err.lower()
                            or "no module named" in err.lower()
                            or "cannot find module" in err.lower()
                            or "cannot find package" in err.lower()
                            or "err_module_not_found" in err.lower()
                            or "認識されていません" in err  # Japanese Windows
                            or "不能被识别为" in err  # Chinese Windows
                            or "不是内部或外部命令" in err):  # Chinese Windows
                            need_restart_install = True
                            break

                    if need_restart_install:
                        logger.info("检测到缺少命令/模块错误，需要重新运行安装阶段")
                        start_from_stage = 1
                    else:
                        # 正常情况：从上次失败的阶段开始重试，不重复已经成功的阶段
                        # 例如：上次安装成功了，失败在质量检查，这次从质量检查开始
                        start_from_stage = result.failed_stage if result.failed_stage > 0 else 1

                    result = self.quality_checker.run_all(
                        working_dir=self.target_dir,
                        ai_backend=self.ai_backend,
                        project_description=self.prd.description,
                        start_from_stage=start_from_stage
                    )

                    # 更新构建命令到进度跟踪器
                    ai_commands = self.quality_checker.get_ai_commands()
                    if ai_commands and self.progress_tracker:
                        self.progress_tracker.set_build_commands(
                            install=ai_commands.get('install', []),
                            quality_check=ai_commands.get('quality_check', []),
                            type_check=ai_commands.get('type_check', []),
                            test=ai_commands.get('test', [])
                        )

                    fix_attempts += 1

                if not result.passed:
                    # 修复失败，打印所有错误信息到日志
                    logger.error(f"故事 {story.id} 经过 {fix_attempts} 次修复尝试后质量检查仍然失败，错误信息汇总：")
                    for i, err in enumerate(result.errors, 1):
                        logger.error(f"[错误 {i}/{len(result.errors)}]\n{err}\n")
                    # 标记失败
                    self.story_manager.mark_failed(story, result.errors)
                    self.progress_tracker.add_lesson(f"{story.id} {story.title} 经过 {fix_attempts} 次修复尝试后质量检查仍然失败")
                    return

            # 质量检查通过，提交
            commit_hash = None
            if self.git_manager:
                commit_hash = self.git_manager.commit(story.id, story.title)

            # 标记完成
            self.story_manager.mark_completed(story, commit_hash)
            logger.info(f"故事 {story.id} 成功完成")

        except Exception as e:
            logger.error(f"处理故事 {story.id} 失败: {str(e)}")
            self.story_manager.mark_failed(story, [str(e)])
            self.progress_tracker.add_lesson(f"{story.id} {story.title} 发生错误: {str(e)}")

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
