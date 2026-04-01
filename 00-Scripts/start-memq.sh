#!/bin/bash
# OpenClaw 启动前钩子
# 在 Gateway 启动前自动启动 MemQ 服务
# 
# 使用方法：
# 1. 在 openclaw gateway start 之前运行
# 2. 或者添加到 ~/.bashrc 或 ~/.profile

PLUGIN_DIR="/home/kyj/.openclaw/plugins/memory-lancedb-pro"
SCRIPT="$PLUGIN_DIR/memq-services.sh"

if [ -x "$SCRIPT" ]; then
    echo "🔧 启动 MemQ 服务..."
    bash "$SCRIPT" start
else
    echo "⚠️  未找到 MemQ 服务脚本：$SCRIPT"
fi
