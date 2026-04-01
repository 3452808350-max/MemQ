#!/bin/bash
# OpenClaw WebSocket Proxy 部署脚本
# 在 106.53.186.90 上运行

set -e

echo "=== OpenClaw WebSocket Proxy 部署 ==="

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "安装 Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "Node.js 版本: $(node --version)"

# 创建应用目录
APP_DIR="/opt/openclaw-ws-proxy"
sudo mkdir -p $APP_DIR
cd $APP_DIR

# 复制文件（假设已通过 scp 上传）
echo "安装依赖..."
npm install

# 创建 systemd 服务
sudo tee /etc/systemd/system/openclaw-ws-proxy.service > /dev/null <<EOF
[Unit]
Description=OpenClaw WebSocket Proxy
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/node ws-proxy.js
Restart=always
RestartSec=5
Environment="PROXY_PORT=8080"
Environment="UPSTREAM_URL=ws://127.0.0.1:18789/ws"
Environment="LOG_LEVEL=info"

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable openclaw-ws-proxy
sudo systemctl restart openclaw-ws-proxy

echo ""
echo "=== 部署完成 ==="
echo "WebSocket 地址: ws://106.53.186.90:8080"
echo "健康检查: http://106.53.186.90:8081/health"
echo ""
echo "查看日志: sudo journalctl -u openclaw-ws-proxy -f"
echo ""

# 显示状态
sleep 2
sudo systemctl status openclaw-ws-proxy --no-pager || true
