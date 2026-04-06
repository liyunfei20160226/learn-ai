#!/usr/bin/env python3
"""
交互式需求分析示例 - 完整软件工程需求分析流水线

用法:
    # 新建项目
    uv run python examples/interactive_requirements_analysis.py --project-id "my-project" --project-name "我的项目"

    # 继续已有项目（断点续问）
    uv run python examples/interactive_requirements_analysis.py --project-id "my-project"

输出持久化:
    所有状态和生成的需求规格都会自动保存到 projects/<project-id>/ 目录
    - pipeline_state.yaml - 当前流水线状态（包含完整问答历史）
    - 01-requirements.yaml - 最终需求规格
    - qa-history.yaml - 完整问答历史
    - 01-requirements.md - Markdown 格式需求文档

知识图谱:
    如果配置了 MEMORY_MCP_BASE_URL，会自动在 memory-mcp 知识图谱中创建：
    - 项目实体
    - 需求规格实体
    - 关联关系

    注意：需要先启动 memory-mcp HTTP 服务才能使用。
    如果不配置或不启动，会跳过知识图谱创建，不影响需求分析流程。
"""
import os
import argparse
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from se_pipeline.types.pipeline import PipelineState
from se_pipeline.storage.project_store import ProjectStore

# 加载环境变量
load_dotenv()


