#!/usr/bin/env bash
# 自动安装脚本
# 支持 OpenClaw 和 CodeWiz 环境

# CodeWiz 环境 (默认)
# `bash install.sh`

# OpenClaw 环境
# `bash install.sh --env=openclaw`

set -e

# 默认参数
TARGET_ENV="codewiz"
BACKUP_MODE=false

# 帮助信息
show_help() {
  cat <<EOF
用法: $0 [选项]

选项:
  --env=<openclaw|codewiz>   目标环境 (默认: codewiz)
  --backup                   启用覆盖保护，安装前确认
  --help                     显示此帮助信息

示例:
  $0                         # 安装到 CodeWiz (默认)
  $0 --env=openclaw          # 安装到 OpenClaw
  $0 --backup                # 启用覆盖保护
EOF
}

# 解析参数
for arg in "$@"; do
  case $arg in
    --env=*)
      TARGET_ENV="${arg#*=}"
      ;;
    --backup)
      BACKUP_MODE=true
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      echo "❌ 未知参数: $arg"
      show_help
      exit 1
      ;;
  esac
done

# 验证参数
if [ "$TARGET_ENV" != "openclaw" ] && [ "$TARGET_ENV" != "codewiz" ]; then
  echo "❌ 无效的环境: $TARGET_ENV (必须是 openclaw 或 codewiz)"
  exit 1
fi

# 确定目标路径
if [ "$TARGET_ENV" = "openclaw" ]; then
  SKILLS_TARGET="$HOME/.openclaw/workspace/skills"
  COMMANDS_TARGET="$HOME/.openclaw/workspace/commands"
else
  SKILLS_TARGET="$HOME/.codewiz/skills"
  COMMANDS_TARGET="$HOME/.codewiz/commands"
fi

# 创建目标目录
mkdir -p "$SKILLS_TARGET"
mkdir -p "$COMMANDS_TARGET"

echo "🚀 开始安装到 $TARGET_ENV 环境..."
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 覆盖保护：删除旧版本
if [ -d "$SCRIPT_DIR/skill" ]; then
  for skill_dir in "$SCRIPT_DIR/skill"/*; do
    if [ -d "$skill_dir" ]; then
      skill_name=$(basename "$skill_dir")
      if [ -d "$SKILLS_TARGET/$skill_name" ]; then
        if [ "$BACKUP_MODE" = true ]; then
          echo "⚠️  检测到已存在 Skill: $skill_name"
          read -p "   是否覆盖? (y/N): " -n 1 -r
          echo
          if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ 已取消安装"
            exit 1
          fi
        fi
        rm -rf "$SKILLS_TARGET/$skill_name"
        echo "🗑️  已删除旧版本: $skill_name"
      fi
    fi
  done
fi

if [ -d "$SCRIPT_DIR/commands" ]; then
  for cmd_file in "$SCRIPT_DIR/commands"/*.md; do
    if [ -f "$cmd_file" ]; then
      cmd_name=$(basename "$cmd_file")
      if [ -f "$COMMANDS_TARGET/$cmd_name" ]; then
        if [ "$BACKUP_MODE" = true ]; then
          echo "⚠️  检测到已存在 Command: $cmd_name"
          read -p "   是否覆盖? (y/N): " -n 1 -r
          echo
          if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ 已取消安装"
            exit 1
          fi
        fi
        rm -f "$COMMANDS_TARGET/$cmd_name"
        echo "🗑️  已删除旧版本: $cmd_name"
      fi
    fi
  done
fi

echo ""

# 安装 Skills
if [ -d "$SCRIPT_DIR/skill" ]; then
  echo "📦 安装 Skills..."
  cp -r "$SCRIPT_DIR/skill"/* "$SKILLS_TARGET/"
  
  for skill_dir in "$SCRIPT_DIR/skill"/*; do
    if [ -d "$skill_dir" ]; then
      skill_name=$(basename "$skill_dir")
      echo "  ✅ $skill_name"
    fi
  done
fi

# 安装 Commands
if [ -d "$SCRIPT_DIR/commands" ]; then
  if [ "$(ls -A $SCRIPT_DIR/commands 2>/dev/null)" ]; then
    echo "📋 安装 Commands..."
    cp -r "$SCRIPT_DIR/commands"/* "$COMMANDS_TARGET/"
    
    for cmd_file in "$SCRIPT_DIR/commands"/*.md; do
      if [ -f "$cmd_file" ]; then
        cmd_name=$(basename "$cmd_file" .md)
        echo "  ✅ /$cmd_name"
      fi
    done
  else
    echo "📋 无 Commands 需要安装（仅 Skill）"
  fi
fi

echo ""
echo "✅ 安装完成！"
echo ""

# 环境特定的后续步骤
if [ "$TARGET_ENV" = "openclaw" ]; then
  echo "🔄 下一步："
  echo "   重启 OpenClaw Agent: openclaw gateway restart"
else
  echo "💡 提示："
  echo "   CodeWiz 环境已安装，请重新加载配置"
fi
