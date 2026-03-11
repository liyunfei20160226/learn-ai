#!/bin/bash
# 安装脚本：将 code-analyzer 技能安装到 ~/.agents/skills/ 目录

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== code-analyzer 技能安装脚本 ===${NC}"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR"
TARGET_DIR="$HOME/.agents/skills/code-analyzer"

echo "源目录: $SOURCE_DIR"
echo "目标目录: $TARGET_DIR"

# 检查目标目录是否存在
if [ ! -d "$HOME/.agents/skills" ]; then
    echo -e "${YELLOW}创建目录: $HOME/.agents/skills${NC}"
    mkdir -p "$HOME/.agents/skills"
fi

# 备份现有技能目录
if [ -d "$TARGET_DIR" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="${TARGET_DIR}_backup_${TIMESTAMP}"
    echo -e "${YELLOW}备份现有技能目录到: $BACKUP_DIR${NC}"
    cp -r "$TARGET_DIR" "$BACKUP_DIR"
fi

# 创建目标目录
echo -e "${GREEN}创建/更新技能目录...${NC}"
mkdir -p "$TARGET_DIR"

# 复制文件
echo "复制技能文件..."
cp -v "$SOURCE_DIR/SKILL.md" "$TARGET_DIR/"
mkdir -p "$TARGET_DIR/scripts"
cp -v "$SOURCE_DIR/scripts/analyzer.py" "$TARGET_DIR/scripts/"
mkdir -p "$TARGET_DIR/evals"
cp -v "$SOURCE_DIR/evals/evals.json" "$TARGET_DIR/evals/"

# 设置执行权限
chmod +x "$TARGET_DIR/scripts/analyzer.py"

echo -e "${GREEN}✅ 技能安装完成！${NC}"
echo ""
echo "技能已安装到: $TARGET_DIR"
echo "使用方法:"
echo "  python \"$TARGET_DIR/scripts/analyzer.py\" [选项] [目录]"
echo ""
echo "常用选项:"
echo "  --output FILE    指定输出JSON文件"
echo "  --summary        只显示汇总信息"
echo "  --no-html        不生成HTML报告"
echo "  --lang {en,zh,ja} 指定HTML报告语言"
echo ""
echo "要卸载技能，只需删除目录: $TARGET_DIR"