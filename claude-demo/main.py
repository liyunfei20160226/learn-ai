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

@app.delete("/api/todos/completed")
def clear_completed():
    """Clear all completed todos"""
    global todos
    completed_count = sum(1 for t in todos if t.completed)
    todos = [t for t in todos if not t.completed]
    return {"message": f"Cleared {completed_count} completed todos"}

@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: str):
    """Delete a todo"""
    global todos
    initial_length = len(todos)
    todos = [t for t in todos if t.id != todo_id]
    if len(todos) == initial_length:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Deleted successfully"}

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

@app.get("/minesweeper")
def minesweeper_game():
    """Minesweeper game"""
    return FileResponse("static/minesweeper.html")

@app.get("/category")
def category_page():
    """Category page showing apps by category"""
    return FileResponse("static/category.html")

# === Notes App with pandas CSV storage - hierarchical structure
import pandas as pd
import os
import uuid
from datetime import datetime
from collections import deque

# Pydantic models for notes - hierarchical storage
class CategoryCreate(BaseModel):
    parent_level: str  # 'root', 'level1', 'level2'
    parent_id: Optional[str] = None
    name: str

class NoteCreate(BaseModel):
    category_id: str
    title: str
    content: str

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

# File paths
CATEGORIES_FILE = "data/categories.csv"
NOTES_FILE = "data/notes.csv"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

def ensure_csv_exists(file_path, columns):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_path, index=False, encoding='utf-8')

def build_category_tree(df):
    """Build nested tree structure from flat categories"""
    # Convert to dict for quick lookup
    nodes = {}
    roots = []

    for _, row in df.iterrows():
        parent_id = None
        if pd.notna(row['parent_id']):
            parent_id = str(row['parent_id'])

        node = {
            "id": str(row['id']),
            "parent_id": parent_id,
            "level": str(row['level']),
            "name": str(row['name']),
            "created_at": str(row['created_at']),
            "children": []
        }
        nodes[node['id']] = node
        if node['level'] == 'level1':
            roots.append(node)

    # Attach children to parents
    for node_id in nodes:
        node = nodes[node_id]
        if node['parent_id'] is not None and node['parent_id'] in nodes:
            nodes[node['parent_id']]['children'].append(node)

    return roots

def get_category_path(cat_df, category_id):
    """Get full path from root to this category"""
    path = []
    current = category_id

    while current is not None:
        row = cat_df[cat_df['id'].astype(str) == str(current)]
        if row.empty:
            break
        row = row.iloc[0]
        path.insert(0, str(row['name']))
        current = row['parent_id'] if pd.notna(row['parent_id']) else None

    return ' → '.join(path)

# Notes App API routes
@app.get("/notes")
def notes_page():
    """Notes application page"""
    return FileResponse("static/notes.html")

@app.get("/api/notes/categories")
def get_categories():
    """Get all categories as nested tree structure"""
    ensure_csv_exists(CATEGORIES_FILE, ["id", "parent_id", "level", "name", "created_at"])
    df = pd.read_csv(CATEGORIES_FILE, encoding='utf-8', dtype={'id': str, 'parent_id': str})

    if df.empty:
        return []

    tree = build_category_tree(df)
    return tree

