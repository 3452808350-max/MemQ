#!/bin/bash
# Docker 安装脚本 for Ubuntu 24.04

set -e

echo "🚀 开始安装 Docker..."

# 1. 卸载旧版本（如果有）
echo "📦 卸载旧版本..."
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
    sudo apt-get remove -y $pkg 2>/dev/null || true
done

# 2. 安装依赖
echo "📥 安装依赖..."
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 3. 添加 GPG 密钥
echo "🔐 添加 GPG 密钥..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 4. 添加仓库
echo "📂 添加 Docker 仓库..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. 安装 Docker
echo "📦 安装 Docker..."
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. 启动 Docker
echo "▶️  启动 Docker 服务..."
sudo systemctl start docker
sudo systemctl enable docker

# 7. 添加用户到 docker 组（可选，需要重新登录）
echo "👤 添加当前用户到 docker 组..."
sudo usermod -aG docker $USER

# 8. 测试安装
echo "🧪 测试 Docker..."
if docker --version; then
    echo "✅ Docker 安装成功！"
    docker --version
    docker compose version
else
    echo "❌ Docker 安装失败"
    exit 1
fi

echo ""
echo "📝 使用说明:"
echo "  1. 重新登录或执行：newgrp docker"
echo "  2. 测试：docker run hello-world"
echo "  3. 拉取 Lightpanda: docker pull lightpanda/browser:nightly"
echo ""