def run_interactive(
    project_id: str,
    project_name: str,
) -> None:
    """交互式运行需求分析流程

    如果项目已经存在，自动加载已有状态继续问答。
    每次回答完问题立即保存状态，支持断点续问。
    """
    # 尝试加载已有项目状态
    store = ProjectStore()
    # 确保base目录存在
    store.base_dir.mkdir(parents=True, exist_ok=True)
    existing_state = store.load_state(project_id)

    if existing_state is not None:
        print(f"📂 发现已有项目 {project_id}，加载状态继续...\n")
        state = existing_state
        # 更新项目名称
        if project_name != existing_state.project_name:
            state = state.model_copy(update={"project_name": project_name})
            state.update_timestamp()
    else:
        # 新建项目，需要原始需求
        print(f"🆕 新建项目: {project_id} ({project_name})\n")
        print("请输入你的原始需求:")
        original_requirement = input("> ").strip()
        print()

        # 初始状态
        state = PipelineState(
            project_id=project_id,
            project_name=project_name,
            current_stage="requirements",
            original_user_requirement=original_requirement,
        )

    # 初始化LLM和所有Agent（手动步进，不使用编译后的app）
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        temperature=0.0,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        extra_body={
            "enable_thinking": False
        }
    )

    # 检测知识图谱服务是否可用
    memory_client = None
    memory_mcp_url = os.getenv("MEMORY_MCP_BASE_URL")
    if memory_mcp_url:
        print("🔍 检测知识图谱服务...")
        import asyncio
        try:
            from se_pipeline.knowledge.memory_mcp_client import MemoryMcpClient
            memory_client = MemoryMcpClient(base_url=memory_mcp_url)
            # 尝试一个简单的get请求看是否连通
            asyncio.run(memory_client.get_project_context("test-connectivity"))
            print("✅ 知识图谱服务连通\n")
        except Exception as e:
            print(f"⚠️  知识图谱服务连接失败: {e}")
            print("\n知识图谱服务需要单独启动HTTP服务才能使用。")
            print("当前配置 MEMORY_MCP_BASE_URL = " + memory_mcp_url)
            print("\n是否继续运行需求分析（跳过知识图谱）？[y/N] ", end="")
            answer = input().strip().lower()
            if answer not in ["y", "yes", "Y"]:
                print("👋 退出，请先启动知识图谱服务再试。")
                return
            print("\n➡️  继续运行，跳过知识图谱...\n")
            memory_client = None
    else:
        print("ℹ️  MEMORY_MCP_BASE_URL 未配置，跳过知识图谱集成\n")

    from se_pipeline.agents import (
        RequirementsAnalystAgent,
        RequirementsVerifierAgent,
        RequirementsFinalAgent,
    )
    from se_pipeline.quality_gate import AutoReviewer
    from se_pipeline.graph.pipeline_graph import (
        analyst_node,
        verifier_node,
        final_node,
        quality_gate_node,
        after_analyst,
        after_verifier,
        after_quality_gate,
        wait_user_node,
    )

    analyst = RequirementsAnalystAgent(llm)
    verifier = RequirementsVerifierAgent(llm)
    finalizer = RequirementsFinalAgent(llm)
    reviewer = AutoReviewer(llm)

    # 打印欢迎信息
    print("\n" + "="*70)
    print("🚀 开始需求分析流程")
    print(f"📋 项目: {state.project_name} ({project_id})")
    print(f"📝 原始需求: {state.original_user_requirement}")
    print("="*70 + "\n")

    node = "analyst" if existing_state is None else after_analyst(state)
    steps = 0

    # 节点名称转中文
    node_name_map = {
        "analyst": "需求分析师",
        "wait_user": "等待用户回答",
        "verifier": "需求验证官",
        "final": "需求生成",
        "quality_gate": "质量闸门",
        "__end__": "结束"
    }

    while node != "__end__":
        steps += 1
        node_name = node_name_map.get(node, node)
        print(f"🔄 步骤 {steps}, 当前: {node_name}...\n")

        if node == "analyst":
            state = analyst_node(state, analyst)
            node = after_analyst(state)
            # 如果分析师判断所有问题已经澄清，直接进入下一阶段，给用户个提示
            has_unanswered = any(item["answer"] is None for item in state.requirements_qa_history)
            if not has_unanswered and state.needs_more_questions:
                print("ℹ️  分析师检查确认所有问题已澄清，不需要继续提问，进入下一阶段...\n")
            next_node_name = node_name_map.get(node, node)
            print(f"➡️  下一步: {next_node_name}\n")
            continue

        if node == "wait_user":
            # 等待用户回答
            unanswered = [i for i in state.requirements_qa_history if i["answer"] is None]
            if unanswered:
                print(f"❓ LLM提问 ({len(unanswered)} 个):\n")
                for i, item in enumerate(unanswered, 1):
                    print(f"  {i}. {item['question']}")
                print()

                # 用户逐个回答，每回答一个问题立即保存
                for item in unanswered:
                    print(f"💬 你的回答: {item['question']}")
                    answer = input("> ").strip()
                    item["answer"] = answer
                    state.update_timestamp()
                    # 每回答一个问题立即保存，中途退出也不丢数据
                    project_dir = store.get_project_dir(project_id)
                    project_dir.mkdir(parents=True, exist_ok=True)
                    store.save_state(project_id, state)
                print()

                # 所有问题回答完，再打印一次保存信息
                project_dir = store.get_project_dir(project_id)
                print(f"💾 所有问题回答完成，当前状态已保存到 {project_dir}")
                print(f"   文件位置: {project_dir / 'pipeline_state.yaml'}")
                print("   (即使退出，下次启动会自动继续)\n")

            # wait_user 只是等待用户输入，回答完后交给路由逻辑判断下一步
            # 问题来自哪里，回答完回到哪里：
            # - 如果分析师还没说 all_clear → 回到 analyst，让分析师继续
            # - 如果分析师已经说 all_clear → 现在是验证官循环 → 回到 verifier，让验证官继续
            state = wait_user_node(state)

            # 判断：当前是谁的循环？
            # 关键：一旦分析师说 all_clear (requirements_verification_passed = False 但 needs_more_questions 是验证官需要)
            # 就永远留在验证官循环，直到验证官也说 all_clear
            if not state.requirements_verification_passed:
                # 分析师还没通过验证 → 分析师循环，回到 analyst
                node = "analyst"
            else:
                # 分析师已经通过，现在是验证官循环 → 回到 verifier
                node = "verifier"
            continue

        if node == "verifier":
            print("🔍 需求验证中...\n")
            state = verifier_node(state, verifier)
            node = after_verifier(state)
            # 如果验证官判断所有问题已经澄清，直接进入下一阶段，给用户个提示
            has_unanswered = any(item["answer"] is None for item in state.requirements_qa_history)
            if not has_unanswered and state.needs_more_questions:
                print("ℹ️  验证官检查确认所有问题已澄清，不需要继续提问，进入下一阶段...\n")
            next_node_name = node_name_map.get(node, node)
            print(f"➡️  下一步: {next_node_name}\n")
            # 保存状态
            project_dir = store.get_project_dir(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            store.save_state(project_id, state)
            continue

        if node == "final":
            print("📝 生成最终需求规格...\n")
            state = final_node(state, finalizer)
            node = "quality_gate"
            next_node_name = node_name_map.get(node, node)
            print(f"➡️  下一步: {next_node_name}\n")
            # 保存状态
            project_dir = store.get_project_dir(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            store.save_state(project_id, state)
            continue

        if node == "quality_gate":
            print("🛡️  质量闸门评审中...\n")
            if state.requirements_spec is not None:
                result = reviewer.review_requirements(state.requirements_spec)
                # 打印评审结果
                if result.passed:
                    print("✅ 质量评审通过！\n")
                else:
                    print("❌ 质量评审不通过，需要进一步澄清：\n")
                    print(result.feedback)
                    print("\n⚠️  自动回流到需求分析师继续澄清...\n")
                # 更新状态
                if not result.passed:
                    state = state.model_copy(update={
                        "requirements_verification_passed": False,
                        "needs_more_questions": True,
                        "backflow_feedback": result.feedback
                    })
            node = after_quality_gate(state)
            next_node_name = node_name_map.get(node, node)
            print(f"➡️  下一步: {next_node_name}\n")
            # 保存状态
            project_dir = store.get_project_dir(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            store.save_state(project_id, state)
            continue

    # 最终保存所有产物
    print("\n💾 保存最终产物...")
    store.save_state(project_id, state)
    if state.requirements_spec is not None:
        store.save_requirements(project_id, state.requirements_spec)
    project_dir = store.get_project_dir(project_id)
    print(f"✓ 所有文件已保存到: {project_dir}")
    print("  - pipeline_state.yaml - 当前流水线状态（包含完整问答历史）")
    print("  - 01-requirements.yaml - 需求规格YAML")
    print("  - qa-history.yaml - 问答历史")
    print("  - 01-requirements.md - Markdown可读文档")
    print()

    # 如果知识图谱可用，创建知识图谱实体
    if memory_client is not None and state.requirements_spec is not None:
        print("\n🧠 创建知识图谱实体...")
        try:
            import asyncio
            asyncio.run(memory_client.create_project_entity(
                project_id=project_id,
                name=project_name,
                description=state.requirements_spec.data.description or ""
            ))
            asyncio.run(memory_client.add_requirements(
                project_id=project_id,
                requirements=state.requirements_spec
            ))
            print("✓ 知识图谱实体创建完成")
        except Exception as e:
            print(f"⚠️  知识图谱创建失败: {e}")
            print("  (忽略此错误不影响需求分析结果)")

    # 输出结果
    print("\n" + "="*70)
    if state.requirements_spec is not None and node == "__end__":
        spec = state.requirements_spec
        print("✅ 需求分析完成！")
        print("="*70)
        print("\n📄 生成结果:")
        print(f"  标题: {spec.data.title}")
        print(f"  描述: {spec.data.description}")
        print(f"  功能需求: {len(spec.data.functional_requirements)} 项")
        print(f"  非功能需求: {len(spec.data.non_functional_requirements)} 项")
        if spec.data.out_of_scope and len(spec.data.out_of_scope) > 0:
            print(f"  超出范围: {len(spec.data.out_of_scope)} 项")
        print()
        print(f"📂 数据目录: {store.get_project_dir(project_id)}")
        print("🎉 流程结束，可以开始下一阶段开发。")
    else:
        print("⚠️  流程未完全完成")
        print(f"  总步数: {steps}")
        print(f"  最终节点: {node}")
        if state.requirements_spec is not None:
            print("  ⚠️  但需求规格已生成，可以使用")
            print(f"  📂 数据目录: {store.get_project_dir(project_id)}")
        else:
            print("  ❌ 未生成最终需求规格")
            print("  💡 下次运行会自动从当前位置继续")

    return


def main():
    parser = argparse.ArgumentParser(description="交互式需求分析（支持断点续问）")
    parser.add_argument("--project-id", default="interactive-001", help="项目ID (用于文件保存，同一ID断点续问)")
    parser.add_argument("--project-name", default=None, help="项目名称（新建项目需要，已有项目可省略）")
    args = parser.parse_args()

    # 如果没有提供项目名称，默认用 project-id
    project_name = args.project_name or args.project_id

    run_interactive(args.project_id, project_name)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 收到中断，优雅退出。状态已保存，可以下次继续。")
        exit(0)
