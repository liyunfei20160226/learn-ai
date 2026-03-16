# claud访问deepseek的配置
```powershell
# 打开配置文件
notepad $PROFILE

# 将下面环境变量写到配置文件中
# 1. 设置DeepSeek API密钥（替换成你自己的）
$env:ANTHROPIC_AUTH_TOKEN="你的-DeepSeek-API-密钥"
# 2. 核心步骤：设置DeepSeek专用的Base URL
#    这是DeepSeek官方提供的兼容Anthropic格式的端点[citation:5]
$env:ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
# 3. 设置默认模型为DeepSeek Chat
$env:ANTHROPIC_MODEL="deepseek-chat"
# 4. （可选）设置辅助模型（如果需要快速小模型）
$env:ANTHROPIC_SMALL_FAST_MODEL="deepseek-chat"
# 使用DeepSeek Reasoner模型
# $env:ANTHROPIC_MODEL="deepseek-reasoner"
# $env:ANTHROPIC_SMALL_FAST_MODEL="deepseek-reasoner"
# 5. （重要）防止超时：设置较长的超时时间（10分钟）
$env:API_TIMEOUT_MS="600000"
# 6. （可选）禁用非必要流量，提高稳定性
$env:CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"
```

# 使用ccenv-cli切换模型
```powershell
# 安装
npm install -g ccenv-cli
# 创建 DeepSeek 配置文件
ccx create deepseek --template deepseek --api-key 你的-DeepSeek-API-密钥
# 列出所有 profiles
ccx list
# 查看配置文件路径
ccx config-path
```

## config.json内容
```json
{
	"profiles": {
		"deepseek-chat": {
			"name": "deepseek-chat",
			"description": "Direct DeepSeek API access",
			"provider": "deepseek",
			"baseUrl": "https://api.deepseek.com/anthropic",
			"apiBase": "https://api.deepseek.com/anthropic",
			"model": "deepseek-chat",
			"apiKey": "sk-2512a0a1d57445b1b2128063e9f02188",
			"clearAnthropicKey": true,
			"createdAt": "2026-03-05T06:34:37.849Z",
			"updatedAt": "2026-03-05T06:34:37.855Z"
		},
		"deepseek-reasoner": {
			"name": "deepseek-reasoner",
			"description": "Direct DeepSeek API access",
			"provider": "deepseek",
			"baseUrl": "https://api.deepseek.com/anthropic",
			"model": "deepseek-reasoner",
			"apiKey": "sk-2512a0a1d57445b1b2128063e9f02188",
			"clearAnthropicKey": true,
			"createdAt": "2026-03-05T06:36:14.822Z",
			"updatedAt": "2026-03-05T06:36:32.385Z"
		},
		"local-codellama": {
			"name": "local-codellama:7b-code-q4_K_M",
			"description": "Local Ollama instance for offline AI",
			"provider": "ollama",
			"baseUrl": "http://localhost:11434",
			"model": "codellama:7b-code-q4_K_M",
			"clearAnthropicKey": true,
			"createdAt": "2026-03-05T06:37:56.961Z",
			"updatedAt": "2026-03-05T06:37:56.968Z"
		},
		"local-qwen15": {
			"name": "local-qwen15",
			"description": "Local Ollama instance for offline AI",
			"provider": "ollama",
			"baseUrl": "http://localhost:11434",
			"model": "qwen2.5-coder:1.5b",
			"clearAnthropicKey": true,
			"createdAt": "2026-03-05T06:41:29.444Z",
			"updatedAt": "2026-03-05T06:41:29.449Z"
		},
		"local-qwen3": {
			"name": "local-qwen3",
			"description": "Local Ollama instance for offline AI",
			"provider": "ollama",
			"baseUrl": "http://localhost:11434",
			"model": "qwen2.5-coder:3b",
			"clearAnthropicKey": true,
			"createdAt": "2026-03-05T06:42:30.666Z",
			"updatedAt": "2026-03-05T06:42:30.670Z"
		}
	},
	"activeProfile": "local-qwen15",
	"settings": {
		"encryptionEnabled": true,
		"defaultShell": "powershell"
	}
}
```
## 启动 Claude
```powershell
# 使用deepseek-chat模型
ccx run deepseek-chat
# 使用本地qwen2.5-coder:3b模型
ccx run local-qwen3
```

# 安装skills
```shell
# 添加插件市场：claude对话框中输入：
/plugin marketplace add anthropics/skills
# 安装技能包示例
/plugin install example-skills@anthropic-agent-skills
# 建议选择全局安装：Install for you (user scope)
```

# 启动claude并安装mcp服务
```shell
claude --mcp-config D:\dev\learn-ai\mcp-todo-server-py\mcp-config.json
```