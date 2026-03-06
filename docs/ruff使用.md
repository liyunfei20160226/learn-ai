# 安装ruff
```bash
uv add --dev ruff
```

# 在pyproject.toml文件中配置
```toml
[tool.ruff]
# 假设你使用的是 Python 3.12，根据你的 .python-version 调整
target-version = "py312"

# 行宽限制 (默认 88，与 Black 一致)
line-length = 88

# 排除目录
exclude = [
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "*.egg-info",
]

# 启用的规则集
# F: Pyflakes (基础错误)
# E: pycodestyle (风格错误)
# W: pycodestyle (风格警告)
# I: isort (导入排序)
# UP: pyupgrade (自动升级语法)
# B: flake8-bugbear (常见 bug)
select = [
    "E", "W",    # 风格
    "F",         # 错误
    "I",         # 导入排序
    "UP",        # 语法升级
    "B",         # 常见 bug
    "C90",       # 复杂度
]

# 忽略的规则 (例如：忽略行过长警告 E501，因为 Ruff formatter 会自动处理换行)
ignore = ["E501"]

# 自动修复配置
[tool.ruff.format]
quote-style = "double" # 使用双引号
indent-style = "space" # 使用空格缩进
```

# 运行 Ruff 检查
```bash
uv run ruff check .
```

# 配置 VS Code 自动格式化与检查
```txt
打开设置：按 Ctrl + , (Mac: Cmd + ,)。
搜索 format。
找到 Editor: Default Formatter，在下拉菜单中选择 Ruff (ID: charliermarsh.ruff)。
勾选 Editor: Format On Save (保存时格式化)。
搜索 ruff。
确保勾选 Ruff: Enable (通常默认开启)。
(可选) 勾选 Ruff: Lint: Run 设置为 onType (输入时实时检查) 或 onSave (保存时检查)。推荐 onType 以获得即时反馈。
```