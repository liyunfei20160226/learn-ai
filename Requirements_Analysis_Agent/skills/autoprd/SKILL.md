---
name: autoprd
description: "AutoPRD - 全自动PRD生成Agent。输入一句话需求，自动多轮自问自答完善需求，最终输出完整PRD和可用于Ralph的prd.json。支持 Claude Code、Amp、OpenAI API 三种方式。"
user-invocable: true
---

# AutoPRD - 全自动PRD生成Agent

从一句话需求开始，自动通过多轮自问自答完善需求分析，最终生成一份完整标准的产品需求文档。

---

## 工作流程

1. 接收用户一句话需求描述
2. 检测是否已有输出目录和PRD，如果有则断点续传
3. 否则生成初始PRD
4. 多轮迭代：分析缺失信息 → 提出问题 → AI自动回答 → 整合进PRD
5. 直到AI判定PRD完整或达到最大迭代次数
6. 转换为Ralph格式的prd.json
7. 输出最终结果

---

## 使用方式

```bash
uv sync
uv run python autoprd.py "一句话需求" [options]
```

## 特点

- ✅ 全自动，无需人工干预
- ✅ 支持多种AI后端：Claude Code、Amp、OpenAI API 直接调用
- ✅ 支持从 .env 文件自动加载 OpenAI 配置
- ✅ 支持断点续传，可增加迭代次数继续完善
- ✅ 输出符合Ralph标准的prd.json，可直接用于自动化开发
- ✅ 所有文档使用中文，便于中文用户阅读
- ✅ 遵循业界最佳PRD实践
