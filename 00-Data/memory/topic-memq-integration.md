# 💾 记忆载入：MemQ 质量评分集成

**时间**: 2026-03-17 09:30 - 10:46  
**主题**: MemQ 质量评分系统集成到 OpenClaw

---

## 📋 项目背景

**目标**: 将 MemQ Pro 的分层检索 + 质量评分能力集成到 OpenClaw 的 `memory_recall` 工具中

**问题**:
- OpenClaw 插件是 TypeScript 运行时，MemQ Pro 是 Python
- LanceDB 有记忆数据，但 MemQ 数据库是空的
- 需要找到合适的集成方案

---

## 🔧 方案探索

### 方案 A：完全替换式集成 ❌
- 创建新插件 `memory-memq-pro`
- 需要移植质量评分逻辑到 TypeScript
- 数据迁移复杂

### 方案 B：Python Bridge HTTP 服务 ⚠️
- 已有 `memq_bridge.py` 和 `openclaw_plugin.py`
- 但 MemQ 数据库是空的，LanceDB 有数据
- 需要数据迁移脚本

### 方案 C：质量评分服务 + 现有检索 ✅
- 保持 LanceDB 存储和 TypeScript 检索
- Python 只提供质量评分 API
- 最小改动，最大兼容

---

## 🎯 最终实现

### 1. Python 质量评分服务

**文件**: `quality_scorer_service.py`  
**端口**: 5556  
**API**:
- `GET /health` - 健康检查
- `POST /score` - 单条评分
- `POST /batch_score` - 批量评分

**评分维度** (6 个):
| 维度 | 权重 | 说明 |
|------|------|------|
| type | 10% | 代码/教程 > 技术 > 普通 |
| length | 20% | 200-2000 字符最佳 |
| entity | 10% | URL/邮箱/代码/数字密度 |
| destructive | 30% | "抱歉"/"作为 AI"扣分 |
| template | 25% | "好的我来帮你"扣分 |
| metadata | 5% | 分类权重 |

### 2. TypeScript 客户端

**文件**: `quality-client.ts`
```typescript
qualityScore(text, category) → {score, dimensions}
batchQualityScore(items) → [results]
qualityServiceHealth() → boolean
```

### 3. Gateway 启动钩子

**文件**: `startup-hook.ts`
- 在 `gateway_start` 时自动检查/启动服务
- 使用 `spawn` 后台运行 Python 进程
- 服务与 Gateway 生命周期解耦

### 4. 记忆检索集成

**文件**: `index.ts` (plugins/memory-lancedb-pro)

在 `before_agent_start` 钩子中：
```typescript
// 1. LanceDB 检索 (取 top 5)
const results = await retriever.retrieve({...});

// 2. 调用质量评分
const scoredResults = await Promise.all(
  results.map(async (r) => {
    const q = await qualityScore(r.entry.text, r.entry.category);
    const finalScore = r.score * (0.5 + 0.5 * q.score);
    return {...r, qualityScore: q.score, score: finalScore};
  })
);

// 3. 过滤低质量 (阈值 0.4)
const filtered = scoredResults
  .filter(r => r.qualityScore >= 0.4)
  .slice(0, 3);

// 4. 注入上下文
return { prependContext: `<relevant-memories>...` };
```

---

## 📁 创建的文件

| 文件 | 说明 |
|------|------|
| `quality_scorer_service.py` | Python Flask 服务 |
| `quality-client.ts` | TS HTTP 客户端 |
| `startup-hook.ts` | Gateway 启动钩子 |
| `memq-services.sh` | 服务管理脚本 |
| `AUTOSTART.md` | 详细文档 |
| `MEMQ-SETUP-COMPLETE.md` | 快速参考 |
| `memq-status.md` | 状态报告 |

**修改的文件**:
- `index.ts` - 集成质量过滤
- `start_bridge.sh` - 更新启动脚本

---

## 🧪 测试结果

**高质量文本** (事实类):
```
"K 的密码文件位置：/home/kyj/文档/pawsswd.md"
→ 质量分：0.845 ✅
```

**低质量文本** (客套话):
```
"好的，我来帮你"
→ 质量分：0.51 ⚠️
```

**服务状态**:
- ✅ 端口 5556 运行中
- ✅ 健康检查通过
- ✅ Gateway 重启后自动恢复

---

## 💡 关键决策

1. **放弃 systemd** → 改用 Gateway 钩子
   - 原因：权限问题复杂，钩子更简单

2. **保持 LanceDB** → 不迁移数据
   - 原因：数据已在 LanceDB，迁移成本高

3. **HTTP 调用** → 不直接 import Python
   - 原因：避免进程管理复杂性

4. **质量阈值 0.4** → 可调整
   - 平衡召回率和准确率

---

## 🎯 下一步优化

1. **模板匹配增强** - 当前"好的我来帮你"没被完全匹配
2. **批量评分优化** - 减少 HTTP 调用次数
3. **质量分可视化** - 在检索结果中显示
4. **自动学习** - 根据用户反馈调整权重

---

**状态**: ✅ 完成并运行中  
**维护者**: Kaguya  
**下次检查**: Gateway 重启后验证自动启动