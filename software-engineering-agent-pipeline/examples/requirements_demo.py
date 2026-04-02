#!/usr/bin/env python3
"""
需求分析阶段交互式演示 - 双Agent澄清流程
- Agent生成问题 → 用户在控制台回答 → 验证官检查 → 循环直到澄清 → 生成需求文档
"""
import os
import sys
import codecs
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from se_pipeline.types.pipeline import PipelineState
from se_pipeline.storage import ProjectStore
from se_pipeline.graph import create_requirements_internal_app


# 设置UTF-8编码输出
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# 加载环境变量
load_dotenv()

# 读取配置
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
model = os.getenv("OPENAI_MODEL")

# 设置环境变量
os.environ["OPENAI_API_KEY"] = api_key
if base_url:
    os.environ["OPENAI_BASE_URL"] = base_url

# 初始化LLM
llm = ChatOpenAI(
    model=model,
    temperature=0,
    request_timeout=180,  # 3分钟超时
)


def run_interactive_demo(project_id: str, original_requirement: str):
    """交互式运行需求分析"""

    # 初始化存储
    store = ProjectStore(base_dir="./examples/projects")

    # 检查断点
    state = store.load_state(project_id)

    if state is None:
        # 新建项目
        print(f"\n🆕 创建新项目: {project_id}")
        state = PipelineState(
            project_id=project_id,
            project_name=project_id,
            current_stage="requirements",
            original_user_requirement=original_requirement,
        )
    else:
        print(f"\n📂 恢复断点，已有 {len(state.requirements_qa_history)} 条问答历史")

    # 创建LangGraph应用
    app = create_requirements_internal_app(llm)

    # 交互循环
    while True:
        print("\n🤖 AI 思考中...")
        sys.stdout.flush()
        # 同步调用
        result = app.invoke(state)
        state = PipelineState(**result)

        # 获取待回答问题
        unanswered = [item for item in state.requirements_qa_history if item["answer"] is None]

        if not unanswered:
            # 所有问题都回答了
            if (state.requirements_spec is not None and
                state.requirements_verification_passed and
                not state.needs_more_questions):
                # 完成了
                print("\n🎉 =========================================")
                print("✅ 需求分析阶段完成！")
                if state.requirements_spec:
                    print(f"📋 生成 {len(state.requirements_spec.data.functional_requirements)} 个功能需求")
                output_path = f"./examples/projects/{project_id}/01-requirements-spec.md"
                print(f"📄 文档: {output_path}")
                print("============================================")

                # 保存制品
                store.save_requirements(project_id, state.requirements_spec)
                store.save_state(project_id, state)
                break
            else:
                # 还需要继续
                continue

        # 输出问题
        print("\n❓ ========================")
        print("请回答以下问题:")
        print("========================")
        for i, item in enumerate(unanswered, 1):
            print(f"  {i}. {item['question']}")

        # 获取用户回答
        print("\n请输入回答 (输入 'quit' 退出，支持断点续问):")
        try:
            answer = input().strip()
        except (EOFError, KeyboardInterrupt):
            answer = "quit"

        if answer.lower() == "quit":
            print("\n💾 保存进度，下次运行可以继续回答...")
            store.save_state(project_id, state)
            break

        if not answer:
            print("⚠️  回答不能为空，请重新输入")
            continue

        # 保存回答到第一个未回答问题
        for item in state.requirements_qa_history:
            if item["answer"] is None:
                item["answer"] = answer
                break

        state.update_timestamp()
        store.save_state(project_id, state)


def main():
    print("=" * 60)
    print("📋 软件工程多Agent流水线 - 需求分析交互式演示")
    print("=" * 60)
    print()
    print("使用说明:")
    print("  - Agent会逐步提问，请你在控制台回答")
    print("  - 可以随时输入 'quit' 退出，进度会保存")
    print("  - 下次运行会自动恢复断点，可以继续回答")
    print()

    # 默认项目
    project_id = input("请输入项目ID [默认: demo-todo]: ").strip() or "demo-todo"

    original_requirement = input("请输入原始需求 [默认: 做一个待办事项清单]: ").strip() or "做一个待办事项清单，前端react，后端spring boot，DB postgres"

    print()
    print(f"🚀 开始需求分析: {project_id}")
    print(f"原始需求: {original_requirement}")

    run_interactive_demo(project_id, original_requirement)


if __name__ == "__main__":
    main()
