"""PRD加载器 - 读取和解析prd.json"""

from typing import List, Optional
from dataclasses import dataclass
import os
from utils.file_utils import read_json
from utils.logger import get_logger


logger = get_logger()


@dataclass
class UserStory:
    """用户故事"""
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: int
    passes: bool = False
    notes: str = ""


@dataclass
class PRD:
    """产品需求文档"""
    project: str
    project_name: str
    branchName: str
    branch_name: str
    description: str
    userStories: List[UserStory]
    user_stories: List[UserStory]


def _convert_legacy_prd(data: dict) -> dict:
    """转换可能的不同字段命名（兼容legacy格式）"""
    converted = data.copy()

    # 兼容 camelCase <-> snake_case
    if 'project' in converted and 'project_name' not in converted:
        converted['project_name'] = converted['project']
    if 'project_name' in converted and 'project' not in converted:
        converted['project'] = converted['project_name']

    if 'branchName' in converted and 'branch_name' not in converted:
        converted['branch_name'] = converted['branchName']
    if 'branch_name' in converted and 'branchName' not in converted:
        converted['branchName'] = converted['branch_name']

    if 'userStories' in converted and 'user_stories' not in converted:
        converted['user_stories'] = converted['userStories']
    if 'user_stories' in converted and 'userStories' not in converted:
        converted['userStories'] = converted['user_stories']

    return converted


def load_prd(prd_path: str) -> Optional[PRD]:
    """加载并解析prd.json"""
    if not os.path.exists(prd_path):
        logger.error(f"PRD file not found: {prd_path}")
        return None

    data = read_json(prd_path)
    if data is None:
        logger.error(f"Failed to read PRD from {prd_path}")
        return None

    try:
        data = _convert_legacy_prd(data)

        user_stories = []
        stories_data = data.get('userStories', data.get('user_stories', []))

        for idx, story_data in enumerate(stories_data):
            # 生成id如果没有
            story_id = story_data.get('id', story_data.get('story_id', f"US-{idx+1:03d}"))
            title = story_data.get('title', '')
            description = story_data.get('description', '')
            acceptance_criteria = story_data.get('acceptanceCriteria', story_data.get('acceptance_criteria', []))
            priority = story_data.get('priority', idx + 1)
            passes = story_data.get('passes', story_data.get('completed', False))
            notes = story_data.get('notes', '')

            story = UserStory(
                id=story_id,
                title=title,
                description=description,
                acceptance_criteria=acceptance_criteria,
                priority=priority,
                passes=passes,
                notes=notes
            )
            user_stories.append(story)

        prd = PRD(
            project=data.get('project', data.get('project_name', 'Unknown Project')),
            project_name=data.get('project_name', data.get('project', 'Unknown Project')),
            branchName=data.get('branchName', data.get('branch_name', 'auto-coding')),
            branch_name=data.get('branch_name', data.get('branchName', 'auto-coding')),
            description=data.get('description', ''),
            userStories=user_stories,
            user_stories=user_stories
        )

        logger.info(f"Loaded PRD: {prd.project_name}, {len(prd.user_stories)} user stories")
        return prd

    except Exception as e:
        logger.error(f"Failed to parse PRD: {str(e)}")
        return None
