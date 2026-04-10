# 添加扫雷游戏 - 任务清单

- [x] 创建 `static/minesweeper.html` - 游戏页面 HTML
- [x] 创建 `static/minesweeper.css` - 游戏样式（玻璃拟态风格）
- [x] 创建 `static/minesweeper.js` - 游戏逻辑（类架构）
- [x] 修改 `main.py` - 添加 `/minesweeper` 路由
- [x] 修改 `static/index.html` - 主页添加扫雷项目卡片
- [x] 测试验证所有路由 ✅

---

# 首页分类导航改造

## 任务拆分

- [x] 1. 修改 `static/index.html` - 将首页改为分类卡片展示
- [x] 2. 新增 `static/category.html` - 分类页面模板 + JavaScript
- [x] 3. 新增 `static/category.css` - 分类页面样式
- [x] 4. 修改 `main.py` - 添加 `/category` 路由
- [x] 5. 测试验证功能 ✅

---

# 新增三级分类笔记应用

## 任务拆分

- [x] 1. 创建 `data/` 目录
- [x] 2. 更新 `pyproject.toml` - 添加 pandas 依赖
- [x] 3. 修改 `main.py` - 添加 pandas 导入、Pydantic 模型、API 路由
- [x] 4. 创建 `static/notes.html` - 笔记应用主页面
- [x] 5. 创建 `static/notes.css` - 样式（玻璃拟态风格）
- [x] 6. 创建 `static/notes.js` - 前端应用逻辑
- [x] 7. 更新 `static/category.html` - 添加笔记应用到效率工具类
- [x] 8. 更新 `static/index.html` - 更新项目计数
- [x] 9. **优化**: 修改为真正的层级存储，支持逐级添加分类，无需一次性填完三级 ✅
- [x] 10. 测试验证功能 ✅

## 修改说明

**原始需求**: 用户可以逐级添加分类，先建大分类，以后再添加中分类、小分类，不需要一开始就填完三级。

**修改内容**:
1. **后端 `main.py`**: 数据结构从扁平化三级存储改为真正的层级存储
   - 每个分类节点单独存储，包含 `id`, `parent_id`, `level`, `name`, `created_at`
   - 支持递归级联删除：删除父分类会自动删除所有子分类和笔记
   - 树形结构递归组装，搜索结果返回完整路径
   
2. **前端 `notes.js`**: 适配新的数据结构
   - 递归渲染树形结构，支持动态缩进
   - 每个层级都可以点击"+ 添加子分类"
   - 只有小分类(level3)才能选择并添加笔记
   - 搜索结果显示完整分类路径

3. **样式 `notes.css`**: 适配新树形结构
   - 支持动态缩进
   - 所有层级都显示删除按钮（hover 时可见）
