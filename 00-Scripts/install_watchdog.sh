#!/bin/bash
# OpenClaw Watchdog 安装脚本

set -e

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
WORKSPACE="$OPENCLAW_HOME/workspace"
WATCHDOG_SCRIPT="$WORKSPACE/openclaw_watchdog.py"
WATCHDOG_SERVICE="$WORKSPACE/openclaw-watchdog.service"
USER=$(whoami)

echo "🦮 OpenClaw Watchdog 安装程序"
echo "================================"
echo ""

# 1. 检查 Python
echo "✓ 检查 Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：需要 Python 3"
    exit 1
fi
python3 --version

# 2. 检查 Watchdog 脚本
echo ""
echo "✓ 检查 Watchdog 脚本..."
if [ ! -f "$WATCHDOG_SCRIPT" ]; then
    echo "❌ 错误：找不到 $WATCHDOG_SCRIPT"
    exit 1
fi
chmod +x "$WATCHDOG_SCRIPT"
echo "  脚本位置：$WATCHDOG_SCRIPT"

# 3. 检查服务文件
echo ""
echo "✓ 检查服务文件..."
if [ ! -f "$WATCHDOG_SERVICE" ]; then
    echo "❌ 错误：找不到 $WATCHDOG_SERVICE"
    exit 1
fi
echo "  服务文件：$WATCHDOG_SERVICE"

# 4. 安装 systemd 服务
echo ""
echo "✓ 安装 systemd 服务..."

# 创建用户 systemd 目录
mkdir -p "$HOME/.config/systemd/user"

# 复制并配置服务文件
USER_SERVICE="$HOME/.config/systemd/user/openclaw-watchdog.service"
cp "$WATCHDOG_SERVICE" "$USER_SERVICE"

# 启用 linger（用户服务在登出后继续运行）
if ! loginctl show-user "$USER" | grep -q "Linger=yes"; then
    echo "  启用用户 linger..."
    sudo loginctl enable-linger "$USER"
fi

# 重载 systemd
echo "  重载 systemd..."
systemctl --user daemon-reload

# 启用服务
echo "  启用服务..."
systemctl --user enable openclaw-watchdog.service

# 启动服务
echo "  启动服务..."
systemctl --user start openclaw-watchdog.service

# 5. 验证
echo ""
echo "✓ 验证服务状态..."
sleep 2
systemctl --user status openclaw-watchdog.service --no-pager || true

# 6. 创建日志目录
echo ""
echo "✓ 创建日志目录..."
LOG_DIR="$OPENCLAW_HOME/logs"
mkdir -p "$LOG_DIR"
touch "$LOG_DIR/watchdog.log"
echo "  日志文件：$LOG_DIR/watchdog.log"

# 7. 完成
echo ""
echo "================================"
echo "✅ 安装完成！"
echo ""
echo "常用命令："
echo "  查看状态：systemctl --user status openclaw-watchdog"
echo "  查看日志：journalctl --user -u openclaw-watchdog -f"
echo "  停止服务：systemctl --user stop openclaw-watchdog"
echo "  重启服务：systemctl --user restart openclaw-watchdog"
echo ""
echo "Watchdog 将会："
echo "  • 每 30 秒检查 Gateway 健康状态"
echo "  • 自动重启崩溃的 Gateway"
echo "  • 修复常见问题（僵尸进程、锁文件等）"
echo "  • 发送通知到 Telegram"
echo ""
