#!/bin/bash
# generate_task2_review_plan.sh - 生成 Task 2 复习计划

echo "🤖 正在分析 Task 2 笔记并生成复习计划..."
echo ""

# 确保 SSH 隧道运行
if ! pgrep -f "ssh -L 5000:localhost:5000" > /dev/null; then
    echo "🔌 重建 SSH 隧道..."
    ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N
    sleep 2
fi

# 发送请求
echo "📝 分析笔记中..."
RESPONSE=$(curl -s -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请读取 /root/.openclaw/workspace/webdav-files/Obsidian Vault/Obsidian Vault/en learning/writing/Task2 笔记整理.md 的内容，然后：\n\n1. 总结 Task 2 的核心要点（3-5 个关键点）\n2. 生成今晚（2 小时）的复习计划，包括：\n   - 复习目标\n   - 时间分配（具体到分钟）\n   - 练习任务\n   - 自我检测方式\n\n请把复习计划保存到 /root/.openclaw/workspace/webdav-files/Obsidian Vault/Obsidian Vault/en learning/writing/2026-03-02-TASK2 复习计划.md\n\n用 Markdown 格式。",
    "session": "ielts-task2-review"
  }' \
  --max-time 120)

echo ""
echo "📊 处理结果:"
echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('response', 'No response'))" 2>/dev/null || echo "$RESPONSE"

echo ""
echo "✅ 完成！复习计划已保存到："
echo "   /var/webdav/Obsidian Vault/Obsidian Vault/en learning/writing/2026-03-02-TASK2 复习计划.md"
echo ""
echo "在本地可以打开查看～"
