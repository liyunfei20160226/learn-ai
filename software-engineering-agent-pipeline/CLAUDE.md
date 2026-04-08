# Claude Ground Rules for this Project

## 核心规则

### 1. **代码提交**
- ❌ **绝对不能** 自行 `git push` 代码到 GitHub
- ✅ 必须修改完成后 **询问用户同意** 才能推送
- ✅ 用户同意后才能执行 push

### 2. **包管理**
- ✅ 这个项目使用 **uv** 作为包管理器
- ❌ 不要使用 Python 默认的 pip 管理依赖

### 3. **代码检查**
- ✅ 创建或更新代码后，必须运行 `uv run ruff check src/ --fix` 修复所有lint错误
- ✅ 确保 `ruff check` 全绿才能提交
