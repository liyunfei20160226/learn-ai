#!/usr/bin/env python3
"""
Web Server for Software Engineering Multi-Agent Pipeline
启动方式:
    uv run python examples/web_server.py

环境变量:
    WEB_HOST - 绑定地址 (默认: 127.0.0.1)
    WEB_PORT - 绑定端口 (默认: 8000)
    WEB_USERNAME - 可选基础认证用户名
    WEB_PASSWORD - 可选基础认证密码
    OPENAI_API_KEY - OpenAI API Key
    OPENAI_BASE_URL - 可选 OpenAI 兼容 endpoint
    OPENAI_MODEL - 模型名称
    MEMORY_MCP_BASE_URL - 可选知识图谱服务
"""
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("WEB_HOST", "127.0.0.1")
port = int(os.getenv("WEB_PORT", "8000"))

if __name__ == "__main__":
    from se_pipeline.web.app import app
    print(f"🚀 Starting SE Pipeline Web Server at http://{host}:{port}")
    print(f"📝 Open your browser to http://{host}:{port}")
    print()
    uvicorn.run(app, host=host, port=port)
