"""
单元测试: 项目存储 ProjectStore
"""
import yaml
from datetime import datetime
from se_pipeline.storage.project_store import ProjectStore
from se_pipeline.types.artifacts import RequirementsSpec
from se_pipeline.types.pipeline import PipelineState


class TestProjectStore:
    """测试项目存储 ProjectStore"""

    def test_init_creates_base_directory(self, tmp_path):
        """测试初始化会创建基础目录"""
        store = ProjectStore(base_dir=str(tmp_path / "projects"))
        assert store.base_dir.exists()
        assert store.base_dir.is_dir()

    def test_get_project_dir(self, tmp_path):
        """测试获取项目目录"""
        store = ProjectStore(base_dir=str(tmp_path / "projects"))
        project_dir = store.get_project_dir("test-001")
        assert project_dir == store.base_dir / "test-001"

    def test_save_and_load_state(self, tmp_path):
        """测试保存和加载流水线状态"""
        store = ProjectStore(base_dir=str(tmp_path / "projects"))

        # 创建测试状态
        state = PipelineState(
            project_id="test-001",
            project_name="测试项目",
            current_stage="requirements",
            original_user_requirement="我需要一个待办事项APP"
        )

        # 保存
        store.save_state("test-001", state)

        # 验证文件存在
        state_file = store.get_project_dir("test-001") / "pipeline_state.yaml"
        assert state_file.exists()

        # 加载
        loaded = store.load_state("test-001")

        assert loaded is not None
        assert loaded.project_id == "test-001"
        assert loaded.project_name == "测试项目"
        assert loaded.current_stage == "requirements"
        assert loaded.original_user_requirement == "我需要一个待办事项APP"

    def test_load_state_not_exists(self, tmp_path):
        """测试加载不存在的状态返回 None"""
        store = ProjectStore(base_dir=str(tmp_path / "projects"))

        loaded = store.load_state("non-existent-project")
        assert loaded is None

    def test_save_requirements_creates_multiple_files(self, tmp_path):
        """测试保存需求规格会创建三个文件: YAML, Markdown, QA历史"""
        store = ProjectStore(base_dir=str(tmp_path / "projects"))

        # 创建测试需求规格
        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="测试待办项目",
                description="这是一个测试项目的描述",
                functional_requirements=[
                    {"id": "FR001", "title": "创建待办", "description": "用户可以创建新的待办事项", "priority": "high"},
                    {"id": "FR002", "title": "编辑待办", "description": "用户可以编辑已有的待办事项", "priority": "medium"}
                ],
                non_functional_requirements=[
                    {"id": "NFR001", "title": "响应时间", "description": "页面响应时间不超过500ms", "priority": "high"}
                ],
                user_roles=[
                    {"name": "普通用户", "description": "使用系统管理个人待办"}
                ],
                out_of_scope=[
                    "团队协作功能",
                    "数据导出"
                ]
            )
        )

        # 保存
        store.save_requirements("test-001", spec)

        # 验证三个文件都被创建
        project_dir = store.get_project_dir("test-001")
        assert (project_dir / "01-requirements.yaml").exists()
        assert (project_dir / "01-requirements-spec.md").exists()
        assert (project_dir / "qa-history.yaml").exists()

        # 验证YAML内容正确
        with open(project_dir / "01-requirements.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            assert data["project_id"] == "test-001"
            assert data["data"]["title"] == "测试待办项目"

    def test_generate_requirements_markdown_contains_all_sections(self):
        """测试生成Markdown包含所有正确章节"""
        # 创建测试需求规格
        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="测试待办项目",
                description="这是一个测试项目的描述",
                functional_requirements=[
                    {"id": "FR001", "title": "创建待办", "description": "用户可以创建新的待办事项", "priority": "high"}
                ],
                non_functional_requirements=[
                    {"id": "NFR001", "title": "响应时间", "description": "页面响应时间不超过500ms"}
                ],
                user_roles=[
                    {"name": "普通用户", "description": "使用系统管理个人待办"}
                ],
                out_of_scope=[
                    "团队协作功能"
                ]
            ),
            verification_passed=True
        )

        store = ProjectStore(base_dir="./tmp-test")
        md = store._generate_requirements_markdown(spec)

        # 验证包含所有章节
        assert "# 需求规格说明书 - 测试待办项目" in md
        assert "**项目ID**: test-001" in md
        assert "✅ 通过" in md
        assert "## 概述" in md
        assert "这是一个测试项目的描述" in md
        assert "## 用户角色" in md
        assert "### 普通用户" in md
        assert "使用系统管理个人待办" in md
        assert "## 功能需求" in md
        assert "FR001 创建待办" in md
        assert "用户可以创建新的待办事项" in md
        assert "🔴" in md  # high priority icon
        assert "## 非功能需求" in md
        assert "NFR001 响应时间" in md
        assert "## 不在范围内" in md
        assert "团队协作功能" in md

    def test_generate_requirements_markdown_with_priority_icons(self):
        """测试Markdown根据优先级显示正确图标"""
        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="测试项目",
                description="描述",
                functional_requirements=[
                    {"id": "H", "title": "High", "description": "High desc", "priority": "high"},
                    {"id": "M", "title": "Medium", "description": "Medium desc", "priority": "medium"},
                    {"id": "L", "title": "Low", "description": "Low desc", "priority": "low"}
                ]
            )
        )

        store = ProjectStore(base_dir="./tmp-test")
        md = store._generate_requirements_markdown(spec)

        assert "🔴" in md  # high
        assert "🟡" in md  # medium
        assert "🟢" in md  # low

    def test_generate_requirements_markdown_with_qa_history(self):
        """测试Markdown包含问答历史"""
        from se_pipeline.types.artifacts import QaHistoryItem, RequirementsQaHistory

        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="测试项目",
                description="描述"
            )
        )

        # 添加问答历史
        spec.qa_history = RequirementsQaHistory(
            items=[
                QaHistoryItem(
                    question_id="q1",
                    question="您需要支持多用户吗？",
                    answer="是的，需要账号登录"
                ),
                QaHistoryItem(
                    question_id="q2",
                    question="需要移动端支持吗？",
                    answer=None
                )
            ]
        )

        store = ProjectStore(base_dir="./tmp-test")
        md = store._generate_requirements_markdown(spec)

        assert "## 问答澄清历史" in md
        assert "### 问题 1" in md
        assert "**问题**: 您需要支持多用户吗？" in md
        assert "**回答**: 是的，需要账号登录" in md
        assert "### 问题 2" in md
        assert "**状态**: ⏸ 尚未回答" in md

    def test_generate_requirements_markdown_verification_not_passed(self):
        """测试未通过验证时显示正确状态"""
        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="测试项目",
                description="描述"
            ),
            verification_passed=False
        )

        store = ProjectStore(base_dir="./tmp-test")
        md = store._generate_requirements_markdown(spec)

        assert "❌ 未通过" in md

    def test_generate_requirements_markdown_empty_optional_sections(self):
        """测试可选章节为空时不显示"""
        spec = RequirementsSpec(
            stage_id="requirements",
            project_id="test-001",
            data=RequirementsSpec.RequirementsData(
                title="测试项目",
                description="描述"
                # 没有 user_roles, functional_requirements, non_functional_requirements, out_of_scope
            )
        )

        store = ProjectStore(base_dir="./tmp-test")
        md = store._generate_requirements_markdown(spec)

        # 基础章节存在
        assert "# 需求规格说明书" in md
        assert "## 概述" in md

        # 空章节不出现
        assert "## 用户角色" not in md
        assert "## 功能需求" not in md
        assert "## 非功能需求" not in md
        assert "## 不在范围内" not in md

    def test_list_projects(self, tmp_path):
        """测试列出所有项目"""
        store = ProjectStore(base_dir=str(tmp_path / "projects"))

        # 创建几个项目目录
        (store.base_dir / "project-001").mkdir()
        (store.base_dir / "project-002").mkdir()
        (store.base_dir / "not-a-project.txt").touch()  # 文件会被忽略

        projects = store.list_projects()

        assert sorted(projects) == ["project-001", "project-002"]
        assert "not-a-project.txt" not in projects

    def test_list_projects_empty_when_base_dir_not_exists(self, tmp_path):
        """测试基础目录不存在时返回空列表"""
        non_existent = tmp_path / "non-existent"
        store = ProjectStore(base_dir=str(non_existent))

        projects = store.list_projects()
        assert projects == []

    def test_list_projects_empty_when_no_projects(self, tmp_path):
        """测试基础目录为空时返回空列表"""
        store = ProjectStore(base_dir=str(tmp_path / "projects"))
        # base_dir 已创建但是空

        projects = store.list_projects()
        assert projects == []
