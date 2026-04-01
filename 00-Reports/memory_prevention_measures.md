# 🛡️ 记忆系统预防措施文档

**创建时间**: 2026-03-13  
**问题**: 记忆召回率只有 80%，部分关键信息丢失  
**目标**: 建立预防机制，确保召回率 ≥ 95%

---

## 📋 问题根因回顾

| 原因 | 说明 | 影响 |
|------|------|------|
| **数据源不同步** | memory-preferences.md 是旧版本 | 后续存储缺少关键信息 |
| **手动存储缺失** | 留学文书未调用 memory_store | 文书内容未进入记忆系统 |
| **自动捕获未工作** | autoCapture 只捕获对话 | 文件更新不会自动同步 |

---

## ✅ 已实施的修复

### 1. 补充存储缺失信息 ✅

**执行时间**: 2026-03-13 20:20  
**执行结果**: 7 条记忆成功导入 LanceDB

```
✅ K 的性格特点（专注、好奇、独立）
✅ K 的价值观（自由、平等）
✅ K 的特长（技术、摄影、HiFi、电脑硬件）
✅ 成均馆大学申请信息
✅ AI Brain Fry 和 FOMO 困难经历
✅ 学习计划
✅ 毕业后计划
```

**数据库状态**: 18 条记忆（原 11 条 + 新增 7 条）

---

### 2. 创建同步脚本 ✅

**文件**: `/home/kyj/.openclaw/workspace/sync_memory_to_lancedb.py`

**功能**:
- 自动扫描 `memory-*.md` 文件
- 提取记忆内容
- 导入到 LanceDB
- 记录同步状态（避免重复）

**使用方法**:
```bash
# 手动同步
python3 sync_memory_to_lancedb.py

# 强制同步（即使无变化）
python3 sync_memory_to_lancedb.py --force
```

---

### 3. 创建验证脚本 ✅

**文件**: `/home/kyj/.openclaw/workspace/verify_memory_recall.py`

**功能**:
- 每周运行召回率测试
- 使用 Kimi K2.5 评估检索结果
- 低于阈值时发送告警
- 保存历史记录

**使用方法**:
```bash
# 运行验证（默认阈值 90%）
python3 verify_memory_recall.py

# 自定义阈值
python3 verify_memory_recall.py --threshold 95
```

---

## 🔧 配置的定时任务

### Cron 任务 1: 每天同步

```bash
# 每天凌晨 2 点同步 memory-*.md 到 LanceDB
openclaw cron add \
  --name "memory-sync-daily" \
  --schedule "0 2 * * *" \
  --command "python3 /home/kyj/.openclaw/workspace/sync_memory_to_lancedb.py"
```

### Cron 任务 2: 每周验证

```bash
# 每周日 3 点验证召回率
openclaw cron add \
  --name "memory-verify-weekly" \
  --schedule "0 3 * * 0" \
  --command "python3 /home/kyj/.openclaw/workspace/verify_memory_recall.py --threshold 95"
```

---

## 📊 监控和告警

### 告警触发条件

| 条件 | 动作 |
|------|------|
| 召回率 < 90% | 🚨 紧急告警 |
| 召回率 90-95% | ⚠️ 警告 |
| 召回率 ≥ 95% | ✅ 正常 |

### 告警文件

**位置**: `/home/kyj/.openclaw/workspace/.memory_alert.json`

**格式**:
```json
{
  "timestamp": "2026-03-13T20:30:00",
  "type": "memory_recall_low",
  "recall_rate": 85,
  "threshold": 90,
  "message": "记忆召回率 85% 低于阈值 90%",
  "action_required": "请检查记忆存储和同步机制"
}
```

### 历史记录

**位置**: `/home/kyj/.openclaw/workspace/.memory_recall_history.json`

**保留**: 最近 100 次测试记录

---

## 🎯 长期预防措施

### 1. 单一数据源原则

**问题**: 多个文件存储相同信息（memory-preferences.md vs 留学文书）

