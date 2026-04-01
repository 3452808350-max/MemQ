#!/bin/bash
# 自动推送到 GitHub

set -e

echo "======================================"
echo "🚀 推送到 GitHub"
echo "======================================"
echo ""

REPO_URL="https://github.com/3452808350-max/openclaw-benrch.git"

echo "📋 仓库：$REPO_URL"
echo ""

# 提示输入认证信息
echo "🔑 GitHub 认证:"
echo "   方式 1: 输入用户名 + Token"
echo "   方式 2: 配置 SSH key"
echo ""
read -p "请输入 GitHub 用户名：" GITHUB_USER
read -sp "请输入 GitHub Token (或密码): " GITHUB_TOKEN
echo ""
echo ""

# 更新远程 URL
REMOTE_URL="https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/3452808350-max/openclaw-benrch.git"
git remote set-url origin "$REMOTE_URL"

echo ""
echo "🚀 开始推送..."
echo ""

# 推送
git push -u origin master --force

echo ""
echo "======================================"
echo "✅ 推送完成！"
echo "======================================"
echo ""
echo "📊 仓库地址:"
echo "   https://github.com/3452808350-max/openclaw-benrch"
echo ""
