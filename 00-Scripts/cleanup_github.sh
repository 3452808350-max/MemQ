#!/bin/bash
# 清理 GitHub 仓库，删除与 OpenClaw 无关的文件

set -e

echo "======================================"
echo "🧹 清理 GitHub 仓库"
echo "======================================"
echo ""

# 删除无关目录和文件
echo "📋 删除以下无关内容:"
echo "   - EvoClaw-main/"
echo "   - dsd-player/"
echo "   - evolver.zip"
echo "   - skills/everything-claude-code/"
echo "   - skills/evomap"
echo "   - notes"
echo "   - openclaw-maintenance-skill"
echo "   - openclaw-min-bundle"
echo "   - tools/gitnexus"
echo "   - memory-lancedb-pro"
echo ""

# 执行删除
git rm -r --cached EvoClaw-main/
git rm -r --cached dsd-player/
git rm --cached evolver.zip
git rm -r --cached skills/everything-claude-code/
git rm -r --cached skills/evomap
git rm -r --cached notes
git rm -r --cached openclaw-maintenance-skill
git rm -r --cached openclaw-min-bundle
git rm -r --cached tools/gitnexus
git rm -r --cached memory-lancedb-pro

echo ""
echo "✅ 已从 Git 索引删除"
echo ""

# 提交更改
echo "📝 提交清理..."
git commit -m "chore: 清理与 OpenClaw 无关的文件

删除以下无关项目:
- EvoClaw-main (独立项目)
- dsd-player (Rust 项目，无关)
- evolver.zip (压缩文件)
- skills/everything-claude-code (独立技能)
- skills/evomap (独立技能)
- notes (个人笔记)
- openclaw-maintenance-skill (维护技能)
- openclaw-min-bundle (捆绑包)
- tools/gitnexus (Git 工具)
- memory-lancedb-pro (外部插件)"

echo ""
echo "✅ 提交完成"
echo ""

# 推送到 GitHub
echo "🚀 推送到 GitHub..."
git push origin master

echo ""
echo "======================================"
echo "✅ 清理完成！"
echo "======================================"
echo ""
echo "📊 仓库地址:"
echo "   https://github.com/3452808350-max/openclaw-benrch"
echo ""
