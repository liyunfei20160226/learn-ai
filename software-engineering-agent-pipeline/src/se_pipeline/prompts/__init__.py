"""
提示词模板管理
"""
import os
from typing import Dict


_PROMPT_CACHE: Dict[str, str] = {}


def get_prompt(name: str) -> str:
    """获取提示词模板"""
    if name in _PROMPT_CACHE:
        return _PROMPT_CACHE[name]

    # 查找提示词文件
    prompt_dir = os.path.dirname(os.path.abspath(__file__))

    # 尝试不同扩展名
    for ext in [".md", ".txt"]:
        path = os.path.join(prompt_dir, f"{name}{ext}")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            _PROMPT_CACHE[name] = content
            return content

    raise FileNotFoundError(f"Prompt template not found: {name}")


def get_quality_checklist(stage: str) -> str:
    """获取质量检查清单"""
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "quality_checks",
        f"{stage}.txt"
    )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
