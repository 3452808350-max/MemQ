#!/bin/bash
# Ollama 自动安装脚本
# 使用方法：bash /home/kyj/.openclaw/workspace/install_ollama.sh

set -e

echo "======================================"
echo "🚀 Ollama 自动安装脚本"
echo "======================================"
echo ""

# 步骤 1: 下载 Ollama
echo "📥 步骤 1: 下载 Ollama..."
curl -fsSL https://ollama.com/install.sh -o /tmp/ollama_install.sh
chmod +x /tmp/ollama_install.sh
echo "✅ Ollama 下载完成"
echo ""

# 步骤 2: 安装 Ollama
echo "🔧 步骤 2: 安装 Ollama..."
echo "   (需要输入 sudo 密码)"
sudo bash /tmp/ollama_install.sh
echo "✅ Ollama 安装完成"
echo ""

# 步骤 3: 拉取模型
echo "📦 步骤 3: 拉取向量化模型 (mxbai-embed-large)..."
echo "   (约 2GB，需要 2-5 分钟)"
ollama pull mxbai-embed-large
echo "✅ 模型下载完成"
echo ""

# 步骤 4: 启动服务
echo "🚀 步骤 4: 启动 Ollama 服务..."
ollama serve &
sleep 3
echo "✅ Ollama 服务已启动"
echo ""

# 步骤 5: 验证安装
echo "🧪 步骤 5: 验证安装..."
curl http://localhost:11434/api/tags
echo ""
echo "✅ 验证成功"
echo ""

# 步骤 6: 测试模型
echo "🎯 步骤 6: 测试模型..."
curl http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "mxbai-embed-large", "prompt": "你好世界"}'
echo ""
echo "✅ 测试成功"
echo ""

echo "======================================"
echo "🎉 Ollama 安装完成！"
echo "======================================"
echo ""
echo "下一步:"
echo "1. 配置 OpenClaw 使用本地 Ollama"
echo "2. 运行性能测试"
echo ""
echo "配置示例:"
echo "  config = EmbeddingConfig("
echo "    use_local=True,"
echo "    local_model='mxbai-embed-large',"
echo "    dimension=1024"
echo "  )"
echo ""
