# CCS Generate - 执行指南

本文档指导 Claude 执行端到端全栈代码生成。

## 工作流概览

```
用户输入 → 1.解析参数 → 2.读取设计书 → 3.生成中文Markdown → 【用户确认解析文档】 → 4.分析数据库 → 5.创建表 → 6.生成后端 → 7.生成前端 → 8.生成测试 → 9.输出结果
```

## 步骤详解

### 步骤 1: 解析用户输入，确认设计文件存在

**目标**: 从用户自然语言中提取设计文件名，确认文件存在。

**动作**:
1. 调用 MCP 工具 `ccs_list_design_files` 列出所有可用设计文件
2. 从用户输入中提取文件名（用户会提到 `.xlsx` 文件名）
3. 调用 `ccs_get_design_info` 获取文件信息和工作表列表
4. 向用户确认是否继续（如果文件不存在要提示用户）

**用户确认**:
> "已找到设计文件 `{filename}`，包含以下工作表: {sheets}。是否继续生成？"

---

### 步骤 2: 读取所有工作表数据，提取图片

**目标**: 获取所有工作表数据和图片。

**动作**:
1. 对每个工作表调用 `ccs_read_design_sheet` 获取完整表格数据
2. 调用 `ccs_extract_images` 提取所有图片
3. **手动整理图片**: 如果提取出的图片 sheet_name 信息不完整（显示为 unknown），根据图片内容判断图片属于哪个 sheet，将图片移动到对应的 sheet 子目录 `./ccs/设计书/output/images/{设计名}/{sheet_name}/`
4. **解析图片内容**: 读懂图片中的内容（流程图、布局图），将图片内容用文字汇总整理，写到解析文档对应位置，方便用户确认
5. 保存 JSON 数据供后续处理

---

### 步骤 3: 翻译生成中文 Markdown 解析文档

**目标**: 生成中文解析文档保存到 `./ccs/设计书/output/`。

**翻译规则**:
- 使用 `translator.py` 中的对照表进行日文 → 中文翻译
- 保持表格结构不变
- 图片链接正确指向提取出的图片 (`images/{设计名}/{sheet_name}/`)
- **输出文件名**: 直接使用设计书名，改为 `.md` 扩展名。例如: `【CCS】画面定義書_小箱状況一覧_1.0.xlsx` → `【CCS】画面定義書_小箱状況一覧_1.0.md`
- **必须输出全部内容**: 设计书中**每个 sheet 的所有非空内容都必须输出**，不得省略任何内容，不得只输出骨架
- **文档结构**: **严格按照 sheet 在设计书中的原有顺序**，依次输出每个 sheet 的内容，每个 sheet 作为一个二级章节
- **重新解析时标识更新**: 如果设计文件已经解析过，再次重新解析时，比较内容差异，在文档末尾添加**更新内容汇总**，列出哪些地方有变更

**文档结构示例**:
```markdown
# {设计文件名} - 中文解析

## {Sheet1名称}（翻译后）
{Sheet1的**全部**表格内容，全部非空行都要输出}
{插入该sheet提取出的所有图片}

## {Sheet2名称}（翻译后）
{Sheet2的**全部**表格内容，全部非空行都要输出}
{插入该sheet提取出的所有图片}

... 依次输出**所有**sheet，一个都不能少
```

---

### 步骤 4: 用户确认解析文档

**目标**: 生成完解析文档后，必须等待用户确认，确认无误后才能继续生成代码。

**动作**:
1. 输出解析文档保存路径给用户
2. **必须提示用户检查确认**: "解析文档已生成，请检查内容是否正确。确认无误后回复"继续"开始生成代码。"
3. 只有收到用户确认（"继续"、"没问题"、确认语句）后，才能进入下一步
4. 如果用户提出修改意见，先修改解析文档，重新确认后再继续

---

### 步骤 5: 分析数据库设计，转换命名

**目标**: 分析设计书中的数据库表结构，转换为英文命名。

**动作**:
1. 从设计书的"DB設計"、"項目定義"、"項目一覧"等工作表提取**所有表**（包括本表和关联的其他表）和字段定义
2. 使用 `translator.py` 进行命名转换:
   - 日文表名 → 英文 snake_case
   - 日名字段名 → 英文 snake_case
   - 日文类型 → PostgreSQL 类型（使用类型映射表）
3. 整理出表结构定义
4. **检查关联表**: 如果设计书中提到了外键关联到其他表，即使该表的完整字段定义不在本设计书中，也要提取出已知字段创建表，剩余字段等后续设计书补充

**类型映射**（严格遵循）:

| 设计书类型 | PostgreSQL 类型 |
|-----------|-----------------|
| 文字列 / 文字 | `VARCHAR(n)` |
| 数値 / 整数 | `INTEGER` |
| 数値 / 小数 | `NUMERIC(18,2)` |
| 日付 | `DATE` |
| 日時 | `TIMESTAMP` |
| 真偽値 | `BOOLEAN` |
| テキスト | `TEXT` |

**命名规则**:
- **表名**: 日文 → 英译 → snake_case
  - 示例: `小箱状況一覧` → `small_box_status_list`
- **字段名**: 日文 → 英译 → snake_case
  - 示例: `郵便受付番号` → `postal_receipt_number`
