#!/bin/bash
# OpenClaw 配置打包脚本
# 用法：./package_openclaw_config.sh

set -e

echo "🦞 OpenClaw 配置打包工具"
echo "========================"

# 配置
WORKSPACE="/home/kyj/.openclaw/workspace"
OUTPUT_DIR="/tmp/openclaw-config-package"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 清理旧目录
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

echo "📁 创建工作目录：$OUTPUT_DIR"

# 复制配置文件
echo "📋 复制配置文件..."

# 1. OpenClaw 主配置
cp /home/kyj/.openclaw/openclaw.json "$OUTPUT_DIR/02-openclaw.json"
echo "  ✅ openclaw.json"

# 2. 模型配置
cp /home/kyj/.openclaw/agents/main/agent/models.json "$OUTPUT_DIR/03-models.json"
echo "  ✅ models.json"

# 3. Workspace 文件
mkdir -p "$OUTPUT_DIR/04-workspace-files"
cp "$WORKSPACE/SOUL.md" "$OUTPUT_DIR/04-workspace-files/"
cp "$WORKSPACE/USER.md" "$OUTPUT_DIR/04-workspace-files/"
cp "$WORKSPACE/IDENTITY.md" "$OUTPUT_DIR/04-workspace-files/"
cp "$WORKSPACE/AGENTS.md" "$OUTPUT_DIR/04-workspace-files/"
cp "$WORKSPACE/MEMORY.md" "$OUTPUT_DIR/04-workspace-files/"
cp "$WORKSPACE/memory-projects.md" "$OUTPUT_DIR/04-workspace-files/"
cp "$WORKSPACE/memory-resources.md" "$OUTPUT_DIR/04-workspace-files/"
cp "$WORKSPACE/memory-preferences.md" "$OUTPUT_DIR/04-workspace-files/" 2>/dev/null || echo "  ⚠️  memory-preferences.md 不存在"
cp "$WORKSPACE/memory-lessons.md" "$OUTPUT_DIR/04-workspace-files/" 2>/dev/null || echo "  ⚠️  memory-lessons.md 不存在"
echo "  ✅ Workspace 文件"

# 4. DSS 模块
mkdir -p "$OUTPUT_DIR/05-dss-modules/dss_modules"
cp "$WORKSPACE/dss_v4.py" "$OUTPUT_DIR/05-dss-modules/"
cp "$WORKSPACE/dss_v2.py" "$OUTPUT_DIR/05-dss-modules/" 2>/dev/null || true
cp "$WORKSPACE/dss_v3.py" "$OUTPUT_DIR/05-dss-modules/" 2>/dev/null || true
cp "$WORKSPACE/dss_modules/"*.py "$OUTPUT_DIR/05-dss-modules/dss_modules/"
cp "$WORKSPACE/test_macro_analyzer.py" "$OUTPUT_DIR/05-dss-modules/"
echo "  ✅ DSS 模块"

# 5. 工具脚本
mkdir -p "$OUTPUT_DIR/06-tools"
cp "$WORKSPACE/tools/kimi_remote_api.py" "$OUTPUT_DIR/06-tools/" 2>/dev/null || echo "  ⚠️  kimi_remote_api.py 不存在"
echo "  ✅ 工具脚本"

# 6. 文档
mkdir -p "$OUTPUT_DIR/07-docs"
cp "$WORKSPACE/docs/"*.md "$OUTPUT_DIR/07-docs/" 2>/dev/null || true
cp "$WORKSPACE/OPENCLAW_REMOTE_SETUP.md" "$OUTPUT_DIR/01-SETUP.md"
echo "  ✅ 文档"

# 复制本指南
cp "$0" "$OUTPUT_DIR/package.sh"

echo ""
echo "📦 打包配置文件..."

# 创建压缩包
cd /tmp
tar -czf "openclaw-config-$TIMESTAMP.tar.gz" openclaw-config-package/

echo ""
echo "✅ 配置包创建完成！"
echo ""
echo "📄 输出文件：/tmp/openclaw-config-$TIMESTAMP.tar.gz"
echo "📊 文件大小：$(du -h /tmp/openclaw-config-$TIMESTAMP.tar.gz | cut -f1)"
echo ""
echo "🚀 上传到服务器："
echo "   scp /tmp/openclaw-config-$TIMESTAMP.tar.gz root@106.53.186.90:~/"
echo ""
echo "📖 配置指南：01-SETUP.md"
echo ""
