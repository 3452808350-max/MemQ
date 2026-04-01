#!/bin/bash
# ai_process.sh - 发送 AI 文件处理命令

INPUT_FILE=$1
OUTPUT_FILE=$2
INSTRUCTION=$3

if [ -z "$INPUT_FILE" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "用法：$0 <输入文件> <输出文件> [处理指令]"
    echo ""
    echo "示例:"
    echo "  $0 input.txt output.txt \"分析并总结\""
    echo "  $0 data.csv report.md \"生成统计报告\""
    exit 1
fi

# 默认指令
if [ -z "$INSTRUCTION" ]; then
    INSTRUCTION="分析并处理"
fi

echo "🤖 发送文件处理命令..."
echo "   输入文件：$INPUT_FILE"
echo "   输出文件：$OUTPUT_FILE"
echo "   处理指令：$INSTRUCTION"
echo ""

# 确保 SSH 隧道运行
if ! pgrep -f "ssh -L 5000:localhost:5000 root@106.53.186.90" > /dev/null; then
    echo "🔌 建立 SSH 隧道..."
    ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N
    sleep 2
fi

# 发送命令
RESPONSE=$(curl -s -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"请读取 /root/.openclaw/workspace/webdav-files/$INPUT_FILE，$INSTRUCTION，然后把结果保存到 /root/.openclaw/workspace/webdav-files/$OUTPUT_FILE。完成后回复处理结果。\",
    \"session\": \"file-processing\"
  }" \
  --max-time 300)

echo ""
echo "📝 AI 响应:"
echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response', 'No response'))" 2>/dev/null || echo "$RESPONSE"
echo ""
echo "✅ 处理完成！结果已保存到：$OUTPUT_FILE"
