#!/usr/bin/env python3
"""Test adding todo via MCP server"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../mcp-todo-server-py'))

from todo_server import TodoServer, Todo
import json
from datetime import datetime

# Create server instance
server = TodoServer()

# Add our todo
title = "学习日语"
todo = Todo(
    id=server.next_id,
    title=title,
    completed=False,
    created_at=datetime.now().isoformat()
)
server.todos.append(todo)
server.next_id += 1

# Save to file for verification
output_file = os.path.join(os.path.dirname(__file__), 'last_add_result.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        "message": "Added todo: " + title,
        "todo": {
            "id": todo.id,
            "title": todo.title,
            "completed": todo.completed,
            "created_at": todo.created_at
        },
        "total": len(server.todos)
    }, f, ensure_ascii=False, indent=2)

# Print only ASCII
print("Result saved to last_add_result.json")
print(f"Total todos: {len(server.todos)}")
