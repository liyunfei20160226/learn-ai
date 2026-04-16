"""用户故事管理器 - 跟踪完成状态，选择下一个故事"""

from typing import List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from core.prd_loader import PRD, UserStory
from utils.logger import get_logger
from utils.file_utils import read_json, write_json


logger = get_logger()


@dataclass
class StoryState:
    """故事状态"""
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: int
    status: str  # pending, in_progress, completed, failed
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    commit_hash: Optional[str] = None
    retries: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class StoryManager:
    """用户故事管理器"""

    def __init__(self, prd: PRD):
        self.prd = prd
        self.states: List[StoryState] = []
        self._init_states()

    def _init_states(self):
        """从PRD初始化状态"""
        for story in self.prd.user_stories:
            status = "completed" if story.passes else "pending"
            state = StoryState(
                id=story.id,
                title=story.title,
                description=story.description,
                acceptance_criteria=story.acceptance_criteria,
                priority=story.priority,
                status=status
            )
            self.states.append(state)

        # 按优先级排序
        self.states.sort(key=lambda s: s.priority)

    def load_from_progress(self, progress_data: dict) -> bool:
        """从进度文件恢复状态"""
        if 'stories' not in progress_data:
            logger.warning("进度数据中没有故事信息")
            return False

        try:
            story_map = {s.id: s for s in self.states}
            for loaded_story in progress_data['stories']:
                if loaded_story['id'] in story_map:
                    # 更新状态
                    story = story_map[loaded_story['id']]
                    story.status = loaded_story.get('status', story.status)
                    story.completed_at = loaded_story.get('completed_at')
                    story.failed_at = loaded_story.get('failed_at')
                    story.commit_hash = loaded_story.get('commit_hash')
                    story.retries = loaded_story.get('retries', 0)
                    story.errors = loaded_story.get('errors', [])

            logger.info(f"已从进度恢复 {len(progress_data['stories'])} 个故事")
            return True
        except Exception as e:
            logger.error(f"从进度恢复失败: {str(e)}")
            return False

    def get_next_story(self) -> Optional[StoryState]:
        """获取下一个待完成的故事（按优先级）"""
        # 按优先级排序，找到第一个pending
        for state in sorted(self.states, key=lambda s: s.priority):
            if state.status == 'pending':
                return state
        return None

    def mark_in_progress(self, story: StoryState):
        """标记为进行中"""
        story.status = 'in_progress'

    def mark_completed(self, story: StoryState, commit_hash: Optional[str] = None):
        """标记为已完成"""
        story.status = 'completed'
        story.completed_at = datetime.now().isoformat()
        story.commit_hash = commit_hash

    def mark_failed(self, story: StoryState, errors: List[str]):
        """标记为失败"""
        story.status = 'failed'
        story.failed_at = datetime.now().isoformat()
        story.errors.extend(errors)
        story.retries += 1

    def retry_story(self, story: StoryState) -> bool:
        """是否可以重试"""
        return story.retries < getattr(self, 'max_retries', 3)

    def get_all_stories(self) -> List[StoryState]:
        """获取所有故事"""
        return self.states

    def count_by_status(self) -> dict:
        """统计各状态数量"""
        counts = {'pending': 0, 'in_progress': 0, 'completed': 0, 'failed': 0}
        for state in self.states:
            counts[state.status] += 1
        return counts

    def is_all_completed(self) -> bool:
        """是否所有都完成"""
        return all(s.status == 'completed' for s in self.states)

    def to_dict_list(self) -> List[dict]:
        """转换为字典列表用于保存"""
        return [asdict(s) for s in self.states]
