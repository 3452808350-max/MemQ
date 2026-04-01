#!/bin/bash
# MemQ 核心组件准备脚本

echo "🔧 准备 MemQ 核心组件..."

# 创建目录
cd /home/kyj/.openclaw/workspace
mkdir -p /tmp/MemQ-core/plugins/memory-lancedb-pro
mkdir -p /tmp/MemQ-core/skills/memq
mkdir -p /tmp/MemQ-core/memq/plugins

# 复制核心文件
echo "📦 复制核心组件..."
cp memq/plugins/memq_pro.py /tmp/MemQ-core/memq/plugins/ 2>/dev/null || echo "⚠️ 跳过 memq_pro.py"
cp memq/plugins/memq.py /tmp/MemQ-core/memq/plugins/ 2>/dev/null || echo "⚠️ 跳过 memq.py"

# 复制插件文件
find plugins -name "memq*.py" -o -name "openclaw_plugin.py" -o -name "memq_bridge.py" -o -name "BRIDGE*.md" 2>/dev/null | while read file; do
    cp "$file" /tmp/MemQ-core/plugins/memory-lancedb-pro/ 2>/dev/null
done

# 复制技能文件
cp skills/memq/*.py /tmp/MemQ-core/skills/memq/ 2>/dev/null || echo "⚠️ 跳过技能文件"
cp skills/memq/README.md /tmp/MemQ-core/skills/memq/ 2>/dev/null || echo "⚠️ 跳过技能 README"

# 复制文档
cp README.md /tmp/MemQ-core/ 2>/dev/null || echo "⚠️ 创建新 README"

# 创建 .gitignore
cat > /tmp/MemQ-core/.gitignore << 'EOF'
# 私人文件
MEMORY.md
memory/
*.md.backup
pawsswd.md
文档/

# 配置文件
*config*.json
*.conf
*.env

# 缓存
cache/
__pycache__/
*.pyc

# 日志
*.log

# 系统文件
.DS_Store
EOF

echo ""
echo "✅ 核心组件准备完成！"
echo ""
echo "📁 位置：/tmp/MemQ-core/"
echo ""
echo "📦 包含内容:"
ls -la /tmp/MemQ-core/
echo ""
echo "🚀 下一步:"
echo "1. cd /tmp/MemQ-core"
echo "2. git init"
echo "3. git add ."
echo "4. git commit -m '🔒 MemQ Core v1.0'"
echo "5. git remote add origin https://github.com/3452808350-max/MemQ.git"
echo "6. git push -u origin main --force"
