# 🚨 错误归因记忆规范

**创建时间**: 2026-03-13  
**目的**: 记录错误和根因，添加特征值方便未来检索和预防

---

## 📋 错误记忆结构

### 标准格式

```json
{
  "text": "错误描述（简洁明了）",
  "category": "fact",
  "scope": "global",
  "importance": 0.9,
  "tags": [
    "错误归因",
    "错误类型",
    "影响系统",
    "根因分类"
  ],
  "metadata": {
    "error_id": "ERR-20260313-001",
    "error_type": "数据丢失",
    "severity": "高/中/低",
    "affected_system": "memory-lancedb-pro",
    "root_cause_category": "数据写入/同步/验证",
    "occurred_at": "2026-03-13T20:00:00",
    "detected_at": "2026-03-13T20:10:00",
    "resolved_at": "2026-03-13T20:25:00",
    "resolution_time_minutes": 25,
    "impact": "召回率从 95% 降至 80%",
    "root_cause": "数据写入环节缺失（3 个原因）",
    "solution": "补充存储 + 自动同步 + 定期验证",
    "prevention": "同步脚本 + 验证脚本 + Cron 任务",
    "lessons": [
      "单一数据源原则",
      "自动化优先",
      "定期验证"
    ],
    "related_files": [
      "memory_recall_root_cause_analysis.md",
      "memory_prevention_measures.md"
    ],
    "similar_errors": [],
    "review_date": "2026-04-13"
  }
}
```

---

## 🏷️ 特征值标签体系

### 错误类型（error_type）

| 标签 | 说明 |
|------|------|
| `数据丢失` | 数据未正确存储或丢失 |
| `配置错误` | 配置文件错误导致问题 |
| `性能问题` | 系统性能下降 |
| `功能异常` | 功能无法正常工作 |
| `安全漏洞` | 安全问题 |
| `兼容性问题` | 版本/系统兼容性 |
| `依赖问题` | 外部依赖导致问题 |
| `人为错误` | 操作失误 |

---

### 严重程度（severity）

| 级别 | 说明 | 响应时间 |
|------|------|---------|
| `高` | 核心功能不可用 | < 1 小时 |
| `中` | 部分功能受影响 | < 24 小时 |
| `低` | 轻微影响 | < 1 周 |

---

### 根因分类（root_cause_category）

| 分类 | 说明 |
|------|------|
| `数据写入` | 数据未正确写入 |
| `数据同步` | 多系统数据不同步 |
| `数据验证` | 缺少验证机制 |
| `配置管理` | 配置错误或未同步 |
| `监控告警` | 缺少监控或告警 |
| `自动化` | 自动化不足 |
| `文档` | 文档缺失或过时 |
| `流程` | 流程不规范 |
| `沟通` | 沟通不畅 |
| `技术债务` | 历史遗留问题 |

---

### 影响系统（affected_system）

| 系统 | 标签 |
|------|------|
| memory-lancedb-pro | `记忆系统` |
| DSS | `DSS 系统` |
| OpenClaw | `OpenClaw` |
| Kimi CLI | `Kimi 集成` |
| Telegram Bot | `Telegram` |
| GitHub | `GitHub` |

---

## 📊 错误记忆检索

### 按错误类型检索

```python
# 查询所有"数据丢失"类错误
memory_recall(
    query="数据丢失",
    category="fact",
    tags=["错误归因", "数据丢失"]
)
```

### 按根因分类检索

```python
# 查询所有"数据同步"相关问题
memory_recall(
    query="数据同步",
    tags=["错误归因", "数据同步"]
)
```

### 按影响系统检索

```python
# 查询 memory-lancedb-pro 所有错误
memory_recall(
    query="memory-lancedb-pro",
    tags=["错误归因", "记忆系统"]
)
```

### 按时间范围检索

```python
# 查询最近 30 天的错误
# 使用 metadata 中的 occurred_at 字段过滤
```

---

## 🔍 相似错误匹配

当新错误发生时：

1. **提取特征值**
   - 错误类型
   - 影响系统
   - 根因分类

