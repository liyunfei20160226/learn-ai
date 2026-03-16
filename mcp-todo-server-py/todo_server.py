"""
简单的待办事项 MCP 服务器
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types


@dataclass
class Todo:
    """待办事项数据类"""
    id: int
    title: str
    completed: bool
    created_at: str


class TodoServer:
    """待办事项服务器"""

    def __init__(self, storage_file: str = "todos.json"):
        self.todos: List[Todo] = []
        self.next_id = 1
        self.storage_file = storage_file
        self.server = Server("todo-server")
        # 启动时加载持久化数据
        self.load_todos()

    def load_todos(self):
        """从文件加载待办事项"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.todos = [Todo(**todo) for todo in data['todos']]
                self.next_id = data['next_id']
        except FileNotFoundError:
            # 文件不存在，使用空列表
            pass

    def save_todos(self):
        """保存待办事项到文件"""
        data = {
            'todos': [
                {
                    'id': t.id,
                    'title': t.title,
                    'completed': t.completed,
                    'created_at': t.created_at
                } for t in self.todos
            ],
            'next_id': self.next_id
        }
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def setup_handlers(self):
        """设置请求处理器"""
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """列出所有可用工具"""
            return [
                types.Tool(
                    name="add_todo",
                    description="添加一个新的待办事项",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "待办事项的标题"
                            }
                        },
                        "required": ["title"]
                    }
                ),
                types.Tool(
                    name="list_todos",
                    description="列出所有待办事项",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="delete_todo",
                    description="删除一个待办事项",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "integer",
                                "description": "要删除的待办ID"
                            }
                        },
                        "required": ["id"]
                    }
                ),
                types.Tool(
                    name="complete_todo",
                    description="标记待办事项为完成",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "integer",
                                "description": "待办ID"
                            }
                        },
                        "required": ["id"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, 
            arguments: Dict[str, Any]
        ) -> List[types.TextContent]:
            """处理工具调用"""
            
            if name == "add_todo":
                title = arguments.get("title")
                if not title:
                    raise ValueError("title不能为空")
                
                todo = Todo(
                    id=self.next_id,
                    title=title,
                    completed=False,
                    created_at=datetime.now().isoformat()
                )
                self.todos.append(todo)
                self.next_id += 1
                self.save_todos()

                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "message": f"✅ 已添加待办: {title}",
                        "todo": asdict(todo),
                        "total": len(self.todos)
                    }, ensure_ascii=False, indent=2)
                )]
            
            elif name == "list_todos":
                if not self.todos:
                    return [types.TextContent(
                        type="text",
                        text="📭 暂无待办事项"
                    )]
                
                todo_list = "\n".join([
                    f"[{t.id}] {'✅' if t.completed else '⬜'} {t.title}"
                    for t in self.todos
                ])
                
                return [types.TextContent(
                    type="text",
                    text=f"📋 待办列表 (共{len(self.todos)}项):\n{todo_list}"
                )]
            
            elif name == "delete_todo":
                todo_id = arguments.get("id")
                if todo_id is None:
                    raise ValueError("id不能为空")
                
                for i, todo in enumerate(self.todos):
                    if todo.id == todo_id:
                        deleted = self.todos.pop(i)
                        self.save_todos()
                        return [types.TextContent(
                            type="text",
                            text=f"🗑️ 已删除待办: {deleted.title}"
                        )]
                
                return [types.TextContent(
                    type="text",
                    text=f"❌ 未找到ID为 {todo_id} 的待办",
                    is_error=True
                )]
            
            elif name == "complete_todo":
                todo_id = arguments.get("id")
                if todo_id is None:
                    raise ValueError("id不能为空")
                
                for todo in self.todos:
                    if todo.id == todo_id:
                        todo.completed = True
                        self.save_todos()
                        return [types.TextContent(
                            type="text",
                            text=f"✅ 已完成: {todo.title}"
                        )]
                
                return [types.TextContent(
                    type="text",
                    text=f"❌ 未找到ID为 {todo_id} 的待办",
                    is_error=True
                )]
            
            else:
                return [types.TextContent(
                    type="text",
                    text=f"未知工具: {name}",
                    is_error=True
                )]
    
    async def run(self):
        """运行服务器"""
        self.setup_handlers()
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="todo-server",
                    server_version="1.0.0",
                    capabilities={
                        "tools": {}
                    }
                )
            )


async def main():
    """主函数"""
    server = TodoServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())