**解决方案**:
```
所有个人数据 → ~/.openclaw/workspace/memory/YYYY-MM-DD.md
                              ↓
                    自动同步到 LanceDB
                              ↓
                    定期导出备份
```

**执行**:
- 每天的记忆写入 `memory/YYYY-MM-DD.md`
- 不再单独维护 `memory-preferences.md`
- 同步脚本自动处理

---

### 2. 自动化优先

**问题**: 依赖人工操作（手动调用 memory_store）

**解决方案**:

```python
# 文件编辑钩子（未来实现）
on_file_change('memory-*.md'):
    sync_to_lancedb()
    verify_recall()
    send_report()
```

**当前替代方案**:
- 每天定时同步（Cron 02:00）
- 每周定时验证（Cron 每周日 03:00）

---

### 3. 文档化数据流转

**文件**: `/home/kyj/.openclaw/workspace/docs/memory_data_flow.md`

**内容**:
```
数据流转链路:
1. 用户编辑 memory/YYYY-MM-DD.md
2. Cron 触发 sync_memory_to_lancedb.py（每天 02:00）
3. 脚本提取记忆内容
4. 调用 import_supplement.js 导入 LanceDB
5. Cron 触发 verify_memory_recall.py（每周日 03:00）
6. 验证召回率
7. 低于阈值 → 发送告警
8. 正常 → 保存历史记录
```

---

### 4. 责任人机制

| 任务 | 责任人 | 频率 |
|------|--------|------|
| 同步检查 | 自动（Cron） | 每天 |
| 召回率验证 | 自动（Cron） | 每周 |
| 告警处理 | K（人工） | 收到告警时 |
| 系统维护 | K（人工） | 每月 |

---

## 📋 检查清单

### 每日检查（自动）

- [x] 02:00 同步 memory-*.md 到 LanceDB
- [ ] 检查同步日志（无错误）

### 每周检查（自动）

- [ ] 周日 03:00 运行召回率测试
- [ ] 召回率 ≥ 95%
- [ ] 保存历史记录

### 每月检查（人工）

- [ ] 审查告警历史
- [ ] 清理过期记忆
- [ ] 更新同步脚本
- [ ] 测试恢复流程

---

## 🔍 故障恢复流程

### 场景 1: 召回率突然下降

```
1. 收到告警
2. 查看 .memory_alert.json
3. 运行 verify_memory_recall.py --threshold 95 --verbose
4. 检查最近同步记录
5. 如有缺失，手动补充存储
6. 重新验证
```

### 场景 2: 同步失败

```
1. 查看同步日志
2. 检查 LanceDB 连接
3. 手动运行 sync_memory_to_lancedb.py --force
4. 检查错误信息
5. 修复后重新运行
```

### 场景 3: 数据库损坏

```
1. 从备份恢复（每天自动备份）
2. 运行 verify_memory_recall.py
3. 验证召回率
4. 如仍有问题，从 memory-*.md 重新导入
```

---

## 📊 预期效果

| 指标 | 修复前 | 修复后（目标） |
|------|--------|---------------|
| **召回率** | 80% | ≥ 95% |
| **数据完整性** | ❌ 部分缺失 | ✅ 完整 |
| **同步延迟** | 不确定 | < 24 小时 |
| **问题发现** | 人工发现 | 自动告警 |
| **恢复时间** | 不确定 | < 1 小时 |

---

## 🎯 持续改进

### Phase 1: 基础预防（已完成 ✅）

- [x] 补充存储缺失信息
- [x] 创建同步脚本
- [x] 创建验证脚本
- [x] 配置定时任务

### Phase 2: 自动化增强（待实施）

- [ ] 文件编辑自动触发同步
- [ ] 实时召回率监控
- [ ] 自动修复机制

### Phase 3: 智能化（未来）

- [ ] AI 自动识别重要信息
- [ ] 智能记忆分类
- [ ] 自动优化检索策略

---

*文档创建时间：2026-03-13*  
*下次审查：2026-04-13*  
*责任人：K*
