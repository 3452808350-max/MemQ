# MemQ v2 Implementation Roadmap

## 概述

MemQ v2 重构项目分为 4 个阶段，总工作量约 6-8 周。

## 阶段划分

```
Phase 1: 基础设施 (2周)
├── 1.1 LanceDB 迁移
├── 1.2 并发框架搭建
└── 1.3 缓存系统

Phase 2: 核心功能 (2周)
├── 2.1 批处理 Rerank
├── 2.2 质量评分改进
└── 2.3 反馈闭环

Phase 3: 验证优化 (2周)
├── 3.1 真实数据采集
├── 3.2 A/B 测试
└── 3.3 性能优化

Phase 4: 集成上线 (1-2周)
├── 4.1 OpenClaw 集成
├── 4.2 灰度发布
└── 4.3 全量上线
```

## Phase 1: 基础设施 (Week 1-2)

### 1.1 LanceDB 迁移

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计 MemorySchema | 0.5天 | - | schema.py |
| 实现 LanceDBVectorStore | 1.5天 | - | storage/lancedb_store.py |
| 数据迁移脚本 | 1天 | - | scripts/migrate_to_lancedb.py |
| 索引优化配置 | 0.5天 | - | config/ivf_pq.yaml |
| 单元测试 | 0.5天 | - | tests/test_lancedb_store.py |

**关键决策：**
- 索引类型：IVF_PQ（平衡速度和内存）
- 分区数：256（根据预期数据量 10K）
- 子向量数：64（1024维 / 64 = 16维子向量）

### 1.2 并发框架搭建

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计并发架构 | 0.5天 | - | docs/concurrency_design.md |
| 实现 EmbeddingPool | 1天 | - | retrieval/embedding_pool.py |
| 实现 AsyncRetrievalPipeline | 1.5天 | - | retrieval/async_pipeline.py |
| 错误处理框架 | 0.5天 | - | utils/error_handler.py |
| 单元测试 | 0.5天 | - | tests/test_async_pipeline.py |

**关键决策：**
- 并发模型：asyncio（Python 原生）
- 最大并发：10（Embedding API 限制）
- 超时策略：30s（Rerank），60s（Embedding）

### 1.3 缓存系统

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计缓存策略 | 0.5天 | - | docs/cache_design.md |
| 实现 EmbeddingCache | 0.5天 | - | cache/embedding_cache.py |
| 实现 QueryCache | 0.5天 | - | cache/query_cache.py |
| 实现 RerankCache | 0.5天 | - | cache/rerank_cache.py |
| 模型版本感知 | 0.5天 | - | cache/model_version_tracker.py |
| 单元测试 | 0.5天 | - | tests/test_cache.py |

**关键决策：**
- 缓存后端：Redis（生产）/ 内存 LRU（开发）
- Embedding TTL：7天
- Query TTL：1小时
- 驱逐策略：LRU + LFU 混合

**Phase 1 里程碑：**
- [ ] LanceDB 存储可用
- [ ] 异步检索框架可用
- [ ] 缓存系统可用
- [ ] 单元测试覆盖率 ≥80%

## Phase 2: 核心功能 (Week 3-4)

### 2.1 批处理 Rerank

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计批处理 API | 0.5天 | - | docs/batch_rerank_design.md |
| 实现 BatchReranker | 1天 | - | retrieval/batch_reranker.py |
| 支持 Ollama API | 0.5天 | - | retrieval/ollama_reranker.py |
| 降级策略 | 0.5天 | - | retrieval/degradation_handler.py |
| 性能基准测试 | 0.5天 | - | benchmarks/rerank_bench.py |

**关键决策：**
- 批处理大小：20（单次 API 调用）
- 超时：30秒
- 降级：API 失败时返回原始排序

### 2.2 质量评分改进

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 上下文感知检测 | 1天 | - | quality/context_aware_detector.py |
| 自适应权重调整 | 1.5天 | - | quality/adaptive_weight_adjuster.py |
| 场景自适应 | 0.5天 | - | quality/scenario_aware_weights.py |
| 类型识别改进 | 0.5天 | - | quality/enhanced_type_detector.py |
| 集成测试 | 0.5天 | - | tests/test_quality_scorer.py |