- **必须添加**: `id` (SERIAL PRIMARY KEY), `created_at`, `updated_at`

---

### 步骤 6: 在数据库创建/更新表

**目标**: 使用 MCP 工具在 PostgreSQL `ccs` 数据库中创建或更新表。

**动作**:
1. 调用 `ccs_list_tables` 查看数据库中已有哪些表
2. 对**每个需要的表**（包括本表和所有关联表）:
   - **如果表不存在**: 生成 `CREATE TABLE` 语句执行创建
   - **如果表已存在**: 调用 `ccs_describe_table` 获取当前表结构，对比设计书，**如果缺少字段，生成 `ALTER TABLE ADD COLUMN` 语句添加缺失字段**
   - **关联表只有部分字段**: 即使只有部分字段，也要先创建表/添加已知字段，等后续其他设计书补充剩余字段
3. 每次执行 DDL 后调用 `ccs_describe_table` 验证表结构正确
4. 如果执行失败，显示错误信息和 SQL 语句，询问用户如何继续

**规则**:
- 永不删除表、永不删除已有字段
- 只创建新表或添加缺失字段
- 这样可以支持分多次设计书逐步完善同一个表的结构

---

### 步骤 7: 生成后端代码

**目标**: 在 `./ccs/backend/` 生成后端代码。

**生成位置**（严格遵循现有项目结构）:

| 组件 | 路径 | 模板 |
|------|------|------|
| SQLAlchemy 模型 | `app/models/{table_name}.py` | `templates/backend/model.py.template` |
| Pydantic Schema | `app/schemas/{table_name}.py` | `templates/backend/schema.py.template` |
| 业务逻辑 Service | `app/services/{table_name}.py` | `templates/backend/service.py.template` |
| FastAPI 路由 | `app/api/endpoints/{table_name}.py` | `templates/backend/router.py.template` |

**代码规则**:
- 模型继承自 `app.core.database: Base`
- 使用 `app.core.database: get_db` 依赖
- 遵循 PEP 8 命名规范
- 添加适当的类型注解
- CRUD 全部实现: `list`, `get`, `create`, `update`, `delete`

---

### 步骤 8: 生成前端代码

**目标**: 在 `./ccs/frontend/` 生成前端代码。

**生成位置**:

| 组件 | 路径 | 模板 |
|------|------|------|
| TypeScript 类型 | `src/types/{feature_name}.ts` | `templates/frontend/types.ts.template` |
| API 客户端 | `src/api/{feature_name}.ts` | `templates/frontend/api.ts.template` |
| Next.js 页面 | `src/app/{feature_name}/page.tsx` | `templates/frontend/page.tsx.template` |

**代码规则**:
- 使用 TypeScript 严格模式
- 使用 Tailwind CSS 样式
- 遵循 Next.js 15 App Router 约定
- 实现列表展示、搜索、分页、表单
- 使用 fetch 或 axios 调用后端 API

---

### 步骤 9: 生成测试代码（要求 100% 覆盖率）

**目标**: 生成完整的测试代码，覆盖所有功能。

**后端测试**:
- 位置: `backend/tests/test_{table_name}.py`
- 模板: `templates/backend/test.py.template`
- 必须测试:
  - 所有 CRUD 端点
  - 成功场景
  - 失败场景（404、验证错误）
  - 使用 pytest
  - 使用测试数据库事务回滚

**前端测试**（如果有）:
- 位置: `frontend/__tests__/{feature_name}.test.tsx`
- 使用 Jest + React Testing Library
- 测试组件渲染
- 测试用户交互

---

### 步骤 10: 汇总输出结果

**目标**: 向用户展示所有生成的文件，提供测试命令。

**输出格式**:

```
✅ 端到端代码生成完成！

📄 生成的解析文档:
- ./ccs/设计书/output/{file}.md
- 🖼️  提取图片:
- ./ccs/设计书/output/images/{file}/{sheet_name}/

🗄️  数据库:
- 已创建表: {table_name}

⚙️  后端代码:
- backend/app/models/{table_name}.py
- backend/app/schemas/{table_name}.py
- backend/app/services/{table_name}.py
- backend/app/api/endpoints/{table_name}.py
- backend/tests/test_{table_name}.py

🎨  前端代码:
- frontend/src/types/{feature_name}.ts
- frontend/src/api/{feature_name}.ts
- frontend/src/app/{feature_name}/page.tsx

🧪  测试命令:

# 运行后端测试
cd ccs/backend
uv run pytest tests/test_{table_name}.py -v

# 运行后端测试覆盖率
cd ccs/backend
uv run pytest tests/test_{table_name}.py --cov=app
```

## 错误处理

1. **文件不存在**: 列出所有可用文件让用户选择
2. **翻译不确定**: 保留原文，添加 `<!-- TODO: 检查翻译 -->` 注释
3. **表已存在**: 询问用户是否覆盖
4. **数据库创建失败**: 显示错误 SQL，询问用户如何继续
5. **覆盖现有文件**: 生成前必须询问用户确认

## 权限提醒

生成大量文件前，提醒用户:
- 建议先提交现有代码到 Git
- Skill 只会新增文件，不会删除现有文件
- 如果文件已存在会询问是否覆盖
