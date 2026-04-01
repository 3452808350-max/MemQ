#!/bin/bash
# test_kimi_remote.sh - 测试 Kimi Remote API 连接

set -e

API_TOKEN="kimi-remote-api-token-2026"
SERVER="root@106.53.186.90"
LOCAL_PORT=5000

echo "🦞 Kimi Remote API 测试工具"
echo "============================"
echo ""

# 步骤 1: 检查 SSH 密钥
echo "📝 步骤 1: 检查 SSH 配置..."
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "⚠️  未找到 SSH 私钥 ~/.ssh/id_rsa"
    echo ""
    echo "请先配置 SSH 密钥："
    echo "  1. 生成密钥：ssh-keygen -t rsa -b 4096"
    echo "  2. 复制到服务器：ssh-copy-id root@106.53.186.90"
    echo ""
    exit 1
fi

echo "✅ SSH 私钥存在：~/.ssh/id_rsa"

# 步骤 2: 测试 SSH 连接
echo ""
echo "📝 步骤 2: 测试 SSH 连接..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes $SERVER "echo OK" > /dev/null 2>&1; then
    echo "✅ SSH 连接成功"
else
    echo "❌ SSH 连接失败"
    echo ""
    echo "请复制 SSH 公钥到服务器："
    echo "  ssh-copy-id root@106.53.186.90"
    echo ""
    exit 1
fi

# 步骤 3: 建立 SSH 隧道
echo ""
echo "📝 步骤 3: 建立 SSH 隧道..."

# 检查是否已运行
if pgrep -f "ssh -L $LOCAL_PORT:localhost:5000 $SERVER" > /dev/null; then
    echo "✅ SSH 隧道已存在"
else
    ssh -L $LOCAL_PORT:localhost:5000 $SERVER -f -N
    echo "✅ SSH 隧道建立成功 (端口 $LOCAL_PORT)"
fi

# 步骤 4: 等待隧道就绪
echo ""
echo "📝 步骤 4: 等待隧道就绪..."
sleep 2

# 步骤 5: 健康检查
echo ""
echo "📝 步骤 5: 健康检查..."
HEALTH=$(curl -s http://localhost:$LOCAL_PORT/health 2>/dev/null)

if echo "$HEALTH" | grep -q "ok"; then
    echo "✅ Kimi API 健康检查通过"
    echo "   响应：$HEALTH"
else
    echo "❌ Kimi API 健康检查失败"
    echo "   响应：$HEALTH"
    echo ""
    echo "可能原因："
    echo "  1. 服务器上 API 服务未运行"
    echo "  2. 防火墙阻止"
    echo ""
    echo "请在服务器上检查："
    echo "  ssh $SERVER 'ps aux | grep kimi_remote_api'"
    echo ""
    exit 1
fi

# 步骤 6: 测试 Kimi 调用
echo ""
echo "📝 步骤 6: 测试 Kimi 调用..."
RESPONSE=$(curl -s -X POST http://localhost:$LOCAL_PORT/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "你好，请用一句话介绍你自己", "session": "test"}' \
  --max-time 30)

if echo "$RESPONSE" | grep -q "success"; then
    echo "✅ Kimi 调用成功"
    echo ""
    echo "📝 响应内容:"
    echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response', 'No response')[:200])" 2>/dev/null || echo "$RESPONSE"
else
    echo "❌ Kimi 调用失败"
    echo "   响应：$RESPONSE"
fi

# 步骤 7: 测试命令执行
echo ""
echo "📝 步骤 7: 测试命令执行（带 Token 认证）..."
CMD_RESPONSE=$(curl -s -X POST http://localhost:$LOCAL_PORT/execute \
  -H "Content-Type: application/json" \
  -d "{\"command\": \"uname -a\", \"auth_token\": \"$API_TOKEN\"}" \
  --max-time 10)

if echo "$CMD_RESPONSE" | grep -q "success"; then
    echo "✅ 命令执行成功"
    echo ""
    echo "📝 命令输出:"
    echo "$CMD_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('stdout', 'No output'))" 2>/dev/null || echo "$CMD_RESPONSE"
else
    echo "❌ 命令执行失败"
    echo "   响应：$CMD_RESPONSE"
fi

# 步骤 8: 显示使用示例
echo ""
echo "============================"
echo "✅ 所有测试完成！"
echo "============================"
echo ""
echo "📝 使用示例:"
echo ""
echo "1. 调用 Kimi:"
echo "   curl http://localhost:$LOCAL_PORT/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"prompt\": \"你好\"}'"
echo ""
echo "2. 执行命令:"
echo "   curl http://localhost:$LOCAL_PORT/execute \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"command\": \"ls -la\", \"auth_token\": \"$API_TOKEN\"}'"
echo ""
echo "3. Python 调用:"
echo "   import requests"
echo "   resp = requests.post('http://localhost:$LOCAL_PORT/chat', json={'prompt': '你好'})"
echo "   print(resp.json())"
echo ""

# 清理（可选）
# echo "🔌 关闭 SSH 隧道..."
# pkill -f "ssh -L $LOCAL_PORT:localhost:5000 $SERVER"
