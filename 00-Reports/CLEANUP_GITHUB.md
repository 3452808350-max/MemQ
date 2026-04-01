# 🔒 彻底清理 GitHub 仓库指南

**问题**: GitHub 仓库还包含大量敏感文件

**解决方案**: 删除仓库，重新创建干净版本

---

## ⚠️ 手动操作步骤

### 步骤 1: 删除 GitHub 仓库

1. 访问 https://github.com/3452808350-max/MemQ
2. 点击 **Settings** (设置)
3. 滚动到最底部 **Danger Zone** (危险区域)
4. 点击 **Delete this repository** (删除此仓库)
5. 输入仓库名确认删除

---

### 步骤 2: 本地清理

```bash
cd /home/kyj/.openclaw/workspace

# 清理 git 缓存
git rm -r --cached .
git add .

# 检查没有敏感文件
git status
```

---

### 步骤 3: 重新创建仓库

1. 在 GitHub 创建新仓库 `MemQ`
2. **不要** 初始化 README/.gitignore
3. 推送代码：

```bash
cd /home/kyj/.openclaw/workspace
git remote set-url origin https://github.com/3452808350-max/MemQ.git
git push -u origin main --force
```

---

## 📋 应该保留的文件

### 核心代码
- ✅ `memq/` - MemQ Pro 核心
- ✅ `plugins/memory-lancedb-pro/` - 插件代码
- ✅ `skills/memq/` - OpenClaw 技能

### 文档
- ✅ `README.md` - 项目说明
- ✅ `BRIDGE_README.md` - API 文档
- ✅ `FINAL_INTEGRATION_PLAN.md` - 集成方案
- ✅ `SECURITY_INCIDENT_REPORT.md` - 安全报告

### 测试
- ✅ `test_*.py` - 测试脚本

---

## ❌ 应该删除的文件

### 个人记忆
- ❌ `MEMORY.md`
- ❌ `memory/` 目录
- ❌ `*memory*.md` (个人记忆相关)
- ❌ `archive/memory/`

### 配置文件
- ❌ `*config*.json`
- ❌ `email_config.json`
- ❌ `openclaw.json`
- ❌ `pawsswd.md`
- ❌ `文档/`

### 临时文件
- ❌ `temp_*.json`
- ❌ `*.backup`
- ❌ `*.md.backup`

---

## 🔍 验证命令

```bash
# 检查敏感文件
git ls-files | grep -iE "(MEMORY\.md$|^memory/|config.*json|pawsswd)"

# 应该返回空结果
```

---

## 🙏 再次道歉

这次错误完全是我的责任。我会：
1. ✅ 协助你彻底清理 GitHub
2. ✅ 确保 .gitignore 正确配置
3. ✅ 以后推送前仔细检查

---

**创建时间**: 2026-03-16 11:50  
**状态**: ⚠️ 需要手动删除 GitHub 仓库
