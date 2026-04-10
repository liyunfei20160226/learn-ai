class NotesApp {
    constructor() {
        this.categoriesTree = [];
        this.notes = [];
        this.currentCategoryId = null;
        this.currentNoteId = null;
        this.expanded = new Set(); // 存储展开的节点ID
        this.isEditing = false;
        this.editingNoteId = null;
        this.pendingDeleteCallback = null;
    }

    async init() {
        this.bindEvents();
        await this.loadCategories();
        this.renderCategoryTree();
    }

    bindEvents() {
        // Add category button
        document.getElementById('addCategoryBtn').addEventListener('click', () => this.openCategoryModal());
        document.querySelector('#categoryModal .close').addEventListener('click', () => this.closeCategoryModal());
        document.getElementById('cancelCategoryBtn').addEventListener('click', () => this.closeCategoryModal());
        document.getElementById('confirmCategoryBtn').addEventListener('click', () => this.createCategory());

        // Add note button
        document.getElementById('addNoteBtn').addEventListener('click', () => this.openNoteModal());
        document.querySelector('#noteModal .close').addEventListener('click', () => this.closeNoteModal());
        document.getElementById('cancelNoteBtn').addEventListener('click', () => this.closeNoteModal());
        document.getElementById('confirmNoteBtn').addEventListener('click', () => this.createOrUpdateNote());

        // Note detail modal
        document.querySelector('#noteDetailModal .close').addEventListener('click', () => this.closeDetailModal());
        document.getElementById('closeDetailBtn').addEventListener('click', () => this.closeDetailModal());
        document.getElementById('editNoteBtn').addEventListener('click', () => this.startEditNote());
        document.getElementById('deleteNoteBtn').addEventListener('click', () => this.deleteNoteConfirm());

        // Confirm delete modal
        document.querySelector('#confirmModal .close').addEventListener('click', () => this.closeConfirmModal());
        document.getElementById('cancelConfirmBtn').addEventListener('click', () => this.closeConfirmModal());
        document.getElementById('confirmDeleteBtn').addEventListener('click', () => this.confirmDelete());

        // Search
        document.getElementById('searchBtn').addEventListener('click', () => this.search());
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.search();
        });

        // Click outside modal to close
        window.addEventListener('click', (e) => {
            if (e.target.id === 'categoryModal') this.closeCategoryModal();
            if (e.target.id === 'noteModal') this.closeNoteModal();
            if (e.target.id === 'noteDetailModal') this.closeDetailModal();
            if (e.target.id === 'confirmModal') this.closeConfirmModal();
        });
    }

    async loadCategories() {
        try {
            const response = await fetch('/api/notes/categories');
            this.categoriesTree = await response.json();
        } catch (error) {
            console.error('Failed to load categories:', error);
            this.showEmptyTree();
        }
    }

    renderCategoryTree() {
        const container = document.getElementById('categoryTree');

        if (this.categoriesTree.length === 0) {
            this.showEmptyTree();
            return;
        }

        let html = '';
        this.categoriesTree.forEach(node => {
            html += this.renderNode(node, 0);
        });

        container.innerHTML = html;
    }

    renderNode(node, depth) {
        const isExpanded = this.expanded.has(node.id);
        const expandedClass = isExpanded ? 'expanded' : '';
        const collapsedClass = isExpanded ? '' : 'collapsed';
        const activeClass = this.currentCategoryId === node.id ? 'active' : '';

        // Different padding based on depth
        const padding = depth * 16;

        // Get button text based on current level
        let addBtnText = '';
        if (node.level === 'level1') {
            addBtnText = '+ 添加中分类';
        } else if (node.level === 'level2') {
            addBtnText = '+ 添加小分类';
        }

        // Click handler: for level3, select it; for others just toggle expand
        let clickHandler;
        if (node.level === 'level3') {
            clickHandler = `onclick="app.selectCategory('${node.id}'); event.stopPropagation();"`;
        } else {
            clickHandler = `onclick="app.toggleExpand('${node.id}'); event.stopPropagation();"`;
        }

        let html = `
            <div class="category-item">
                <div class="category-level${depth + 1} ${expandedClass} ${activeClass}" style="padding-left: ${padding}px;" ${clickHandler}>
                    ${node.children && node.children.length > 0 ? `<span class="toggle">▶</span>` : '<span class="toggle toggle-empty"></span>'}
                    <span class="toggle-text">${this.escapeHtml(node.name)}</span>
                    ${addBtnText ? `<button class="add-sub-btn" onclick="app.openAddSubcategory('${node.id}', '${node.level}', '${node.name.replace(/'/g, '\\\'')}'); event.stopPropagation();">${addBtnText}</button>` : ''}
                    <button class="delete-btn" onclick="app.deleteCategory('${node.id}'); event.stopPropagation();">删除</button>
                </div>
                ${node.children && node.children.length > 0 ? `<div class="children-container ${collapsedClass}">` : ''}
        `;

        if (node.children && node.children.length > 0) {
            node.children.forEach(child => {
                html += this.renderNode(child, depth + 1);
            });
            html += `</div>`;
        }

        html += `</div>`;

        return html;
    }

    showEmptyTree() {
        document.getElementById('categoryTree').innerHTML = `
            <div class="empty-state">
                还没有分类，请点击上方"添加分类"创建第一个分类
            </div>
        `;
    }

    toggleExpand(nodeId) {
        if (this.expanded.has(nodeId)) {
            this.expanded.delete(nodeId);
        } else {
            this.expanded.add(nodeId);
        }
        this.renderCategoryTree();
    }

    async selectCategory(categoryId) {
        this.currentCategoryId = categoryId;
        document.getElementById('addNoteBtn').disabled = false;
        await this.loadNotes();
        this.renderCategoryTree();
        this.renderNotes();
    }

    async loadNotes() {
        if (!this.currentCategoryId) {
            this.notes = [];
            return;
        }

        try {
            const response = await fetch(`/api/notes/category/${this.currentCategoryId}`);
            this.notes = await response.json();
        } catch (error) {
            console.error('Failed to load notes:', error);
            this.notes = [];
        }
    }

    renderNotes() {
        const container = document.getElementById('notesList');

        if (!this.currentCategoryId) {
            container.innerHTML = `<div class="empty-state">请在左侧选择一个小分类</div>`;
            return;
        }

        if (this.notes.length === 0) {
            container.innerHTML = `<div class="empty-state">该分类下还没有笔记，点击上方"新建笔记"添加</div>`;
            return;
        }

        let html = '';
        this.notes.forEach(note => {
            const preview = note.content.length > 80 ? note.content.substring(0, 80) + '...' : note.content;
            html += `
                <div class="note-item" onclick="app.openNoteDetail('${note.id}')">
                    <div class="note-item-title">${this.escapeHtml(note.title)}</div>
                    <div class="note-item-preview">${this.escapeHtml(preview)}</div>
                    <div class="note-item-meta">更新于 ${this.escapeHtml(note.updated_at)}</div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async search() {
        const keyword = document.getElementById('searchInput').value.trim();
        if (!keyword) {
            this.renderNotes();
            return;
        }

        try {
            const response = await fetch(`/api/notes/search?keyword=${encodeURIComponent(keyword)}`);
            const results = await response.json();

            const container = document.getElementById('notesList');

            if (results.length === 0) {
                container.innerHTML = `<div class="empty-state">没有找到包含"${this.escapeHtml(keyword)}"的笔记</div>`;
                return;
            }

            let html = '';
            results.forEach(note => {
                const preview = note.content.length > 80 ? note.content.substring(0, 80) + '...' : note.content;
                html += `
                    <div class="note-item" onclick="app.openSearchResultDetail(${JSON.stringify(note).replace(/"/g, '&quot;')})">
                        <div class="search-result-path">${this.escapeHtml(note.path)}</div>
                        <div class="note-item-title">${this.escapeHtml(note.title)}</div>
                        <div class="note-item-preview">${this.escapeHtml(preview)}</div>
                        <div class="note-item-meta">更新于 ${this.escapeHtml(note.updated_at)}</div>
                    </div>
                `;
            });

            container.innerHTML = html;
        } catch (error) {
            console.error('Search failed:', error);
            alert('搜索失败，请重试');
        }
    }

    openCategoryModal() {
        // Adding root level1 category from scratch
        this.addParentInfo = null;
        document.getElementById('categoryModalTitle').textContent = '添加大分类';
        document.getElementById('level1Group').style.display = 'block';
        document.getElementById('level2Group').style.display = 'none';
        document.getElementById('level3Group').style.display = 'none';
        document.getElementById('parentPath').style.display = 'none';
        document.getElementById('level1').value = '';
        document.getElementById('level2').value = '';
        document.getElementById('level3').value = '';
        document.getElementById('categoryModal').classList.add('active');
    }

    openAddSubcategory(parentId, parentLevel, parentName) {
        this.addParentInfo = { parentId, parentLevel, parentName };
        document.getElementById('categoryModal').classList.add('active');

        if (parentLevel === 'level1') {
            document.getElementById('categoryModalTitle').textContent = '添加中分类';
            document.getElementById('level1Group').style.display = 'none';
            document.getElementById('level2Group').style.display = 'block';
            document.getElementById('level3Group').style.display = 'none';
            document.getElementById('parentPath').style.display = 'block';
            document.getElementById('parentPath').textContent = `父分类：${parentName}`;
            document.getElementById('level2').value = '';
        } else if (parentLevel === 'level2') {
            document.getElementById('categoryModalTitle').textContent = '添加小分类';
            document.getElementById('level1Group').style.display = 'none';
            document.getElementById('level2Group').style.display = 'none';
            document.getElementById('level3Group').style.display = 'block';
            document.getElementById('parentPath').style.display = 'block';
            document.getElementById('parentPath').textContent = `父分类：${parentName}`;
            document.getElementById('level3').value = '';
        }

        // Auto expand parent
        this.expanded.add(parentId);
    }

    closeCategoryModal() {
        document.getElementById('categoryModal').classList.remove('active');
        this.addParentInfo = null;
    }

    async createCategory() {
        // Clear previous error
        let errorEl = document.getElementById('categoryError');
        if (errorEl) {
            errorEl.style.display = 'none';
            errorEl.textContent = '';
        }

        let name = '';
        let parentLevel = null;
        let parentId = null;

        if (!this.addParentInfo) {
            // Creating root level1
            name = document.getElementById('level1').value.trim();
            parentLevel = 'root';
            if (!name) {
                if (errorEl) {
                    errorEl.textContent = '请输入大分类名称';
                    errorEl.style.display = 'block';
                } else {
                    alert('请输入大分类名称');
                }
                return;
            }
        } else if (this.addParentInfo.parentLevel === 'level1') {
            // Creating level2 under level1
            name = document.getElementById('level2').value.trim();
            parentLevel = 'level1';
            parentId = this.addParentInfo.parentId;
            if (!name) {
                if (errorEl) {
                    errorEl.textContent = '请输入中分类名称';
                    errorEl.style.display = 'block';
                } else {
                    alert('请输入中分类名称');
                }
                return;
            }
        } else if (this.addParentInfo.parentLevel === 'level2') {
            // Creating level3 under level2
            name = document.getElementById('level3').value.trim();
            parentLevel = 'level2';
            parentId = this.addParentInfo.parentId;
            if (!name) {
                if (errorEl) {
                    errorEl.textContent = '请输入小分类名称';
                    errorEl.style.display = 'block';
                } else {
                    alert('请输入小分类名称');
                }
                return;
            }
        }

        try {
            const response = await fetch('/api/notes/categories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    parent_level: parentLevel,
                    parent_id: parentId,
                    name: name
                })
            });

            if (!response.ok) {
                let errorMsg = '创建分类失败，请重试';
                try {
                    const errorData = await response.json();
                    if (errorData.detail) {
                        errorMsg = errorData.detail;
                    }
                } catch (e) {
                    // ignore
                }
                if (errorEl) {
                    errorEl.textContent = errorMsg;
                    errorEl.style.display = 'block';
                } else {
                    alert(errorMsg);
                }
                return;
            }

            this.closeCategoryModal();
            await this.loadCategories();

            if (this.addParentInfo) {
                // Auto expand parent
                this.expanded.add(this.addParentInfo.parentId);
            }

            this.renderCategoryTree();
        } catch (error) {
            console.error('Failed to create category:', error);
            if (errorEl) {
                errorEl.textContent = '网络错误，请重试';
                errorEl.style.display = 'block';
            } else {
                alert('网络错误，请重试');
            }
        }
    }

    closeCategoryModal() {
        document.getElementById('categoryModal').classList.remove('active');
        this.addParentInfo = null;
        // Clear error when closing
        const errorEl = document.getElementById('categoryError');
        if (errorEl) {
            errorEl.style.display = 'none';
            errorEl.textContent = '';
        }
    }

    openConfirmModal(message, callback) {
        this.pendingDeleteCallback = callback;
        document.getElementById('confirmMessage').textContent = message;
        document.getElementById('confirmModal').classList.add('active');
    }

    closeConfirmModal() {
        document.getElementById('confirmModal').classList.remove('active');
        this.pendingDeleteCallback = null;
    }

    confirmDelete() {
        if (this.pendingDeleteCallback) {
            this.pendingDeleteCallback();
        }
        this.closeConfirmModal();
    }

    deleteCategory(categoryId) {
        this.openConfirmModal(
            '确定要删除这个分类吗？分类下的所有子分类和笔记也会被删除，此操作不可恢复。',
            async () => {
                try {
                    const response = await fetch(`/api/notes/categories/${categoryId}`, {
                        method: 'DELETE'
                    });

                    if (!response.ok) {
                        throw new Error('Delete failed');
                    }

                    if (this.currentCategoryId === categoryId) {
                        this.currentCategoryId = null;
                        this.notes = [];
                        this.renderNotes();
                    }

                    this.expanded.delete(categoryId);
                    await this.loadCategories();
                    this.renderCategoryTree();
                } catch (error) {
                    console.error('Failed to delete category:', error);
                    alert('删除失败，请重试');
                }
            }
        );
    }

    openNoteModal() {
        document.getElementById('noteModal').classList.add('active');
        document.getElementById('noteModalTitle').textContent = this.isEditing ? '编辑笔记' : '新建笔记';
        document.getElementById('noteTitle').value = '';
        document.getElementById('noteContent').value = '';
        this.isEditing = false;
        this.editingNoteId = null;
    }

    closeNoteModal() {
        document.getElementById('noteModal').classList.remove('active');
    }

    async createOrUpdateNote() {
        const title = document.getElementById('noteTitle').value.trim();
        const content = document.getElementById('noteContent').value.trim();

        if (!title) {
            alert('请输入笔记标题');
            return;
        }

        if (!this.currentCategoryId) {
            alert('请先在左侧选择一个小分类');
            return;
        }

        try {
            if (this.isEditing) {
                // Update
                const response = await fetch(`/api/notes/${this.editingNoteId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, content })
                });

                if (!response.ok) {
                    throw new Error('Update failed');
                }
            } else {
                // Create
                const response = await fetch('/api/notes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        category_id: this.currentCategoryId,
                        title,
                        content
                    })
                });

                if (!response.ok) {
                    throw new Error('Create failed');
                }
            }

            this.closeNoteModal();
            await this.loadNotes();
            this.renderNotes();
        } catch (error) {
            console.error('Failed to save note:', error);
            alert('保存失败，请重试');
        }
    }

    async openNoteDetail(noteId) {
        try {
            const response = await fetch(`/api/notes/${noteId}`);
            if (!response.ok) {
                throw new Error('Not found');
            }
            const note = await response.json();
            this.currentNoteId = noteId;

            document.getElementById('detailTitle').textContent = note.title;
            document.getElementById('detailPath').textContent = note.path;
            document.getElementById('detailContent').textContent = note.content;
            document.getElementById('detailCreated').textContent = `创建: ${note.created_at}`;
            document.getElementById('detailUpdated').textContent = `更新: ${note.updated_at}`;

            document.getElementById('noteDetailModal').classList.add('active');
        } catch (error) {
            console.error('Failed to load note detail:', error);
            alert('加载笔记详情失败');
        }
    }

    openSearchResultDetail(note) {
        document.getElementById('detailTitle').textContent = note.title;
        document.getElementById('detailPath').textContent = note.path;
        document.getElementById('detailContent').textContent = note.content;
        document.getElementById('detailCreated').textContent = `创建: ${note.created_at}`;
        document.getElementById('detailUpdated').textContent = `更新: ${note.updated_at}`;
        this.currentNoteId = note.id;
        document.getElementById('noteDetailModal').classList.add('active');
    }

    closeDetailModal() {
        document.getElementById('noteDetailModal').classList.remove('active');
    }

    startEditNote() {
        // Close detail modal and open edit modal
        this.closeDetailModal();
        this.isEditing = true;
        this.editingNoteId = this.currentNoteId;

        // Load current note data
        fetch(`/api/notes/${this.editingNoteId}`)
            .then(res => res.json())
            .then(note => {
                document.getElementById('noteModal').classList.add('active');
                document.getElementById('noteModalTitle').textContent = '编辑笔记';
                document.getElementById('noteTitle').value = note.title;
                document.getElementById('noteContent').value = note.content;
            })
            .catch(err => {
                console.error(err);
                alert('加载笔记内容失败');
            });
    }

    deleteNoteConfirm() {
        this.openConfirmModal(
            '确定要删除这篇笔记吗？此操作不可恢复。',
            async () => {
                try {
                    const response = await fetch(`/api/notes/${this.currentNoteId}`, {
                        method: 'DELETE'
                    });

                    if (!response.ok) {
                        throw new Error('Delete failed');
                    }

                    this.closeDetailModal();
                    await this.loadNotes();
                    this.renderNotes();
                } catch (error) {
                    console.error('Failed to delete note:', error);
                    alert('删除失败，请重试');
                }
            }
        );
    }

    escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.app = new NotesApp();
    window.app.init();
});
