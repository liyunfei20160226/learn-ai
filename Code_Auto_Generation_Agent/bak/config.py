"""配置管理模块

所有可配置项都集中在此文件中：
1. 基础开关配置（Config dataclass）- 可通过环境变量覆盖
2. 复杂结构配置（常量定义）- 集中管理，便于修改
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from dotenv import load_dotenv

# ============================================
# 命令包装器配置
# 自动检测项目类型，给命令加上正确的执行前缀
# ============================================
COMMAND_WRAPPERS: List[Dict] = [
    {
        "name": "uv",
        "detect_files": ["pyproject.toml", ".venv"],
        "commands": {"pytest", "ruff", "mypy", "uvicorn", "python", "python3", "pip"},
        "wrap_prefix": "uv run ",
    },
    {
        "name": "poetry",
        "detect_files": ["pyproject.toml", "poetry.lock"],
        "commands": {"pytest", "ruff", "mypy", "uvicorn", "python", "python3", "pip"},
        "wrap_prefix": "poetry run ",
    },
    {
        "name": "pnpm",
        "detect_files": ["package.json", "pnpm-lock.yaml", "node_modules"],
        "commands": {"eslint", "tsc", "jest", "vitest", "next"},
        "wrap_prefix": "pnpm exec ",
    },
    {
        "name": "npm",
        "detect_files": ["package.json", "package-lock.json", "node_modules"],
        "commands": {"eslint", "tsc", "jest", "vitest", "next"},
        "wrap_prefix": "npx ",
    },
]

# ============================================
# 框架映射配置
# ============================================
BACKEND_FRAMEWORK_MAPPING: Dict[str, str] = {
    "fastapi": "fastapi",
    "flask": "generic",
    "django": "generic",
    "spring": "spring-boot",
    "springboot": "spring-boot",
    "spring-boot": "spring-boot",
    "gin": "gin",
    "gin-gonic": "gin",
    "go-gin": "gin",
    "express": "generic",
    "nestjs": "generic",
    "nest": "generic",
}

FRONTEND_FRAMEWORK_MAPPING: Dict[str, str] = {
    "next": "nextjs",
    "nextjs": "nextjs",
    "next.js": "nextjs",
    "react": "generic",
    "vue": "generic",
    "vuejs": "generic",
    "angular": "generic",
    "svelte": "generic",
    "sveltekit": "generic",
    "nuxt": "generic",
    "nuxtjs": "generic",
}

# ============================================
# 脚手架命令配置（纯字典结构，方便配置修改）
# ============================================
BACKEND_SCAFFOLD_COMMANDS: Dict[str, Dict] = {
    "fastapi": {
        "commands": [
            "uv init --python 3.11 --no-readme --vcs none",
            "uv add fastapi uvicorn[standard] python-multipart",
            "uv add --dev ruff pytest mypy",
            "del main.py 2>nul || rm -f main.py 2>/dev/null || true",
        ],
        "description": "FastAPI + uv 扁平化目录初始化",
        "working_dir": "backend"
    },
    "spring-boot": {
        "commands": [],
        "description": "Spring Boot 使用 AI 直接生成",
        "working_dir": "backend"
    },
    "gin": {
        "commands": [
            "go mod init backend",
            "go get -u github.com/gin-gonic/gin",
        ],
        "description": "Go Modules + Gin 初始化",
        "working_dir": "backend"
    },
}

FRONTEND_SCAFFOLD_COMMANDS: Dict[str, Dict] = {
    "nextjs": {
        "commands": [
            "npx create-next-app@latest frontend --typescript --tailwind --eslint --app --no-src-dir --no-turbopack --import-alias '@/*' --use-npm --no-agents-md",
        ],
        "description": "Next.js 官方标准初始化（TypeScript + Tailwind + ESLint + App Router）",
        "working_dir": ""
    },
    "react": {
        "commands": [],
        "description": "React + Vite 使用 AI 直接生成",
        "working_dir": "frontend"
    },
    "vue": {
        "commands": [],
        "description": "Vue 使用 AI 直接生成",
        "working_dir": "frontend"
    },
}


@dataclass
class TimeoutConfig:
    """超时配置"""
    # 脚手架命令超时（uv init, create-next-app 等）
    scaffold_command: int = 300  # 5分钟
    # AI 命令执行超时
    ai_command: int = 3600  # 1小时
    # 通用命令超时
    general_command: int = 600  # 10分钟


@dataclass
class Config:
    """应用配置

    所有配置项都可以通过环境变量覆盖，变量名格式：大写 + 下划线
    例如：ai_backend → AI_BACKEND
    """
    # ============================================
    # AI后端配置
    # ============================================
    ai_backend: str = "claude"  # "claude" 或 "openai"

    # Claude CLI配置
    claude_cmd: str = "claude"

    # OpenAI API配置
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # ============================================
    # 重试配置
    # ============================================
    max_retries: int = 3
    max_fix_attempts: int = 3

    # ============================================
    # AI 输出配置
    # ============================================
    max_tokens: int = 32768

    # ============================================
    # Git配置
    # ============================================
    git_auto_commit: bool = True

    # ============================================
    # 功能开关
    # ============================================
    quality_check_enabled: bool = True
    # 是否使用 ReAct Agent 模式（工具调用模式，更稳定但稍慢）
    use_agent_mode: bool = False

    # ============================================
    # 输出配置
    # ============================================
    output_base_dir: str = "./output"

    # ============================================
    # 超时配置
    # ============================================
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)


def load_config() -> Config:
    """从环境变量加载配置"""
    load_dotenv()

    config = Config()

    # ============================================
    # AI工具
    # ============================================
    if os.getenv("DEFAULT_TOOL"):
        config.ai_backend = os.getenv("DEFAULT_TOOL").strip()

    # Claude CLI
    if os.getenv("CLAUDE_CMD"):
        config.claude_cmd = os.getenv("CLAUDE_CMD").strip()

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        config.openai_api_key = os.getenv("OPENAI_API_KEY").strip()
    if os.getenv("OPENAI_BASE_URL"):
        config.openai_base_url = os.getenv("OPENAI_BASE_URL").strip()
    if os.getenv("OPENAI_MODEL"):
        config.openai_model = os.getenv("OPENAI_MODEL").strip()

    # ============================================
    # 功能开关
    # ============================================
    if os.getenv("QUALITY_CHECK_ENABLED") is not None:
        config.quality_check_enabled = os.getenv("QUALITY_CHECK_ENABLED").lower() in ("true", "1", "yes")
    if os.getenv("USE_AGENT_MODE") is not None:
        config.use_agent_mode = os.getenv("USE_AGENT_MODE").lower() in ("true", "1", "yes")

    # ============================================
    # 重试配置
    # ============================================
    if os.getenv("MAX_RETRIES"):
        config.max_retries = int(os.getenv("MAX_RETRIES"))
    if os.getenv("MAX_FIX_ATTEMPTS"):
        config.max_fix_attempts = int(os.getenv("MAX_FIX_ATTEMPTS"))

    # ============================================
    # AI 输出配置
    # ============================================
    if os.getenv("MAX_TOKENS"):
        config.max_tokens = int(os.getenv("MAX_TOKENS"))

    # ============================================
    # Git
    # ============================================
    if os.getenv("GIT_AUTO_COMMIT") is not None:
        config.git_auto_commit = os.getenv("GIT_AUTO_COMMIT").lower() in ("true", "1", "yes")

    # ============================================
    # 输出
    # ============================================
    if os.getenv("OUTPUT_BASE_DIR"):
        config.output_base_dir = os.getenv("OUTPUT_BASE_DIR").strip()

    # ============================================
    # 超时配置
    # ============================================
    if os.getenv("SCAFFOLD_COMMAND_TIMEOUT"):
        config.timeout.scaffold_command = int(os.getenv("SCAFFOLD_COMMAND_TIMEOUT"))
    if os.getenv("AI_COMMAND_TIMEOUT"):
        config.timeout.ai_command = int(os.getenv("AI_COMMAND_TIMEOUT"))
    if os.getenv("GENERAL_COMMAND_TIMEOUT"):
        config.timeout.general_command = int(os.getenv("GENERAL_COMMAND_TIMEOUT"))

    return config


def get_config() -> Config:
    """获取配置单例"""
    return load_config()
