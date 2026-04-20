#!/usr/bin/env python3
"""
启动 Architecture Design Agent Web UI
"""

import uvicorn
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

if __name__ == "__main__":
    print("=" * 60)
    print("   Architecture Design Agent Web UI")
    print("=" * 60)
    print("Starting server...")
    print("URL: http://localhost:8001")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    uvicorn.run("web.app:app", host="0.0.0.0", port=8001, reload=True)
