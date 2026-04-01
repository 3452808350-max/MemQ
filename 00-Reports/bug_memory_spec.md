# 🐛 Bug 排查记忆规范

**创建时间**: 2026-03-13  
**目的**: 记录 Bug 现象和解决方案，方便未来快速排查  
**核心**: 现象特征优先，原因辅助

---

## 📋 Bug 记忆结构

### 标准格式

```json
{
  "text": "Bug 描述（现象 + 影响）",
  "category": "fact",
  "scope": "global",
  "importance": 0.9,
  "tags": [
    "Bug",
    "影响系统",
    "现象类型",
    "解决状态"
  ],
  "metadata": {
    "bug_id": "BUG-20260313-001",
    
    "🔍 现象特征": {
      "environment": "运行环境",
      "operation": "什么操作",
      "symptom": "什么症状",
      "error_message": "错误信息",
      "frequency": "出现频率",
      "reproducible": "是否可复现"
    },
    
    "📊 影响范围": {
      "affected_system": "影响系统",
      "affected_module": "影响模块",
      "severity": "严重程度",
      "user_impact": "用户影响"
    },
    
    "🔎 根因分析": {
      "root_cause": "根本原因",
      "cause_category": "原因分类"
    },
    
    "✅ 解决方案": {
      "solution": "解决方案",
      "workaround": "临时方案",
      "resolution_time": "解决时间"
    },
    
    "📚 参考信息": {
      "related_docs": ["相关文档"],
      "similar_bugs": ["相似 Bug ID"]
    }
  }
}
```

---

## 🏷️ 现象特征值体系（重点）

### 1. 环境特征（environment）

| 特征 | 说明 | 示例 |
|------|------|------|
| `操作系统` | Linux/Windows/macOS | `Ubuntu 22.04` |
| **运行环境** | 本地/服务器/容器 | `OpenClaw Gateway` |
| **软件版本** | 关键软件版本 | `OpenClaw 2026.3.8` |
| **依赖版本** | 关键依赖版本 | `node 24.13.1` |
| **配置状态** | 关键配置 | `memory-lancedb-pro enabled` |

---

### 2. 操作特征（operation）

| 特征 | 说明 | 示例 |
|------|------|------|
| **触发操作** | 什么操作触发 | `调用 memory_recall` |
| **输入参数** | 输入了什么 | `query="性格特点"` |
| **前置条件** | 需要什么条件 | `LanceDB 已初始化` |
| **操作频率** | 操作频率 | `每天多次` |

---

### 3. 症状特征（symptom）

| 特征 | 说明 | 示例 |
|------|------|------|
| **错误类型** | 什么错误 | `召回率低` |
| **错误代码** | 错误码 | `无` |
| **异常行为** | 什么异常 | `部分信息未检索到` |
| **性能问题** | 性能症状 | `无` |
| **数据问题** | 数据症状 | `数据缺失` |

---

### 4. 错误信息（error_message）

| 特征 | 说明 | 示例 |
|------|------|------|
| **错误标题** | 错误信息标题 | `无` |
| **关键错误** | 关键错误信息 | `召回率 80%` |
| **堆栈信息** | 关键堆栈 | `无` |
| **日志信息** | 相关日志 | `无` |

---

### 5. 频率特征（frequency）

| 特征 | 说明 | 示例 |
|------|------|------|
| **出现频率** | 多久出现 | `每次检索` |
| **时间规律** | 时间规律 | `无` |
| **触发条件** | 什么条件触发 | `查询特定关键词` |
| **是否必现** | 是否必现 | `是` |

---

### 6. 可复现性（reproducible）

| 特征 | 说明 | 示例 |
|------|------|------|
| **可复现** | 是否可复现 | `是` |
| **复现步骤** | 复现步骤 | `1.查询 2.检查召回` |
| **复现率** | 复现概率 | `100%` |

---

## 📊 影响范围特征

### 影响系统（affected_system）

| 系统 | 标签 |
|------|------|
| memory-lancedb-pro | `记忆系统` |
| DSS | `DSS 系统` |
| OpenClaw | `OpenClaw` |
| Kimi CLI | `Kimi 集成` |

---

### 影响模块（affected_module）

| 模块 | 说明 |
|------|------|
| `数据写入` | 数据写入模块 |
| `数据检索` | 数据检索模块 |
| `数据同步` | 数据同步模块 |
| `数据验证` | 数据验证模块 |

---

### 严重程度（severity）

| 级别 | 说明 | 响应时间 |
|------|------|---------|
| `P0-致命` | 系统不可用 | < 15 分钟 |
| `P1-严重` | 核心功能异常 | < 1 小时 |
| `P2-一般` | 部分功能异常 | < 24 小时 |
| `P3-轻微` | 轻微影响 | < 1 周 |

---

## 🔎 根因分类（辅助）

### 原因分类（cause_category）

| 分类 | 说明 |
|------|------|
| `数据缺失` | 数据未正确存储 |
| `配置错误` | 配置问题 |
| `代码 Bug` | 代码逻辑错误 |
| `依赖问题` | 外部依赖问题 |
| **环境问题** | 运行环境问题 |
| **操作问题** | 操作失误 |
| `性能问题` | 性能不足 |
| `设计缺陷` | 设计问题 |

