from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime

app = FastAPI(title="Cool Todo List", description="A beautiful and cool todo list application")

# In-memory storage for todos
todos = []

# Pydantic models
class TodoCreate(BaseModel):
    title: str
    description: Optional[str] = ""

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None

class Todo(BaseModel):
    id: str
    title: str
    description: str
    completed: bool
    created_at: str

# API Routes
@app.get("/api/todos", response_model=List[Todo])
def get_todos():
    """Get all todos"""
    return todos

@app.post("/api/todos", response_model=Todo)
def create_todo(todo_create: TodoCreate):
    """Create a new todo"""
    todo = Todo(
        id=str(uuid.uuid4())[:8],
        title=todo_create.title,
        description=todo_create.description or "",
        completed=False,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    todos.append(todo)
    return todo

@app.put("/api/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: str, todo_update: TodoUpdate):
    """Update a todo"""
    for todo in todos:
        if todo.id == todo_id:
            if todo_update.title is not None:
                todo.title = todo_update.title
            if todo_update.description is not None:
                todo.description = todo_update.description
            if todo_update.completed is not None:
                todo.completed = todo_update.completed
            return todo
    raise HTTPException(status_code=404, detail="Todo not found")
@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: str):
    """Delete a todo"""
    global todos
    initial_length = len(todos)
    todos = [t for t in todos if t.id != todo_id]
    if len(todos) == initial_length:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Deleted successfully"}

@app.delete("/api/todos/completed")
def clear_completed():
    """Clear all completed todos"""
    global todos
    completed_count = sum(1 for t in todos if t.completed)
    todos = [t for t in todos if not t.completed]
    return {"message": f"Cleared {completed_count} completed todos"}

# Mount static files and serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    """Home page with project links"""
    return FileResponse("static/index.html")

@app.get("/todo")
def todo_list():
    """Todo list application"""
    return FileResponse("static/todo.html")

@app.get("/snake")
def snake_game():
    """Snake game"""
    return FileResponse("static/snake.html")

@app.get("/sudoku")
def sudoku_game():
    """Sudoku puzzle game"""
    return FileResponse("static/sudoku.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

