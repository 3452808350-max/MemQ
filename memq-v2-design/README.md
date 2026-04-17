# MemQ v2 Design

MemQ v2 是质量感知记忆检索系统的重构设计方案。

## 背景

MemQ v1 存在以下核心问题：

| 类别 | 问题 | 影响 |
|------|------|------|
| **架构** | 单进程、无并发、缓存幼稚 | 性能极差（21s延迟） |
| **质量评分** | 破坏词粗糙、权重固定 | 误伤率高（20%） |
| **检索流程** | O(n)遍历、逐个rerank | 无法扩展 |
| **验证** | 合成数据、自证循环 | 无法验证真实效果 |

## 设计方案

### 1. 架构设计 (ARCHITECTURE.md)

**核心改进：**
- **并发处理** - asyncio 异步检索池
- **智能缓存** - LRU + TTL + 模型版本感知
- **真正分层** - L0/L1/L2 影响检索路径
- **向量索引** - LanceDB IVF_PQ，O(log n)

**性能目标：** 21s → <200ms (100x)

### 2. 质量评分 (QUALITY_SCORING.md)

**核心改进：**
- **上下文感知** - 破坏词位置分析，避免误伤
- **自适应权重** - 基于反馈动态调整
- **反馈闭环** - 用户采纳/忽略驱动改进
- **类型增强** - 多特征识别，不依赖关键词

**质量目标：** 误伤率 20% → <5%

### 3. 检索流程 (RETRIEVAL_PIPELINE.md)

**核心改进：**
- **LanceDB 索引** - IVF_PQ 向量索引
- **批处理 Rerank** - 单次 API 调用
- **异步并发** - Promise.all 并发检索
- **降级策略** - 多级降级，保证可用性

**延迟目标：** 21s → <200ms

### 4. 验证方案 (VALIDATION.md)

**核心改进：**
- **真实数据** - OpenClaw 用户数据，非合成
- **A/B 测试** - 对照组 vs 实验组，统计检验
- **人工标注** - 1000 样本，交叉验证
- **对比基准** - LanceDB/Chroma/v1，相对评估

**验证标准：** p < 0.05，Recall@5 ≥0.80

### 5. 实现路线 (ROADMAP.md)

**分阶段实施：**

| 阶段 | 时间 | 主要任务 |
|------|------|----------|
| Phase 1 | 2周 | 基础设施（LanceDB + 并发 + 缓存） |
| Phase 2 | 2周 | 核心功能（Rerank + 质量评分 + 反馈） |
| Phase 3 | 2周 | 验证优化（数据采集 + A/B 测试 + 标注） |
| Phase 4 | 1-2周 | 集成上线（OpenClaw + 灰度 + 全量） |

**总工作量：** 7-8 周，35-40 人天

## 文档索引

| 文档 | 内容 | 页数 |
|------|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 整体架构设计 | 10 |
| [QUALITY_SCORING.md](./QUALITY_SCORING.md) | 质量评分改进 | 20 |
| [RETRIEVAL_PIPELINE.md](./RETRIEVAL_PIPELINE.md) | 检索流程优化 | 28 |
| [VALIDATION.md](./VALIDATION.md) | 实验验证方案 | 15 |
| [ROADMAP.md](./ROADMAP.md) | 实现路线图 | 8 |

## 关键指标对比

| 指标 | v1 | v2 目标 | 改进 |
|------|-----|---------|------|
| **延迟** | 21s | <200ms | 100x |
| **Recall@5** | 0.63 | ≥0.80 | +27% |
| **误伤率** | 20% | <5% | -75% |
| **噪声识别** | 80% | ≥95% | +19% |
| **缓存命中** | 0% | ≥60% | 新增 |
| **并发能力** | 1 | 10+ | 新增 |

## 技术选型

| 模块 | v1 | v2 | 原因 |
|------|-----|-----|------|
| Vector Store | 内存 Dict | LanceDB | 真正的向量索引 |
| Cache | JSON 文件 | Redis/LRU | 驱逐策略，版本感知 |
| Rerank | 逐个调用 | 批处理 API | 性能提升 10-20x |
| Quality | 固定规则 | 自适应+反馈 | 减少误伤 |
| Concurrency | 单进程 | asyncio | 并发检索 |

## 集成方案

### OpenClaw 集成
```typescript
interface MemQPlugin {
  name: 'memq-v2';
  hooks: {
    'memory:store': (event) => Promise<void>;
    'memory:retrieve': (event) => Promise<MemoryResult>;
    'memory:cleanup': (event) => Promise<void>;
  };
}
```

### Context Manager 集成
- Token Budget 共享
- Priority Layer 对齐
- 质量分影响截断

### Claude Plugin 集成
- Task Notification 存储
- Worker 结果查询
- 质量反馈记录

## 下一步行动

1. **评审设计方案** - 团队评审 5 个设计文档
2. **确定优先级** - 根据资源调整 Phase 1 范围
3. **启动 Phase 1** - LanceDB 迁移和并发框架
4. **准备测试数据** - 开始真实数据采集

## 参考资源

- 原 MemQ 代码: `/home/kyj/.openclaw/workspace/MemQ-review/`
- Claude Plugin: `/home/kyj/文档/IELTS-Obsidian/Projects/claude-plugin/`
- Context Manager: `/home/kyj/.openclaw/workspace/context-manager-impl/`

---

**设计完成时间**: 2026-04-17
**设计状态**: 待评审
**预计启动**: Phase 1 (Week 1)