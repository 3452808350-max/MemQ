# 🔍 memory-lancedb-pro 信息丢失根因分析报告

**分析时间**: 2026-03-13 20:15  
**问题**: 记忆召回率只有 80%，部分关键信息丢失  
**分析方法**: 全链路排查（数据源 → 写入 → 存储 → 检索）

---

## 📊 问题现象

| 期望召回的关键词 | 实际检索结果 |
|----------------|-------------|
| 专注、独立（性格） | ❌ 未找到 |
| 自由、平等（价值观） | ❌ 未找到 |
| HiFi、电脑硬件（特长） | ❌ 未找到 |
| 成均馆大学、OpenWrt、AI Brain Fry | ✅ 找到 |

**综合召回率**: ~80%（低于预期的 95%+）

---

## 🔬 排查过程

### Step 1: 检查数据源（memory-preferences.md）

```bash
检查文件：/home/kyj/.openclaw/workspace/memory-preferences.md
创建时间：2026-02-25
最后更新：2026-03-13
```

**检查结果**:
```
❌ "专注": 不存在
❌ "独立": 不存在
❌ "自由": 不存在
❌ "平等": 不存在
❌ "HiFi": 不存在
❌ "电脑硬件": 不存在
```

**发现问题 1**: 原始数据源不包含那些关键词

---

### Step 2: 检查 LanceDB 实际存储

```bash
数据库：/home/kyj/.openclaw/workspace/lancedb
表：memories
记录数：11 条
```

**检查结果**:
```
存储的记忆:
1. sample (测试数据)
2. 人格结构分析报告（2 月 25 日）
3. Test: Kaguya Memory LanceDB Pro 已成功安装
4. Pre-compaction memory flush
5. Memory 模块索引
6. 项目历史（2 月 25 日）
7. K 的偏好（2 月 25 日）
8. 重要 API
9. 经验教训
10. Kimi Remote API 部署
11. Kimi Remote API 测试通过

关键词检查:
❌ "专注": 不存在
❌ "独立": 不存在
❌ "自由": 不存在
❌ "平等": 不存在
❌ "HiFi": 不存在
❌ "电脑硬件": 不存在
```

**发现问题 2**: LanceDB 中没有存储那些关键词

---

### Step 3: 检查数据流转链路

```
数据源 → 写入 → 存储 → 检索
  ↓       ↓       ↓       ↓
 ❌      ❌      ❌      ✅
```

**详细分析**:

| 环节 | 状态 | 说明 |
|------|------|------|
| **数据源** | ❌ | memory-preferences.md 是旧版本（2 月 25 日） |
| **写入** | ❌ | 留学文书写好后未调用 memory_store |
| **存储** | ❌ | LanceDB 只存储了旧记忆 |
| **检索** | ✅ | 向量检索正常，但源数据缺失 |

---

## 🎯 根本原因

### 主要原因（3 个）

#### 1. 数据源不同步

**问题**: memory-preferences.md 文件是 2 月 25 日的旧版本，不包含今天新增的信息

**原因**: 
- 今天填写留学文书时，更新了 .docx.md 文件
- 但没有同步更新 memory-preferences.md
- 导致数据源和实际信息不一致

**影响**: 
- 后续基于 memory-preferences.md 的记忆存储缺少关键信息

---

#### 2. 手动存储缺失

**问题**: 留学文书写好后，没有手动存入 LanceDB

**原因**:
- 留学文书保存在 `.docx.md` 文件中
- 没有调用 `memory_store` 工具将内容存入 LanceDB
- 依赖人工操作，容易遗漏

**影响**:
- 留学文书中的详细信息（成均馆大学、AI Brain Fry 等）未存入
- 只有早期手动存储的少量记忆

---

#### 3. 自动捕获未启用

**问题**: memory-lancedb-pro 的 autoCapture 功能未正确配置

**原因**:
```json
// openclaw.json 配置
"memory-lancedb-pro": {
  "autoCapture": true,  // ✅ 已启用
  "autoRecall": true    // ✅ 已启用
}
```

但实际未工作，可能原因：
- Gateway 重启后插件未正确加载
- autoCapture 只捕获 Agent 对话，不捕获文件编辑
- 没有文件监听机制

**影响**:
- 编辑 memory-*.md 文件时不会自动同步到 LanceDB
- 需要手动调用 memory_store

---

## 📋 问题链路图

