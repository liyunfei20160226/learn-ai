# Claude Ground Rules for this Project

## 核心规则

### 1. **Git操作**
- ❌ **绝对禁止** 自行执行 `git add` / `git commit` / `git push` 任何git写操作
- ✅ 任何git操作（add/commit/push）都必须 **先询问用户同意**，得到许可后方可操作
- ✅ 用户同意后才能执行

### 2. **包管理**
- ✅ 这个项目使用 **uv** 作为包管理器
- ❌ 不要使用 Python 默认的 pip 管理依赖

### 3. **代码检查**
- ✅ 创建或更新代码后，必须运行 `uv run ruff check src/ --fix` 修复所有lint错误
- ✅ 确保 `ruff check` 全绿才能提交

### 4. **验证要求**
- ✅ 每次宣称成功后必须提供证据，并定期反问：真的完成了？有证据么？
