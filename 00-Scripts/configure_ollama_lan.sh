#!/bin/bash
# 配置 Ollama 开放局域网 API 访问

set -e

echo "======================================"
echo "🔓 配置 Ollama 开放局域网访问"
echo "======================================"
echo ""

# 创建 systemd 覆盖配置
echo "📝 创建 systemd 配置..."
sudo mkdir -p /etc/systemd/system/ollama.service.d

cat > /tmp/ollama-override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_ORIGINS=*"
EOF

sudo cp /tmp/ollama-override.conf /etc/systemd/system/ollama.service.d/override.conf
echo "✅ systemd 配置已创建"

# 重新加载 systemd
echo "🔄 重新加载 systemd..."
sudo systemctl daemon-reload
echo "✅ systemd 已重新加载"

# 重启 Ollama
echo "🔄 重启 Ollama..."
sudo systemctl restart ollama
echo "✅ Ollama 已重启"

# 检查状态
echo ""
echo "📊 检查服务状态..."
systemctl status ollama --no-pager | head -10

# 检查监听端口
echo ""
echo "📊 检查监听端口..."
ss -tlnp | grep 11434 || netstat -tlnp | grep 11434 || echo "⚠️  端口未监听"

# 检查防火墙
echo ""
echo "🔒 检查防火墙..."
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "11434"; then
        echo "✅ 防火墙已开放 11434 端口"
    else
        echo "⚠️  防火墙未开放 11434 端口"
        echo "📝 运行以下命令开放端口:"
        echo "   sudo ufw allow 11434/tcp"
    fi
else
    echo "ℹ️  UFW 未安装，检查其他防火墙"
fi

echo ""
echo "======================================"
echo "✅ 配置完成！"
echo "======================================"
echo ""
echo "📊 访问信息:"
echo "   本地访问：http://localhost:11434"
echo "   局域网访问：http://$(hostname -I | awk '{print $1}'):11434"
echo ""
echo "🔒 安全提示:"
echo "   如果服务器在公网，请配置防火墙只允许信任的 IP 访问"
echo "   示例：sudo ufw allow from 192.168.1.0/24 to any port 11434"
echo ""