---

## 🔍 Bug 检索策略

### 策略 1: 现象匹配（优先）

```python
# 用户报告 Bug
bug_report = {
    "environment": "OpenClaw Gateway",
    "operation": "调用 memory_recall",
    "symptom": "部分信息未检索到",
    "error_message": "召回率 80%"
}

# 检索历史 Bug
similar_bugs = search_bugs(
    environment=bug_report["environment"],
    symptom=bug_report["symptom"],
    error_message=bug_report["error_message"]
)

# 返回相似 Bug 和解决方案
```

---

### 策略 2: 原因匹配（辅助）

```python
# 新类型 Bug（无历史匹配）
# 使用根因分析辅助

root_cause = analyze_root_cause(bug_report)
similar_by_cause = search_bugs(
    cause_category=root_cause["category"]
)
```

---

## 📋 Bug 记忆示例

### 示例：本次召回率问题

```json
{
  "text": "memory-lancedb-pro 记忆召回率只有 80%，查询'性格特点'、'价值观'、'特长'时，部分关键信息（专注、独立、自由、平等、HiFi、电脑硬件）未被检索到。每次检索都出现，100% 可复现。",
  "category": "fact",
  "scope": "global",
  "importance": 0.9,
  "tags": ["Bug", "记忆系统", "召回率", "数据缺失"],
  "metadata": {
    "bug_id": "BUG-20260313-001",
    
    "🔍 现象特征": {
      "environment": "OpenClaw Gateway 2026.3.8, LanceDB",
      "operation": "调用 memory_recall 查询性格、价值观、特长",
      "symptom": "部分关键信息未被检索到，召回率 80%",
      "error_message": "召回率从 95% 降至 80%",
      "frequency": "每次检索都出现",
      "reproducible": "是，100% 可复现"
    },
    
    "📊 影响范围": {
      "affected_system": "memory-lancedb-pro",
      "affected_module": "数据检索",
      "severity": "P2-一般",
      "user_impact": "记忆检索不完整"
    },
    
    "🔎 根因分析": {
      "root_cause": "数据写入环节缺失：1.数据源不同步 2.手动存储缺失 3.自动捕获未工作",
      "cause_category": "数据缺失"
    },
    
    "✅ 解决方案": {
      "solution": "1.补充存储 7 条缺失记忆 2.创建同步脚本 3.创建验证脚本 4.配置定时任务",
      "workaround": "手动补充存储缺失信息",
      "resolution_time": "25 分钟"
    },
    
    "📚 参考信息": {
      "related_docs": ["memory_recall_root_cause_analysis.md"],
      "similar_bugs": []
    }
  }
}
```

---

## 🎯 Bug 排查流程

### Step 1: 记录现象

```
用户报告 → 提取现象特征 → 标准化记录
```

### Step 2: 检索历史

```
现象特征 → 搜索历史 Bug → 匹配相似度
```

### Step 3: 参考解决

```
相似 Bug → 查看解决方案 → 尝试应用
```

### Step 4: 更新记忆

```
解决后 → 更新 Bug 记忆 → 补充特征值
```

---

## 📊 现象特征检索示例

### 场景 1: 召回率问题

```python
# 用户报告
query = {
    "symptom": "召回率低",
    "system": "记忆系统"
}

# 检索
bugs = search_bugs(
    symptom="召回率",
    affected_system="记忆系统"
)

# 返回：BUG-20260313-001
```

---

### 场景 2: 数据缺失问题

```python
# 用户报告
query = {
    "symptom": "数据未检索到",
    "operation": "查询"
}

# 检索
bugs = search_bugs(
    symptom="未检索到",
    operation="查询"
)

# 返回：BUG-20260313-001
```

---

### 场景 3: 新问题（无历史匹配）

```python
# 无现象匹配
# 使用根因分析辅助

root_cause = "数据写入失败"
bugs = search_bugs(
    cause_category="数据缺失"
)

# 返回相似根因的 Bug
```

---

## 📋 检查清单

### Bug 记录时

- [ ] 记录环境特征（操作系统、版本、配置）
- [ ] 记录操作特征（什么操作、输入参数）
- [ ] 记录症状特征（什么错误、异常行为）
- [ ] 记录错误信息（错误码、日志）
- [ ] 记录频率特征（多久出现、是否必现）
- [ ] 记录可复现性（复现步骤、复现率）
- [ ] 评估影响范围（系统、模块、严重程度）
- [ ] 分析根因（根本原因、原因分类）
- [ ] 记录解决方案（解决方案、临时方案）
- [ ] 关联相关文档

### Bug 排查时

- [ ] 提取现象特征
- [ ] 检索历史 Bug
- [ ] 匹配相似度
- [ ] 参考解决方案
- [ ] 尝试应用
- [ ] 更新 Bug 记忆

---

*规范创建时间：2026-03-13*  
*下次审查：2026-04-13*
