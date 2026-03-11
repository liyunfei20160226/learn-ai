# code-analyzer 技能开发指南

## 目录结构

```
my-claude-skill/code-analyzer/
├── SKILL.md                    # 技能描述文件
├── scripts/
│   └── analyzer.py            # 主脚本
├── evals/
│   └── evals.json             # 评估数据
├── install.sh                 # 安装脚本
└── DEVELOPMENT.md             # 本文档
```

## 开发流程

### 1. 修改源代码
所有代码修改应在 `my-claude-skill/code-analyzer/` 目录下进行。

```bash
cd D:\dev\learn-ai\my-claude-skill\code-analyzer
# 编辑 scripts/analyzer.py 或其他文件
```

### 2. 测试修改
在安装前，先测试修改是否正常工作：

```bash
# 直接运行源代码脚本进行测试
cd D:\dev\learn-ai
python my-claude-skill/code-analyzer/scripts/analyzer.py --no-html --output test.json
```

### 3. 安装到技能目录
使用安装脚本将修改同步到 Claude 技能目录：

```bash
cd D:\dev\learn-ai\my-claude-skill\code-analyzer
./install.sh
```

安装脚本会：
- 备份现有的技能目录
- 复制所有必要文件到 `~/.agents/skills/code-analyzer/`
- 设置执行权限

### 4. 验证安装
验证技能是否正确安装：

```bash
# 运行安装后的技能
python ~/.agents/skills/code-analyzer/scripts/analyzer.py --help
```

## Windows 编码问题修复

技能已包含 Windows 控制台编码修复代码：

```python
# Fix Windows console encoding issue
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')
```

这段代码确保在 Windows 上能正确显示 Unicode 字符（如中文和 Emoji）。

## 技能目录说明

- **源代码目录**: `D:\dev\learn-ai\my-claude-skill\code-analyzer`
  - 这是开发目录，所有修改应在这里进行
  - 使用版本控制管理此目录

- **技能安装目录**: `C:\Users\liyf\.agents\skills\code-analyzer`
  - 这是 Claude 技能实际加载的目录
  - 通过 `install.sh` 脚本从此目录同步

## 注意事项

1. **不要直接修改技能安装目录**，所有修改应在源代码目录中进行
2. **安装前备份**：安装脚本会自动备份现有技能目录
3. **测试后再安装**：确保修改在源代码目录中测试通过后再安装
4. **版本一致性**：保持源代码目录和技能安装目录的版本一致

## 故障排除

### 技能未显示在 Claude 中
如果使用 `Skill("code-analyzer")` 无法找到技能：
- 检查技能是否安装到正确目录：`~/.agents/skills/code-analyzer`
- Claude Code 可能从不同目录加载技能，请参考 Claude Code 文档

### Windows 编码错误
如果仍然出现 Unicode 编码错误：
- 确保脚本中包含 Windows 编码修复代码
- 检查 Python 版本和编码设置

### 安装脚本失败
如果安装脚本失败：
- 检查目标目录权限
- 手动复制文件：
  ```bash
  cp -r my-claude-skill/code-analyzer/* ~/.agents/skills/code-analyzer/
  ```