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

