"""
单元测试: memory-mcp知识图谱客户端 MemoryMcpClient
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from se_pipeline.knowledge.memory_mcp_client import MemoryMcpClient


class TestMemoryMcpClient:
    """测试MemoryMcpClient"""

    def test_init_with_default_url(self):
        """测试使用默认URL初始化"""
        client = MemoryMcpClient()
        assert client.base_url == "http://localhost:8000"

    def test_init_with_custom_url(self):
        """测试使用自定义URL初始化"""
        client = MemoryMcpClient(base_url="http://192.168.1.100:8080")
        assert client.base_url == "http://192.168.1.100:8080"

    @pytest.mark.asyncio
    async def test_create_project_entity(self):
        """测试创建项目实体"""
        client = MemoryMcpClient()

        # 创建支持异步上下文管理器的mock响应
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = Mock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)

            await client.create_project_entity(
                project_id="test-001",
                name="测试项目",
                description="这是一个测试项目"
            )

            # 验证调用了正确的URL
            call_args = mock_session.post.call_args
            assert call_args[0][0] == "http://localhost:8000/entities"
            # 验证发送了正确的JSON
            called_json = call_args[1]['json']
            assert called_json['name'] == "test-001"
            assert called_json['type'] == "Project"
            assert called_json['properties']['project_id'] == "test-001"
            assert called_json['properties']['name'] == "测试项目"
            assert called_json['properties']['description'] == "这是一个测试项目"

    @pytest.mark.asyncio
    async def test_add_requirements_creates_entities_and_relations(self):
        """测试添加需求会创建实体和关系"""
        client = MemoryMcpClient()
        requirements = [
            {"id": "FR001", "title": "创建待办", "description": "用户可以创建待办"},
            {"id": "FR002", "title": "编辑待办", "description": "用户可以编辑待办"}
        ]

        # 创建支持异步上下文管理器的mock响应
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = Mock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)

            await client.add_requirements("test-001", requirements)

            # 验证调用次数：2个需求实体 + 2个关系 = 4次POST
            assert mock_session.post.call_count == 4

            # 第一个调用是创建FR001实体
            call1 = mock_session.post.call_args_list[0]
            assert call1[0][0] == "http://localhost:8000/entities"
            called_json1 = call1[1]['json']
            assert called_json1['name'] == "FR001"
            called_json1['type'] == "Requirement"

            # 第二个调用是创建关系：project -> FR001
            call2 = mock_session.post.call_args_list[1]
            assert call2[0][0] == "http://localhost:8000/relations"
            called_json2 = call2[1]['json']
            assert called_json2['from'] == "test-001"
            assert called_json2['to'] == "FR001"
            assert called_json2['relationType'] == "CONTAINS"

    @pytest.mark.asyncio
    async def test_add_requirements_generates_id_from_title_when_missing(self):
        """测试当需求没有id时从标题生成"""
        client = MemoryMcpClient()
        requirements = [
            {"title": "创建待办事项", "description": "用户可以创建待办"},
        ]

        # 创建支持异步上下文管理器的mock响应
        mock_resp = Mock()
        mock_resp.raise_for_status = Mock()
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = Mock()
            mock_session.post.return_value = mock_resp
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)

            await client.add_requirements("test-001", requirements)

            # 检查生成的实体ID
            first_call = mock_session.post.call_args_list[0]
            called_json = first_call[1]['json']
            assert called_json['name'] == "req_创建待办事项"  # 从标题生成

    @pytest.mark.asyncio
    async def test_get_project_context_returns_data_when_exists(self):
        """测试获取项目上下文返回数据当项目存在"""
        client = MemoryMcpClient()

        # 创建支持异步上下文管理器的mock响应
        def create_mock_response(status, json_data):
            mock_resp = Mock()
            mock_resp.status = status
            mock_resp.raise_for_status = Mock()
            mock_resp.json = AsyncMock(return_value=json_data)
            # 支持异步上下文管理器
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=None)
            return mock_resp

        mock_project_resp = create_mock_response(200, {
            "name": "test-001",
            "type": "Project",
            "properties": {"name": "Test"}
        })

        mock_outgoing_resp = create_mock_response(200, [
            {"from": "test-001", "to": "FR001", "relationType": "CONTAINS"}
        ])

        mock_entity_resp = create_mock_response(200, {
            "name": "FR001",
            "type": "Requirement",
            "properties": {"title": "Test Requirement"}
        })

        # mock ClientSession.get
        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = Mock()
            mock_session.get.side_effect = [mock_project_resp, mock_outgoing_resp, mock_entity_resp]
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)

            result = await client.get_project_context("test-001")

            assert "project" in result
            assert "contained_entities" in result
            assert "relations" in result
            assert result["project"]["name"] == "test-001"
            assert len(result["contained_entities"]) == 1

    @pytest.mark.asyncio
    async def test_get_project_context_returns_empty_when_not_exists(self):
        """测试获取不存在项目返回空字典"""
        client = MemoryMcpClient()

        # 创建支持异步上下文管理器的mock响应
        def create_mock_response(status, json_data):
            mock_resp = Mock()
            mock_resp.status = status
            mock_resp.raise_for_status = Mock()
            mock_resp.json = Mock(return_value=json_data)
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=None)
            return mock_resp

        mock_resp = create_mock_response(404, {})

        with patch('aiohttp.ClientSession') as mock_session_cls:
            mock_session = Mock()
            mock_session.get.return_value = mock_resp
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)

            result = await client.get_project_context("non-existent")
            assert result == {}
