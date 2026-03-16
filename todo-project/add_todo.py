#!/usr/bin/env python3
"""简单的脚本添加待办事项"""

import sys
sys.path.insert(0, 'D:/dev/learn-ai/mcp-todo-server-py')

from todo_server import TodoServer, Todo
import json
from datetime import datetime

# 创建服务器实例并加载存储
server = TodoServer()
# 直接添加待办
todo = Todo(
    id=server.next_id,
    title="todo mcp服务",
    completed=False,
    created_at=datetime.now().isoformat()
)
server.todos.append(todo)
server.next_id += 1

print("已添加待办: %s" % todo.title)
print("ID: %d" % todo.id)
print("当前共有 %d 个待办事项" % len(server.todos))
print("\n当前待办列表:")
for t in server.todos:
    print("[%d] %s %s" % (t.id, '✅' if t.completed else '⬜', t.title))
