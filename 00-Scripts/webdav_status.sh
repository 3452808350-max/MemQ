#!/bin/bash
# webdav_status.sh - 检查 WebDAV 配置状态

echo "🦞 WebDAV + AI 文件处理系统状态检查"
echo "===================================="
echo ""

# 1. 检查 WebDAV 服务
echo "📡 检查 WebDAV 服务..."
if curl -s -X PROPFIND http://106.53.186.90/ --user admin:webdav-password-2026 | grep -q "multistatus"; then
    echo "✅ WebDAV 服务运行正常"
else
    echo "❌ WebDAV 服务异常"
fi
echo ""

# 2. 检查 SSH 隧道
echo "🔌 检查 SSH 隧道..."
if pgrep -f "ssh -L 5000:localhost:5000 root@106.53.186.90" > /dev/null; then
    echo "✅ SSH 隧道已建立 (端口 5000)"
else
    echo "⚠️  SSH 隧道未建立，运行：ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N"
fi
echo ""

# 3. 检查 Kimi API
echo "🤖 检查 Kimi Remote API..."
if curl -s http://localhost:5000/health | grep -q "ok"; then
    echo "✅ Kimi API 运行正常"
else
    echo "❌ Kimi API 无法访问"
fi
echo ""

# 4. 测试文件访问
echo "📁 测试 AI 文件访问..."
if ssh root@106.53.186.90 "test -f /root/.openclaw/workspace/webdav-files/test.txt && echo OK" 2>/dev/null | grep -q "OK"; then
    echo "✅ AI 可以访问 WebDAV 文件"
else
    echo "❌ AI 无法访问 WebDAV 文件"
fi
echo ""

echo "===================================="
echo "📝 使用示例:"
echo ""
echo "1. 保存文件到 WebDAV:"
echo "   curl -T input.txt http://106.53.186.90/input.txt --user admin:webdav-password-2026"
echo ""
echo "2. 发送处理命令:"
echo "   curl http://localhost:5000/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"prompt\": \"请读取 /root/.openclaw/workspace/webdav-files/input.txt 并处理\", \"session\": \"file-processing\"}'"
echo ""
echo "3. 读取结果:"
echo "   curl http://106.53.186.90/output.txt --user admin:webdav-password-2026"
echo ""
