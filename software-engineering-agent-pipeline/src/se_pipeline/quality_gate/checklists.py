"""
质量检查清单定义
"""
from ..types.quality_gate import CheckItem, Severity


def load_checklist_from_text(text: str) -> list[CheckItem]:
    """从文本加载检查清单"""
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 格式: "- id 问题描述 severity
        # 跳过开头的列表标记 '-'
        if line.startswith("-"):
            line = line[1:].strip()
        # 最后一个词是 severity
        parts = line.rsplit(None, 1)
        if len(parts) != 2:
            continue

        rest, sev = parts
        if sev in ["error", "warning", "info"]:
            # 第一个token是id
            parts2 = rest.split(None, 1)
            if len(parts2) == 2:
                item_id, question = parts2
                items.append(CheckItem(
                    id=item_id,
                    question=question,
                    severity=Severity(sev)
                ))

    return items


def get_requirements_checklist() -> list[CheckItem]:
    """需求阶段检查清单"""
    from ..prompts import get_quality_checklist
    text = get_quality_checklist("requirements")
    return load_checklist_from_text(text)