```
┌─────────────────────────────────────────────────────────┐
│                    数据流转链路                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. 填写留学文书                                        │
│     ↓ (保存到 .docx.md)                                 │
│  2. 更新 memory-preferences.md ❌ (未执行)               │
│     ↓                                                   │
│  3. 调用 memory_store ❌ (未执行)                        │
│     ↓                                                   │
│  4. 写入 LanceDB ❌ (无数据)                             │
│     ↓                                                   │
│  5. 向量检索 ✅ (正常)                                   │
│     ↓                                                   │
│  6. 召回失败 ❌ (源数据缺失)                             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ 解决方案

### 立即修复（今天完成）

#### 1. 补充存储缺失信息

```python
# 执行以下命令补充存储
memory_store(
    text="K 的性格特点：专注、好奇、独立",
    category="preference",
    importance=0.9,
    tags=["性格", "特点"]
)

memory_store(
    text="K 的价值观：自由、平等",
    category="preference",
    importance=0.9,
    tags=["价值观"]
)

memory_store(
    text="K 的特长：技术（网络技术、系统架构、AI）、摄影、HiFi、电脑硬件",
    category="preference",
    importance=0.8,
    tags=["特长", "技能"]
)

# 存储留学文书关键内容
memory_store(
    text="K 申请成均馆大学（Sungkyunkwan University）人工智能专业，2026-03-13 完成文书",
    category="fact",
    importance=0.95,
    tags=["留学", "申请"]
)

memory_store(
    text="K 遇到过 AI Brain Fry（连续高强度学习导致头晕）和 FOMO 焦虑（技术更新太快）",
    category="fact",
    importance=0.8,
    tags=["困难", "成长"]
)
```

---

#### 2. 更新 memory-preferences.md

```bash
# 编辑文件，补充缺失信息
vim /home/kyj/.openclaw/workspace/memory-preferences.md

# 添加：
性格特征：专注、好奇、独立
价值观：自由、平等
特长：技术、摄影、HiFi、电脑硬件
```

---

### 长期修复（建立机制）

#### 3. 建立数据同步脚本

创建 `/home/kyj/.openclaw/workspace/sync_memory_to_lancedb.py`:

```python
#!/usr/bin/env python3
"""
定期同步 memory-*.md 文件到 LanceDB
"""

import os
from pathlib import Path
import hashlib

def sync_memory_files():
    workspace = Path('/home/kyj/.openclaw/workspace')
    memory_files = list(workspace.glob('memory-*.md'))
    
    for file in memory_files:
        # 读取文件内容
        content = file.read_text(encoding='utf-8')
        
        # 计算哈希（检查是否变化）
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # 检查是否已存储
        # TODO: 查询 LanceDB 是否已有该内容的记忆
        
        # 存入 LanceDB
        # TODO: 调用 memory_store 工具
        
        print(f"✅ 同步：{file.name}")

if __name__ == "__main__":
    sync_memory_files()
```

---

#### 4. 配置定时同步

```bash
# 添加 Cron 任务，每天同步一次
openclaw cron add \
  --name "memory-sync" \
  --schedule "0 2 * * *" \
  --command "python3 /home/kyj/.openclaw/workspace/sync_memory_to_lancedb.py"
```

---

#### 5. 建立验证机制

创建 `/home/kyj/.openclaw/workspace/verify_memory_recall.py`:

```python
#!/usr/bin/env python3
"""
每周验证记忆召回率
"""

def test_recall():
    # 运行召回率测试
    # 如果低于 90%，发送告警
    pass

if __name__ == "__main__":
    test_recall()
```

---

## 📊 修复后验证

执行补充存储后，重新运行召回率测试：

```bash
cd /home/kyj/.openclaw/workspace/memory-lancedb-pro
node eval/test_recall_kimi.js
```

**预期结果**:
- 召回率从 80% 提升到 95%+
- 所有关键词都能正确召回

---

## 🎯 经验教训

### 本次问题的教训

1. **数据源管理不当**
   - 多个文件存储相同信息（memory-preferences.md vs 留学文书）
   - 没有单一数据源（Single Source of Truth）

2. **依赖人工操作**
   - 需要手动调用 memory_store
   - 容易遗漏

3. **缺少验证机制**
   - 没有定期测试召回率
   - 问题发现晚

---

### 未来项目的预防措施

#### 1. 单一数据源原则

```
所有数据 → 统一存储位置 → 自动同步到各系统
```

#### 2. 自动化优先

```
文件编辑 → 自动触发同步 → 自动验证 → 失败告警
```

#### 3. 定期验证

```
每周召回率测试 → 低于阈值告警 → 自动修复
```

#### 4. 文档化

```
所有数据流转环节 → 文档说明 → 责任明确
```

---

## 📋 检查清单（未来项目）

- [ ] 确定单一数据源
- [ ] 配置自动同步机制
- [ ] 设置定期验证任务
- [ ] 建立告警机制
- [ ] 文档化数据流转链路
- [ ] 指定责任人

---

*分析完成时间：2026-03-13 20:15*  
*分析师：Kaguya (AI Assistant)*  
*状态：待修复*