@app.post("/api/notes/categories")
def create_category(category_create: CategoryCreate):
    """Create a new category - supports incremental adding"""
    ensure_csv_exists(CATEGORIES_FILE, ["id", "parent_id", "level", "name", "created_at"])
    df = pd.read_csv(CATEGORIES_FILE, encoding='utf-8', dtype={'id': str, 'parent_id': str})

    new_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Determine level and parent
    if category_create.parent_level == 'root':
        level = 'level1'
        parent_id = None
    elif category_create.parent_level == 'level1':
        level = 'level2'
        parent_id = category_create.parent_id
    elif category_create.parent_level == 'level2':
        level = 'level3'
        parent_id = category_create.parent_id
    else:
        raise HTTPException(status_code=400, detail="Invalid parent level")

    # Check for duplicate name in same parent
    name_clean = category_create.name.strip()
    if parent_id is None:
        # Root level - check same level1 name
        mask = (df['level'] == 'level1') & (df['name'].astype(str).str.strip() == name_clean)
    else:
        # Check under same parent
        mask = (df['parent_id'].astype(str) == str(parent_id)) & (df['name'].astype(str).str.strip() == name_clean)

    if len(df[mask]) > 0:
        raise HTTPException(status_code=409, detail="同一个父分类下已有同名分类，请使用不同名称")

    new_row = pd.DataFrame([{
        "id": new_id,
        "parent_id": parent_id,
        "level": level,
        "name": name_clean,
        "created_at": now
    }])

    if df.empty:
        df = new_row
    else:
        df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv(CATEGORIES_FILE, index=False, encoding='utf-8')

    return {
        "id": new_id,
        "parent_id": parent_id,
        "level": level,
        "name": name_clean,
        "created_at": now
    }

@app.delete("/api/notes/categories/{category_id}")
def delete_category(category_id: str):
    """Delete a category and cascade delete all descendant categories and notes"""
    ensure_csv_exists(CATEGORIES_FILE, ["id", "parent_id", "level", "name", "created_at"])
    cat_df = pd.read_csv(CATEGORIES_FILE, encoding='utf-8', dtype={'id': str, 'parent_id': str})

    # Find all descendant ids including self
    to_delete = set([category_id])
    queue = deque([category_id])

    while queue:
        current = queue.popleft()
        children = cat_df[cat_df['parent_id'].astype(str) == current]['id'].astype(str)
        for child_id in children:
            to_delete.add(child_id)
            queue.append(child_id)

    # Delete all categories in to_delete
    cat_df = cat_df[~cat_df['id'].astype(str).isin(to_delete)]
    cat_df.to_csv(CATEGORIES_FILE, index=False, encoding='utf-8')

    # Cascade delete all notes in deleted categories
    ensure_csv_exists(NOTES_FILE, ["id", "category_id", "title", "content", "created_at", "updated_at"])
    notes_df = pd.read_csv(NOTES_FILE, encoding='utf-8')
    notes_df = notes_df[~notes_df['category_id'].astype(str).isin(to_delete)]
    notes_df.to_csv(NOTES_FILE, index=False, encoding='utf-8')

    return {"message": f"Deleted {len(to_delete)} categories and associated notes successfully"}

@app.get("/api/notes/category/{category_id}")
def get_notes_by_category(category_id: str):
    """Get all notes in a specific category"""
    ensure_csv_exists(NOTES_FILE, ["id", "category_id", "title", "content", "created_at", "updated_at"])
    df = pd.read_csv(NOTES_FILE, encoding='utf-8', dtype={'id': str, 'category_id': str})

    if df.empty:
        return []

    notes = df[df['category_id'].astype(str) == category_id].to_dict('records')
    # Convert all fields to strings for safety
    return [{k: str(v) if pd.notna(v) else "" for k, v in note.items()} for note in notes]

@app.get("/api/notes/search")
def search_notes(keyword: str):
    """Search notes by keyword in title or content"""
    ensure_csv_exists(NOTES_FILE, ["id", "category_id", "title", "content", "created_at", "updated_at"])
    ensure_csv_exists(CATEGORIES_FILE, ["id", "parent_id", "level", "name", "created_at"])

    notes_df = pd.read_csv(NOTES_FILE, encoding='utf-8', dtype={'id': str, 'category_id': str})
    cat_df = pd.read_csv(CATEGORIES_FILE, encoding='utf-8', dtype={'id': str, 'parent_id': str})

    if notes_df.empty:
        return []

    # Search in title and content (case-insensitive)
    keyword_lower = keyword.lower()
    mask = (
        notes_df['title'].astype(str).str.lower().str.contains(keyword_lower, na=False) |
        notes_df['content'].astype(str).str.lower().str.contains(keyword_lower, na=False)
    )

    results = []
    matched = notes_df[mask]

    for _, note in matched.iterrows():
        cat_id = str(note['category_id'])
        result = {
            "id": str(note['id']),
            "category_id": cat_id,
            "title": str(note['title']),
            "content": str(note['content']),
            "created_at": str(note['created_at']),
            "updated_at": str(note['updated_at']),
            "path": get_category_path(cat_df, cat_id)
        }
        results.append(result)

    return results

