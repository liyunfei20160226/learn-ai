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
   ```

2. 安装依赖
   ```bash
   uv install
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

## 测试覆盖率

当前覆盖率：

| Module | Coverage |
|--------|----------|
| `requirements_analyst.py` | 100% |
| `requirements_verifier.py` | 100% |
| `requirements_final.py` | 100% |
| `pipeline_graph.py` | **94%** |
| `auto_reviewer.py` | **100%** |
| `checklists.py` | 96% |
| `project_store.py` | **99%** |
| `memory_mcp_client.py` | **100%** |
| **Total** | **~98%** |