**关键决策：**
- 破坏词位置分析：开头 vs 全局
- 自适应调整率：0.1（每次调整幅度）
- 场景检测：基于查询关键词

### 2.3 反馈闭环

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计反馈机制 | 0.5天 | - | docs/feedback_design.md |
| 实现 FeedbackCollector | 0.5天 | - | feedback/collector.py |
| 实现 FeedbackAggregator | 0.5天 | - | feedback/aggregator.py |
| 实现 FeedbackDrivenUpdater | 0.5天 | - | feedback/updater.py |
| OpenClaw 集成 | 0.5天 | - | feedback/openclaw_integration.py |
| 集成测试 | 0.5天 | - | tests/test_feedback.py |

**关键决策：**
- 反馈类型：adopted / ignored / rejected / rated
- 聚合周期：1小时
- 权重更新：基于维度准确率

**Phase 2 里程碑：**
- [ ] 批处理 Rerank 可用（延迟 <100ms）
- [ ] 质量评分改进（误伤率 <5%）
- [ ] 反馈闭环可用
- [ ] 集成测试通过

## Phase 3: 验证优化 (Week 5-6)

### 3.1 真实数据采集

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计采集方案 | 0.5天 | - | docs/data_collection_plan.md |
| 实现 DataCollector | 1天 | - | validation/data_collector.py |
| 数据清洗 | 0.5天 | - | validation/data_cleaner.py |
| 匿名化处理 | 0.5天 | - | validation/anonymizer.py |
| 采集 1000+ 记忆 | 1天 | - | data/memories_*.jsonl |
| 采集 500+ 查询 | 1天 | - | data/queries_*.jsonl |

**关键决策：**
- 数据来源：OpenClaw 日志、Agent Session、Claude Plugin
- 匿名化：邮箱 → [EMAIL]，人名 → [USER]
- 最小样本：1000 记忆，500 查询

### 3.2 A/B 测试

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计 A/B 测试 | 0.5天 | - | docs/ab_test_design.md |
| 实现 ABTestFramework | 1天 | - | validation/ab_test.py |
| 用户分流 | 0.5天 | - | validation/user_splitter.py |
| 结果分析 | 0.5天 | - | validation/statistical_analysis.py |
| 运行 A/B 测试 | 1天 | - | results/ab_test_results.json |
| 生成报告 | 0.5天 | - | reports/ab_test_report.md |

**关键决策：**
- 分流比例：50/50
- 样本量：≥1000 查询
- 显著性水平：p < 0.05

### 3.3 人工标注

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计标注任务 | 0.5天 | - | docs/annotation_guide.md |
| 实现标注工具 | 1天 | - | validation/annotation_tool.py |
| 招募标注员 | 0.5天 | - | - |
| 标注 1000 样本 | 2天 | - | data/annotations.jsonl |
| 一致性验证 | 0.5天 | - | validation/consistency_check.py |
| 生成报告 | 0.5天 | - | reports/annotation_report.md |

**关键决策：**
- 标注员：3人（交叉验证）
- 样本数：1000
- 一致性阈值：≥70%

### 3.4 性能优化

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 性能分析 | 0.5天 | - | reports/performance_analysis.md |
| 索引优化 | 0.5天 | - | config/index_optimized.yaml |
| 缓存调优 | 0.5天 | - | config/cache_optimized.yaml |
| 并发调优 | 0.5天 | - | config/concurrency_optimized.yaml |
| 压力测试 | 0.5天 | - | benchmarks/stress_test.py |
| 生成报告 | 0.5天 | - | reports/performance_report.md |

**Phase 3 里程碑：**
- [ ] 1000+ 真实记忆采集完成
- [ ] A/B 测试完成（p < 0.05）
- [ ] 人工标注完成（一致性 ≥70%）
- [ ] 性能达标（延迟 <200ms）

## Phase 4: 集成上线 (Week 7-8)

