---
name: ai-git-sync
description: AI Git文件同步工具
---

# AI Git Sync 工具规范

## 核心功能

1. **Git操作自动化**
   - `add(patterns)` - 添加文件
   - `commit(message)` - 提交
   - `push(remote, branch)` - 推送
   - `pull(remote, branch)` - 拉取

2. **SSH远程同步**
   - 支持SSH远程仓库
   - 自动配置SSH密钥

3. **定时同步**
   - 支持cron定时任务
   - 自动检测文件变化

## 使用方法

在Kimi CLI中运行：
```
/skill:ai-git-sync
```

然后描述你想要的功能。
