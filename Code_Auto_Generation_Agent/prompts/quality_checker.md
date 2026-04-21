根据以下技术栈和项目结构，生成质量检查命令。

技术栈：
{{tech_stack}}

项目结构：
{{project_tree}}

请输出 JSON 格式，包含以下字段：
- install: 安装依赖的命令列表（如 uv sync, npm install）
- lint: 代码质量检查命令列表（如 ruff check, npm run lint）
- type_check: 类型检查命令列表（如 mypy, tsc --noEmit）
- test: 测试执行命令列表（如 pytest, npm test）

要求：
1. 每个数组可以包含 0-N 个命令
2. 命令是相对项目根目录的 shell 命令
3. 如果某步不需要，返回空数组 []
4. 直接输出 JSON，不要用 markdown 代码块包裹
