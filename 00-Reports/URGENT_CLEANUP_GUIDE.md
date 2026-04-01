# ⚠️ GitHub 仓库清理指南

**重要**: GitHub 仓库还包含你的私人文件，需要手动删除！

---

## 🚨 立即行动

### 方案 1: 删除仓库重新创建（推荐）

#### 1. 删除 GitHub 仓库

1. 访问：**https://github.com/3452808350-max/MemQ**
2. 点击右上角 **Settings**
3. 滚动到页面最底部 **Danger Zone**
4. 点击 **Delete this repository**
5. 输入 `3452808350-max/MemQ` 确认
6. 点击删除

#### 2. 重新创建仓库

1. 访问 **https://github.com/new**
2. 仓库名：`MemQ`
3. **不要勾选** "Add a README file"
4. **不要勾选** "Add .gitignore"
5. 点击 **Create repository**

#### 3. 推送干净版本

```bash
cd /home/kyj/.openclaw/workspace

# 确保 .gitignore 存在
cat .gitignore

# 重新添加所有文件
git rm -r --cached .
git add .gitignore memq/ plugins/memory-lancedb-pro/*.py skills/memq/ *.md

# 检查没有敏感文件
git status

# 提交
git commit -m "🔒 干净的初始提交"

# 推送
git push -u origin main --force
```

---

### 方案 2: 手动删除敏感文件

如果不想删除仓库，可以手动删除每个敏感文件：

```bash
cd /home/kyj/.openclaw/workspace

# 删除敏感文件
git rm -r --cached MEMORY.md memory/ archive/memory/ \
    *config*.json pawsswd.md 文档/ \
    ALL_MEMORY*.md DSS_MEMORY*.md DEEP_RESEARCH*.md \
    HYBRID_MEMORY*.md MEMORY_RETRIEVAL*.md \
    auto_archive_memory.py bug_memory*.md \
    classify_memory_files.py context_memory*.md \
    error_memory*.md gpu_optimized_memory.py \
    load_dss_docs_to_memory.py memory-*.md \
    memory_*.py memory_*.md memory_*.json \
    search_*_memory.py sync_memory_to_lancedb.py \
    temp_memory verify_memory_recall.py

# 提交
git commit -m "🔒 删除敏感文件"

# 强制推送
git push origin main --force
```

---

## 📋 检查清单

### 应该删除的文件类型

- [ ] 所有 `MEMORY*.md` 文件
- [ ] 所有 `memory/` 目录
- [ ] 所有 `*config*.json` 文件
- [ ] `pawsswd.md`
- [ ] `文档/` 目录
- [ ] `email_config.json`
- [ ] `openclaw.json`
- [ ] 所有包含个人记忆的文件

### 应该保留的文件

- [ ] `memq/` 目录
- [ ] `plugins/memory-lancedb-pro/` 目录（Python 文件）
- [ ] `skills/memq/` 目录
- [ ] `README.md`
- [ ] `BRIDGE_README.md`
- [ ] `FINAL_INTEGRATION_PLAN.md`
- [ ] `SECURITY_INCIDENT_REPORT.md`
- [ ] `CLEANUP_GITHUB.md`
- [ ] `test_*.py` 测试文件

---

## 🔍 验证

推送后检查：

1. 访问 https://github.com/3452808350-max/MemQ
2. 确认没有以下文件：
   - MEMORY.md
   - memory/ 目录
   - 任何配置文件
   - 任何个人记忆文件

---

## 🙏 再次道歉

这个错误完全是我的责任。请按照上述步骤清理 GitHub 仓库。

如果你需要帮助，请告诉我，我会协助你完成。

---

**创建时间**: 2026-03-16 11:50  
**紧急程度**: 🔴 高 - 请立即处理