@app.get("/api/notes/{note_id}")
def get_note(note_id: str):
    """Get a single note by id with full category path"""
    ensure_csv_exists(NOTES_FILE, ["id", "category_id", "title", "content", "created_at", "updated_at"])
    ensure_csv_exists(CATEGORIES_FILE, ["id", "parent_id", "level", "name", "created_at"])

    notes_df = pd.read_csv(NOTES_FILE, encoding='utf-8', dtype={'id': str, 'category_id': str})
    cat_df = pd.read_csv(CATEGORIES_FILE, encoding='utf-8', dtype={'id': str, 'parent_id': str})

    if notes_df.empty:
        raise HTTPException(status_code=404, detail="Note not found")

    note = notes_df[notes_df['id'].astype(str) == note_id]
    if note.empty:
        raise HTTPException(status_code=404, detail="Note not found")

    result = note.iloc[0].to_dict()
    result = {k: str(v) if pd.notna(v) else "" for k, v in result.items()}

    # Add full category path
    category_id = result['category_id']
    result['path'] = get_category_path(cat_df, category_id)

    return result

@app.post("/api/notes")
def create_note(note_create: NoteCreate):
    """Create a new note"""
    ensure_csv_exists(NOTES_FILE, ["id", "category_id", "title", "content", "created_at", "updated_at"])
    df = pd.read_csv(NOTES_FILE, encoding='utf-8')

    new_id = str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_row = pd.DataFrame([{
        "id": new_id,
        "category_id": note_create.category_id,
        "title": note_create.title.strip(),
        "content": note_create.content.strip(),
        "created_at": now,
        "updated_at": now
    }])

    if df.empty:
        df = new_row
    else:
        df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv(NOTES_FILE, index=False, encoding='utf-8')

    return {
        "id": new_id,
        "category_id": note_create.category_id,
        "title": note_create.title.strip(),
        "content": note_create.content.strip(),
        "created_at": now,
        "updated_at": now
    }

@app.put("/api/notes/{note_id}")
def update_note(note_id: str, note_update: NoteUpdate):
    """Update an existing note"""
    ensure_csv_exists(NOTES_FILE, ["id", "category_id", "title", "content", "created_at", "updated_at"])
    df = pd.read_csv(NOTES_FILE, encoding='utf-8')

    mask = df['id'].astype(str) == note_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Note not found")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if note_update.title is not None:
        df.loc[mask, 'title'] = note_update.title.strip()
    if note_update.content is not None:
        df.loc[mask, 'content'] = note_update.content.strip()

    df.loc[mask, 'updated_at'] = now
    df.to_csv(NOTES_FILE, index=False, encoding='utf-8')

    return df[mask].iloc[0].to_dict()

@app.delete("/api/notes/{note_id}")
def delete_note(note_id: str):
    """Delete a note"""
    ensure_csv_exists(NOTES_FILE, ["id", "category_id", "title", "content", "created_at", "updated_at"])
    df = pd.read_csv(NOTES_FILE, encoding='utf-8')

    if (df['id'].astype(str) == note_id).sum() == 0:
        raise HTTPException(status_code=404, detail="Note not found")

    df = df[df['id'].astype(str) != note_id]
    df.to_csv(NOTES_FILE, index=False, encoding='utf-8')

    return {"message": "Note deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
