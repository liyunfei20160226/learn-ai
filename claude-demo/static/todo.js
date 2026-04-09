class TodoApp {
    constructor() {
        this.todos = [];
        this.currentFilter = 'all';
        this.init();
    }

    async init() {
        this.bindEvents();
        await this.loadTodos();
        this.render();
    }

    bindEvents() {
        document.getElementById('addBtn').addEventListener('click', () => this.addTodo());
        document.getElementById('todoTitle').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addTodo();
        });
        document.getElementById('clearCompleted').addEventListener('click', () => this.clearCompleted());

        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelector('.filter-btn.active').classList.remove('active');
                e.target.classList.add('active');
                this.currentFilter = e.target.dataset.filter;
                this.render();
            });
        });
    }

    async loadTodos() {
        try {
            const response = await fetch('/api/todos');
            this.todos = await response.json();
        } catch (error) {
            console.error('Failed to load todos:', error);
        }
    }

    async addTodo() {
        const titleInput = document.getElementById('todoTitle');
        const descInput = document.getElementById('todoDescription');

        const title = titleInput.value.trim();
        const description = descInput.value.trim();

        if (!title) {
            this.shakeInput(titleInput);
            return;
        }

        try {
            const response = await fetch('/api/todos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, description })
            });

            if (response.ok) {
                const newTodo = await response.json();
                this.todos.push(newTodo);
                titleInput.value = '';
                descInput.value = '';
                this.render();
                titleInput.focus();
            }
        } catch (error) {
            console.error('Failed to add todo:', error);
        }
    }

    async toggleTodo(id) {
        const todo = this.todos.find(t => t.id === id);
        if (!todo) return;

        try {
            const response = await fetch(`/api/todos/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ completed: !todo.completed })
            });

            if (response.ok) {
                const updatedTodo = await response.json();
                todo.completed = updatedTodo.completed;
                this.render();
            }
        } catch (error) {
            console.error('Failed to update todo:', error);
        }
    }

    async deleteTodo(id) {
        const todoElement = document.querySelector(`[data-id="${id}"]`);
        if (todoElement) {
            todoElement.classList.add('fade-out');
            await new Promise(resolve => setTimeout(resolve, 300));
        }

        try {
            const response = await fetch(`/api/todos/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.todos = this.todos.filter(t => t.id !== id);
                this.render();
            }
        } catch (error) {
            console.error('Failed to delete todo:', error);
            this.render();
        }
    }

    async clearCompleted() {
        try {
            const response = await fetch('/api/todos/completed', {
                method: 'DELETE'
            });

            if (response.ok) {
                await this.loadTodos();
                this.render();
            }
        } catch (error) {
            console.error('Failed to clear completed:', error);
        }
    }

    getFilteredTodos() {
        switch (this.currentFilter) {
            case 'active':
                return this.todos.filter(t => !t.completed);
            case 'completed':
                return this.todos.filter(t => t.completed);
            default:
                return this.todos;
        }
    }

    render() {
        const todoList = document.getElementById('todoList');
        const filteredTodos = this.getFilteredTodos();
        const activeCount = this.todos.filter(t => !t.completed).length;

        document.getElementById('itemsLeft').textContent =
            `${activeCount} 个待办事项`;

        if (this.todos.length === 0) {
            todoList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-emoji">📝</div>
                    <div class="empty-state-text">还没有待办事项，添加一个开始吧！</div>
                </div>
            `;
            this.updateStats();
            return;
        }

        if (filteredTodos.length === 0) {
            todoList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-text">当前筛选条件下没有待办事项</div>
                </div>
            `;
            this.updateStats();
            return;
        }

        todoList.innerHTML = filteredTodos.map(todo => `
            <div class="todo-item ${todo.completed ? 'completed' : ''}" data-id="${todo.id}">
                <div class="checkbox ${todo.completed ? 'checked' : ''}"
                     onclick="app.toggleTodo('${todo.id}')">
                </div>
                <div class="todo-content">
                    <div class="todo-title">${this.escapeHtml(todo.title)}</div>
                    ${todo.description ? `<div class="todo-description">${this.escapeHtml(todo.description)}</div>` : ''}
                    <span class="todo-time">🕒 ${todo.created_at}</span>
                </div>
                <button class="delete-btn" onclick="app.deleteTodo('${todo.id}')">🗑️</button>
            </div>
        `).join('');

        this.updateStats();
    }

    updateStats() {
        const activeCount = this.todos.filter(t => !t.completed).length;
        const hasCompleted = this.todos.some(t => t.completed);
        const clearBtn = document.getElementById('clearCompleted');
        clearBtn.style.display = hasCompleted ? 'block' : 'none';
    }

    shakeInput(input) {
        input.style.border = '2px solid #f5576c';
        input.animate([
            { transform: 'translateX(0)' },
            { transform: 'translateX(-10px)' },
            { transform: 'translateX(10px)' },
            { transform: 'translateX(-10px)' },
            { transform: 'translateX(0)' }
        ], { duration: 300 });

        setTimeout(() => {
            input.style.border = 'none';
        }, 300);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TodoApp();
});
