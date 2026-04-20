"""PRD加载器 - 加载并解析输入的prd.json"""
from dataclasses import dataclass
from typing import List, Optional

from utils.file_utils import read_json
from utils.logger import get_logger

logger = get_logger()


@dataclass
class UserStory:
    """PRD中的用户故事"""
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: int
    passes: bool
    notes: str


@dataclass
class PRD:
    """产品需求文档"""
    project: str
    branch_name: str
    description: str
    user_stories: List[UserStory]


def load_prd(prd_path: str) -> Optional[PRD]:
    """加载PRD JSON文件"""
    data = read_json(prd_path)
    if data is None:
        return None

    try:
        # 支持两种字段名格式：camelCase (from Requirements_Analysis_Agent) 和 snake_case
        project_name = data.get("project") or data.get("projectName", "Unknown Project")
        branch_name = data.get("branchName") or data.get("branch_name", "autodesign/main")
        description = data.get("description", "")

        user_stories_list = data.get("userStories") or data.get("user_stories", [])

        user_stories = []
        for i, story_data in enumerate(user_stories_list):
            user_stories.append(UserStory(
                id=story_data.get("id") or f"US-{i+1:03d}",
                title=story_data.get("title", ""),
                description=story_data.get("description", ""),
                acceptance_criteria=story_data.get("acceptanceCriteria") or story_data.get("acceptance_criteria", []),
                priority=story_data.get("priority", 1),
                passes=story_data.get("passes", False),
                notes=story_data.get("notes", "")
            ))

        return PRD(
            project=project_name,
            branch_name=branch_name,
            description=description,
            user_stories=user_stories
        )

    except Exception as e:
        logger.error(f"解析PRD失败: {e}")
        return None