2. **检索相似错误**
   ```python
   similar = memory_recall(
       query=error_description,
       tags=["错误归因", error_type],
       limit=5
   )
   ```

3. **参考历史解决方案**
   - 查看类似错误的根因
   - 参考解决方案
   - 避免重复犯错

---

## 📋 错误归因流程

### Step 1: 记录错误

```python
error_memory = {
    "text": "错误描述",
    "category": "fact",
    "importance": 0.9,
    "tags": ["错误归因", "错误类型", "影响系统"],
    "metadata": {
        "error_id": f"ERR-{datetime.now().strftime('%Y%m%d')}-{seq:03d}",
        "error_type": "...",
        "severity": "...",
        "occurred_at": "...",
        ...
    }
}
```

### Step 2: 根因分析

- 使用 5 Why 分析法
- 找出根本原因
- 记录到 metadata.root_cause

### Step 3: 解决方案

- 立即修复措施
- 长期预防措施
- 记录到 metadata.solution 和 metadata.prevention

### Step 4: 经验教训

- 提炼 lessons learned
- 记录到 metadata.lessons
- 更新相关文档

### Step 5: 定期回顾

- 每月审查错误记录
- 分析错误趋势
- 更新预防措施

---

## 📊 错误统计面板

### 每月统计

```python
# 统计本月错误数量
errors_this_month = query_errors(
    start_date="2026-03-01",
    end_date="2026-03-31"
)

# 按类型统计
by_type = group_by(errors_this_month, "error_type")

# 按根因统计
by_root_cause = group_by(errors_this_month, "root_cause_category")

# 按严重程度统计
by_severity = group_by(errors_this_month, "severity")
```

### 趋势分析

- 错误数量趋势（上升/下降）
- 高频错误类型
- 高频根因分类
- 平均解决时间

---

## 🎯 错误记忆示例

### 示例：本次记忆召回率问题

```json
{
  "text": "memory-lancedb-pro 记忆召回率只有 80%，部分关键信息（专注、独立、自由、平等、HiFi、电脑硬件）未被检索到。根因：数据写入环节缺失（数据源不同步、手动存储缺失、自动捕获未工作）。解决方案：补充存储 7 条记忆、创建同步脚本、创建验证脚本、配置定时任务。",
  "category": "fact",
  "scope": "global",
  "importance": 0.95,
  "tags": ["错误归因", "数据丢失", "记忆系统", "数据写入"],
  "metadata": {
    "error_id": "ERR-20260313-001",
    "error_type": "数据丢失",
    "severity": "中",
    "affected_system": "memory-lancedb-pro",
    "root_cause_category": "数据写入",
    "occurred_at": "2026-03-13T20:00:00",
    "detected_at": "2026-03-13T20:10:00",
    "resolved_at": "2026-03-13T20:25:00",
    "resolution_time_minutes": 25,
    "impact": "召回率从 95% 降至 80%",
    "root_cause": "数据写入环节缺失（3 个原因）：1.数据源不同步 2.手动存储缺失 3.自动捕获未工作",
    "solution": "补充存储 7 条记忆、创建同步脚本、创建验证脚本、配置定时任务",
    "prevention": "每天自动同步、每周自动验证、低于阈值自动告警",
    "lessons": [
      "单一数据源原则",
      "自动化优先",
      "定期验证",
      "犯错不可怕，就怕没记性"
    ],
    "related_files": [
      "memory_recall_root_cause_analysis.md",
      "memory_prevention_measures.md",
      "memory_fix_summary.md"
    ],
    "similar_errors": [],
    "review_date": "2026-04-13"
  }
}
```

---

## 📋 实施清单

- [x] 设计错误记忆结构
- [x] 定义特征值标签体系
- [x] 创建错误归因流程
- [ ] 将本次错误存入记忆系统
- [ ] 创建错误检索工具
- [ ] 配置每月错误统计
- [ ] 建立错误回顾机制

---

*规范创建时间：2026-03-13*  
*下次审查：2026-04-13*
