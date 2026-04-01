#!/bin/bash
# OpenClaw Context 压缩与清理脚本

set -e

echo "======================================"
echo "🗑️ OpenClaw Context 压缩与清理"
echo "======================================"
echo ""

# 1. 清理 Python 缓存
echo "📦 清理 Python 缓存..."
find /home/kyj/.openclaw/workspace -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find /home/kyj/.openclaw/workspace -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Python 缓存清理完成"
echo ""

# 2. 清理测试缓存
echo "📦 清理测试缓存..."
rm -rf /home/kyj/.openclaw/workspace/.pytest_cache 2>/dev/null || true
rm -rf /home/kyj/.openclaw/workspace/htmlcov 2>/dev/null || true
echo "✅ 测试缓存清理完成"
echo ""

# 3. 清理临时文件
echo "📦 清理临时文件..."
rm -f /tmp/ollama_install.sh 2>/dev/null || true
rm -f /tmp/*.tmp 2>/dev/null || true
echo "✅ 临时文件清理完成"
echo ""

# 4. 压缩日志文件
echo "📦 压缩日志文件..."
find /home/kyj/.openclaw/workspace -name "*.log" -size +10M -exec gzip {} \; 2>/dev/null || true
echo "✅ 日志文件压缩完成"
echo ""

# 5. 生成清理报告
echo "📊 生成清理报告..."
echo "======================================" > /tmp/cleanup_report.txt
echo "OpenClaw 清理报告" >> /tmp/cleanup_report.txt
echo "======================================" >> /tmp/cleanup_report.txt
echo "时间：$(date)" >> /tmp/cleanup_report.txt
echo "" >> /tmp/cleanup_report.txt
echo "清理项目:" >> /tmp/cleanup_report.txt
echo "- Python 缓存 ✅" >> /tmp/cleanup_report.txt
echo "- 测试缓存 ✅" >> /tmp/cleanup_report.txt
echo "- 临时文件 ✅" >> /tmp/cleanup_report.txt
echo "- 日志压缩 ✅" >> /tmp/cleanup_report.txt
echo "" >> /tmp/cleanup_report.txt
echo "✅ 清理完成！" >> /tmp/cleanup_report.txt

cat /tmp/cleanup_report.txt
echo ""
echo "✅ 清理完成！"
