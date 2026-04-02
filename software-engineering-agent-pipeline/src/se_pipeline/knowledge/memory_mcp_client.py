"""
memory-mcp知识图谱客户端封装
"""
from typing import List, Dict, Any


class MemoryMcpClient:
    """memory-mcp知识图谱客户端封装

    负责将各Agent产出的制品提取实体和关系，写入知识图谱，
    供后续Agent读取保证一致性。
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def create_project_entity(
        self,
        project_id: str,
        name: str,
        description: str
    ) -> None:
        """创建项目实体"""
        # TODO: 调用MCP协议创建实体
        pass

    async def add_requirements(
        self,
        project_id: str,
        requirements: List[Dict[str, Any]]
    ) -> None:
        """添加需求实体到项目"""
        # TODO: 调用MCP协议批量添加实体和关系
        pass

    async def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """获取项目完整上下文用于后续Agent"""
        # TODO: 查询知识图谱返回完整上下文
        return {}
