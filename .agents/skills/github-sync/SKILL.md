---
name: github-sync
description: GitHub 仓库同步最佳实践。处理多仓库管理、分支清理、强制推送等场景。Use when: (1) 同步文件到 GitHub 仓库, (2) 清理混乱的分支结构, (3) 处理远程仓库冲突, (4) 重新组织仓库内容, (5) 避免误推送到错误仓库。
---

# GitHub 同步最佳实践

## 踩坑记录 (2026-04-01)

### ❌ 错误 1: 推送到错误仓库
**问题**: 默认 origin 指向 MemQ，但想推送到 notes 仓库
```bash
# 错误: 推送到 origin (MemQ)
git push origin master

# 正确: 明确指定远程
git push notes master
```

**教训**: 多仓库场景下，永远显式指定远程名称，不要依赖默认 origin。

### ❌ 错误 2: 分支混乱
**问题**: 本地和远程有多个分支 (main, master, feature/*)，互相冲突
```bash
# 查看所有分支
git branch -a

# 删除本地分支
git branch -d main feature/dss-transformer ...

# 删除远程分支
git push notes --delete main
```

**教训**: 保持单一分支策略，要么 main 要么 master，不要混用。

### ❌ 错误 3: 仓库内容混杂
**问题**: notes 仓库被混入 528 个无关文件 (DSS、MemQ、OpenClaw 项目文件)

**解决方案**:
```bash
# 彻底清理
git rm -rf .
git clean -fd

# 重建干净结构
mkdir -p {IELTS,Tech,Investment,AI,Reading,Projects,Life,Daily}
```

**教训**: 一个仓库一个用途，不要混用。知识库 ≠ 项目仓库。

## ✅ 正确流程

### 多仓库管理
```bash
# 查看当前远程
git remote -v

# 添加命名明确的远程
git remote add notes https://github.com/user/notes.git
git remote add memq https://github.com/user/MemQ.git
git remote add dss https://github.com/user/DSS.git

# 推送时显式指定
git push notes master
git push memq main
```

### 分支策略
```bash
# 统一使用 master
git checkout master
git branch -d main  # 删除本地 main
git push origin --delete main  # 删除远程 main

# 或统一使用 main
git checkout -b main
git branch -d master
git push origin main
git push origin --delete master
```

### 强制推送 (谨慎使用)
```bash
# 仅当确定要覆盖远程历史时
# 场景: 清理敏感文件、重新组织仓库
git push --force notes master

# 安全做法: 先备份
git bundle create backup.bundle --all
```

### 仓库重组
```bash
# 1. 备份当前内容
cp -r . /tmp/backup-repo

# 2. 清空仓库
git rm -rf .
git clean -fd

# 3. 创建新结构
mkdir -p {docs,src,assets}

# 4. 提交并推送
git add -A
git commit -m "chore: Reorganize repository structure"
git push --force origin master
```

## 检查清单

推送前确认:
- [ ] `git remote -v` 确认目标远程正确
- [ ] `git branch` 确认当前分支正确
- [ ] `git status` 确认要提交的文件
- [ ] 敏感文件已排除 (`.gitignore`)
- [ ] 如果是强制推送，已备份重要历史

## 快速修复

### 推送到错误远程
```bash
# 撤销 (如果刚推送)
git push origin --delete master  # 删除错误远程的分支

# 重新推送到正确远程
git push notes master
```

### 合并冲突
```bash
# 放弃本地更改，使用远程版本
git fetch notes
git reset --hard notes/master

# 或变基
git pull --rebase notes master
```

### 清理大文件历史
```bash
# 使用 git-filter-repo (需安装)
git filter-repo --strip-blobs-bigger-than 10M

# 或使用 BFG Repo-Cleaner
bfg --delete-files *.log
```
