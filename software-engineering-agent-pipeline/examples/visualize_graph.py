#!/usr/bin/env python3
"""
生成需求分析阶段内部图的Mermaid图形化展示
"""
from se_pipeline.graph import build_requirements_internal_graph


# 节点名翻译成中文
NODE_NAME_MAP = {
    "__start__": "开始",
    "__end__": "结束",
    "analyst": "需求分析师<br/><font size=-1>分析需求 → 生成问题</font>",
    "wait_user": "等待用户<br/><font size=-1>用户回答问题<br/>支持断点续问</font>",
    "verifier": "需求验证官<br/><font size=-1>独立验证 → 检查遗漏</font>",
    "final": "文档做成<br/><font size=-1>整理生成需求文档</font>",
    "quality_gate": "质量闸门<br/><font size=-1>自动评审 → 质量检查</font>",
}


def generate_mermaid(output_path: str = "./requirements_graph.mmd"):
    """生成Mermaid图"""
    # 需要一个实际client来构造
    import anthropic
    client = anthropic.AsyncAnthropic(api_key="fake")

    graph = build_requirements_internal_graph(client)
    compiled = graph.compile()

    # 生成mermaid
    mermaid = compiled.get_graph().draw_mermaid()

    # 将英文节点名替换为中文
    for eng, chn in NODE_NAME_MAP.items():
        # 处理两种格式: name(name) 和 ([<p>name</p>])
        mermaid = mermaid.replace(f">{eng}<", f">{chn}<")
        mermaid = mermaid.replace(f"({eng})", f"({chn})")
        mermaid = mermaid.replace(f"[{eng}]", f"[{chn}]")

    # 添加更好的配置
    if "---" not in mermaid:
        mermaid = """---
config:
  flowchart:
    curve: linear
---
""" + mermaid

    # 增加行高
    if "classDef default" in mermaid:
        mermaid = mermaid.replace("line-height:1.2", "line-height:1.6")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mermaid)

    print(f"Mermaid graph saved to {output_path}")
    print("\nGraph content:")
    print("-" * 60)
    print(mermaid)
    print("-" * 60)
    print("\nYou can paste this into https://mermaid.live/ to see the visual graph.")


if __name__ == "__main__":
    generate_mermaid()