### 4.1 OpenClaw 集成

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计插件接口 | 0.5天 | - | docs/openclaw_integration.md |
| 实现 MemQPlugin | 1天 | - | plugins/memq_v2.py |
| 钩子集成 | 0.5天 | - | hooks/memory_hooks.py |
| Context Manager 集成 | 0.5天 | - | integration/context_manager.py |
| Claude Plugin 集成 | 0.5天 | - | integration/claude_plugin.py |
| 集成测试 | 0.5天 | - | tests/test_openclaw_integration.py |

**关键决策：**
- 插件接口：OpenClaw 标准插件格式
- 钩子：memory:store, memory:retrieve, memory:cleanup
- 集成方式：依赖注入

### 4.2 灰度发布

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 设计灰度策略 | 0.5天 | - | docs/canary_plan.md |
| 实现 Feature Flag | 0.5天 | - | utils/feature_flags.py |
| 监控配置 | 0.5天 | - | config/monitoring.yaml |
| 5% 灰度 | 1天 | - | - |
| 20% 灰度 | 1天 | - | - |
| 50% 灰度 | 1天 | - | - |
| 问题修复 | 1天 | - | - |

**关键决策：**
- 灰度比例：5% → 20% → 50% → 100%
- 监控指标：延迟、错误率、用户反馈
- 回滚策略：Feature Flag 立即关闭

### 4.3 全量上线

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 上线检查清单 | 0.5天 | - | docs/launch_checklist.md |
| 全量发布 | 0.5天 | - | - |
| 监控观察 | 1天 | - | - |
| 问题响应 | 1天 | - | - |
| 上线报告 | 0.5天 | - | reports/launch_report.md |

**Phase 4 里程碑：**
- [ ] OpenClaw 插件集成完成
- [ ] 灰度发布完成（无重大问题）
- [ ] 全量上线完成
- [ ] 监控正常（延迟 <200ms，错误率 <1%）

## 工作量预估

| 阶段 | 周数 | 人天 | 主要任务 |
|------|------|------|----------|
| Phase 1 | 2 | 10 | 基础设施 |
| Phase 2 | 2 | 10 | 核心功能 |
| Phase 3 | 2 | 10 | 验证优化 |
| Phase 4 | 1-2 | 5-10 | 集成上线 |
| **总计** | **7-8** | **35-40** | - |

## 风险与应对

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|----------|
| LanceDB 性能不达预期 | 中 | 高 | 备选 Chroma，预留 2 天切换 |
| Ollama API 不稳定 | 高 | 中 | 降级策略，本地模型备选 |
| 真实数据采集困难 | 中 | 高 | 扩大数据源，延长采集周期 |
| 人工标注一致性低 | 中 | 中 | 增加标注员，细化标注指南 |
| 集成冲突 | 低 | 高 | 早期集成测试，预留缓冲时间 |

## 成功标准

| 维度 | 标准 | 验证方式 |
|------|------|----------|
| **功能** | 所有核心功能可用 | 单元测试 + 集成测试 |
| **性能** | 延迟 <200ms | 基准测试 |
| **质量** | 误伤率 <5%，噪声识别 ≥95% | 人工标注 |
| **效果** | Recall@5 ≥0.80，p < 0.05 | A/B 测试 |
| **稳定** | 错误率 <1%，可用性 ≥99% | 监控数据 |

## 关键里程碑

| 日期 | 里程碑 | 验收标准 |
|------|--------|----------|
| Week 2 | 基础设施完成 | LanceDB + 并发框架 + 缓存可用 |
| Week 4 | 核心功能完成 | Rerank + 质量评分 + 反馈闭环可用 |
| Week 6 | 验证完成 | A/B 测试通过，人工标注完成 |
| Week 8 | 上线完成 | 全量发布，监控正常 |

## 总结

MemQ v2 重构路线图的核心：

1. **分阶段实施** - 4 个阶段，风险可控
2. **数据驱动** - 真实数据验证，A/B 测试
3. **性能优先** - 100x 性能提升目标
4. **质量保障** - 人工标注，统计检验
5. **平滑上线** - 灰度发布，监控完备

---

**文档版本**: v1.0
**最后更新**: 2026-04-17
**状态**: 设计完成，待评审