"""
memory-mcp知识图谱客户端封装
"""
import aiohttp
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
        entity = {
            "name": project_id,
            "type": "Project",
            "properties": {
                "project_id": project_id,
                "name": name,
                "description": description
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/entities", json=entity) as resp:
                resp.raise_for_status()

    async def add_requirements(
        self,
        project_id: str,
        requirements: List[Dict[str, Any]]
    ) -> None:
        """添加需求实体到项目，建立包含关系"""
        async with aiohttp.ClientSession() as session:
            for req in requirements:
                # 创建需求实体
                req_id = req.get("id", f"req_{req.get('title', '').lower().replace(' ', '_')}")
                entity = {
                    "name": req_id,
                    "type": "Requirement",
                    "properties": req
                }
                async with session.post(f"{self.base_url}/entities", json=entity) as resp:
                    resp.raise_for_status()

                # 创建关系：Project 包含 Requirement
                relation = {
                    "from": project_id,
                    "to": req_id,
                    "relationType": "CONTAINS"
                }
                async with session.post(f"{self.base_url}/relations", json=relation) as resp:
                    resp.raise_for_status()

    async def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """获取项目完整上下文（所有关联实体和关系）"""
        async with aiohttp.ClientSession() as session:
            # 获取项目实体
            async with session.get(f"{self.base_url}/entities/{project_id}") as resp:
                if resp.status == 404:
                    return {}
                resp.raise_for_status()
                project = await resp.json()

            # 获取所有出边（项目包含的内容）
            async with session.get(f"{self.base_url}/entities/{project_id}/outgoing") as resp:
                resp.raise_for_status()
                outgoing = await resp.json()

            # 获取所有关联实体的详细信息
            entities = []
            for rel in outgoing:
                async with session.get(f"{self.base_url}/entities/{rel['to']}") as resp:
                    if resp.status == 200:
                        entities.append(await resp.json())

            return {
                "project": project,
                "contained_entities": entities,
                "relations": outgoing
            }
