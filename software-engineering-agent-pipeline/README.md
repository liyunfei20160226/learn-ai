# 软件工程多Agent流水线系统 (Software Engineering Multi-Agent Pipeline)

基于 LangGraph 的软件工程全流程多Agent协作流水线。

## 需求分析阶段 (当前完成)

三个Agent协作完成需求澄清：

| Agent | 职责 |
|-------|------|
| `RequirementsAnalystAgent` | 分析模糊需求，主动提问逐步澄清 |
| `RequirementsVerifierAgent` | 独立验证，发现遗漏则要求继续提问 |
| `RequirementsFinalAgent` | 整理生成标准化需求规格文档 |

## 快速开始

1. 配置API密钥：复制 `.env.example` 为 `.env` 并填入你的API信息
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，设置 OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
   # 如果要启用知识图谱，添加: MEMORY_MCP_BASE_URL=http://localhost:8000
   ```

2. 安装依赖
   ```bash
   uv sync
   uv pip install -e .
   ```

3. （可选）启动知识图谱HTTP服务
   ```bash
   cd memory-mcp
   # Windows
   start-http.bat
   # Linux/macOS
   ./start-http.sh
   ```

4. 运行交互式需求分析
   ```bash
   # 使用默认参数快速启动（project-id: interactive-001）
   uv run python examples/interactive_requirements_analysis.py
   
   # 新建项目，指定项目ID和名称
   uv run python examples/interactive_requirements_analysis.py --project-id "my-project" --project-name "我的项目"
   
   # 继续已有项目（断点续问）
   uv run python examples/interactive_requirements_analysis.py --project-id "my-project"
   ```

5. 启动Web界面
   ```bash
   # 启动Web服务器（默认端口 8000）
   uv run python examples/web_server.py
   
   # 然后在浏览器打开 http://localhost:8000
   
   # 指定自定义端口
   uv run python examples/web_server.py --port 8080
   ```

## 常用测试命令

### 运行单元测试（不需要API，全部mock）
```bash
uv run pytest tests/se_pipeline/agents/ -v
```

### 运行集成测试（使用真实LLM验证Agent功能）
```bash
uv run pytest tests/integration/ -v -m integration
```

### 查看单元测试覆盖率
```bash
uv run pytest tests/se_pipeline/agents/ --cov=src/se_pipeline/agents --cov-report=term
```

### pipeline_graph 模块测试
```bash
# 运行 graph 模块所有单元测试
uv run python -m pytest tests/se_pipeline/graph/test_pipeline_graph_functions.py -v

# 查看 graph 模块覆盖率
uv run python -m pytest tests/se_pipeline/graph/test_pipeline_graph_functions.py --cov=se_pipeline.graph.pipeline_graph --cov-report=term-missing
```

### quality_gate 自动评审模块测试
```bash
# 运行 auto_reviewer 单元测试
uv run pytest tests/se_pipeline/quality_gate/test_auto_reviewer.py -v

# 查看 quality_gate 模块覆盖率
uv run pytest tests/se_pipeline/quality_gate/test_auto_reviewer.py --cov=se_pipeline.quality_gate --cov-report=term
```

### storage 项目存储模块测试
```bash
# 运行 project_store 单元测试
uv run pytest tests/se_pipeline/storage/test_project_store.py -v

# 查看 project_store 模块覆盖率
uv run pytest tests/se_pipeline/storage/test_project_store.py --cov=se_pipeline.storage.project_store --cov-report=term
```

### knowledge 知识图谱模块测试
```bash
# 运行 memory_mcp_client 单元测试
uv run pytest tests/se_pipeline/knowledge/test_memory_mcp_client.py -v

# 查看 memory_mcp_client 模块覆盖率
uv run pytest tests/se_pipeline/knowledge/test_memory_mcp_client.py --cov=se_pipeline.knowledge.memory_mcp_client --cov-report=term
```

## 知识图谱集成

本项目集成了 [memory-mcp](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) 知识图谱，可以自动将项目和需求信息保存到知识图谱中，后续阶段可以读取上下文保持一致性。

### 启动知识图谱 HTTP 服务

```bash
cd memory-mcp
npm install
npm run build

# Windows
./start-http.bat

# Linux/macOS
./start-http.sh
```

默认端口 `8000`，指定端口：`./start-http.sh 8080`

### 配置

在 `.env` 中添加：
```
MEMORY_MCP_BASE_URL=http://localhost:8000
```

### 存储位置

知识图谱默认持久化存储在 `memory-mcp/memory.jsonl`。可以通过环境变量自定义路径：
```bash
export MEMORY_FILE_PATH=/path/to/your/memory.jsonl
./start-http.sh
```

## TODO / 待改进

### Excel 文档处理改进

当前问题：Excel 中提取出来的图片，如果不属于某个 sheet，则无法判断其在哪个具体 sheet 中。目前的做法是直接给多模态 LLM，让模型分析应该属于哪个 sheet。

改进方案：

1. **第一步**：将 Excel 的每个 sheet，通过 pandas 转成 dataframe，再转成 markdown 文档  
   ✅ 这一步已经实现  
   ✅ 表格数据转换准确，不会丢单元格数据

2. **第二步**：将 Excel 整体转成 PDF，再将 PDF 的每一页转换成图片，分别给多模态 LLM 进行 OCR，分析转换成临时的 markdown 文件  
   - PDF分页自然分片，即使大sheet也能正确处理，不会因为太大丢信息
   - 每页OCR能提取出该页上的所有图片，并保留图片在页面中的位置信息

3. **第三步**：将第一步（表格结构化转换）和第二步（PDF图片OCR）得到的所有内容再次交给 LLM 分析，合并生成正式的完整 Excel 文档 markdown 资料
   - LLM 同时拿到：**结构化表格数据** + **分页OCR结果（含图片位置）**
   - LLM 的任务：基于结构化表格，把OCR出来的图片按位置插入正确位置，合并成完整文档
   - 这样既保证了表格数据的准确性，又能完整提取图片，解决图片归属问题
