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

## 测试覆盖率

当前覆盖率：

| Module | Coverage |
|--------|----------|
| `requirements_analyst.py` | 100% |
| `requirements_verifier.py` | 100% |
| `requirements_final.py` | 100% |
| **Total** | **99%** |
