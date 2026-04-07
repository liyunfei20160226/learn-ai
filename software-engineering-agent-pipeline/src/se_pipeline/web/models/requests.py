"""
Pydantic request models for web API
"""
from pydantic import BaseModel, field_validator
import re


class CreateProjectRequest(BaseModel):
    """创建新项目请求"""
    project_id: str
    project_name: str
    original_requirement: str

    @field_validator('project_id')
    def validate_project_id(cls, v):
        """项目ID只能包含字母数字下划线横杠"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Project ID can only contain letters, numbers, underscores, and hyphens')
        return v


class AnswerQuestionsRequest(BaseModel):
    """提交问题答案请求"""
    answers: list[dict[str, str]]
    """answers: 列表，每项包含 question 和 answer"""


class DeleteProjectRequest(BaseModel):
    """删除项目请求"""
    project_id: str
