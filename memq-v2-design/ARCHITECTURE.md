# MemQ v2 Architecture Design

## 概述

MemQ v2 是质量感知记忆检索系统的重构版本，解决 v1 的核心架构缺陷，引入并发处理、智能缓存和真正的分层检索。

## 核心模块划分

### 1. Storage Layer (存储层)

```
┌─────────────────────────────────────────┐
│         StorageManager                  │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ LanceDB     │  │ Metadata    │       │
│  │ VectorStore │  │ Index       │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ LayerIndex  │  │ Quality     │       │
│  │ (L0/L1/L2)  │  │ Index       │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
```

**职责**：
- LanceDB 向量存储（替换内存+JSON）
- 三层索引（L0_Abstract / L1_Overview / L2_Content）
- 质量分索引（支持按质量过滤检索）
- 元数据索引（category, scope, importance）

**改进点**：
- v1: 内存 Dict + JSON 文件，无索引
- v2: LanceDB 向量数据库，IVF-PQ 索引，O(log n) 检索

### 2. Retrieval Layer (检索层)

```
┌─────────────────────────────────────────┐
│         RetrievalPipeline               │
│                                         │
│  ┌───────────┐    ┌───────────┐         │
│  │ BM25      │───▶│ RRF       │         │
│  │ Searcher  │    │ Fusion    │         │
│  └───────────┘    └───────────┘         │
│       │                │                │
│       │                ▼                │
│  ┌───────────┐    ┌───────────┐         │
│  │ Vector    │───▶│ Batch     │         │
│  │ Searcher  │    │ Reranker  │         │
│  └───────────┘    └───────────┘         │
│                        │                │
│                        ▼                │
│                   ┌───────────┐         │
│                   │ Quality   │         │
│                   │ Weighting │         │
│                   └───────────┘         │
└─────────────────────────────────────────┘
```

**职责**：
- 并发混合检索（BM25 + Vector）
- 批处理 Rerank（替换逐个调用）
- RRF 融合（倒数秩融合）
- 质量分加权

**改进点**：
- v1: embedding/rerank 逐个请求，串行
- v2: 异步并发检索，批处理 rerank，Promise.all

### 3. Quality Layer (质量评分层)

```
┌─────────────────────────────────────────┐
│         QualityScorer                   │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Context     │  │ Adaptive    │       │
│  │ Aware       │  │ Weights     │       │
│  │ Detection   │  │ Adjuster    │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Feedback    │  │ Quality     │       │
│  │ Loop        │  │ Dimensions  │       │
│  │ Aggregator  │  │ Calculator  │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
```

**职责**：
- 上下文感知检测（避免误伤）
- 自适应权重调整（基于反馈）
- 反馈闭环（用户点击/采纳记录）
- 多维度质量计算

**改进点**：
- v1: 固定破坏词列表，固定权重，无反馈
- v2: 上下文感知检测，自适应权重，反馈闭环

### 4. Cache Layer (缓存层)

```
┌─────────────────────────────────────────┐
│         CacheManager                    │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Embedding   │  │ Query       │       │
│  │ Cache       │  │ Cache       │       │
│  │ (LRU+TTL)   │  │ (LRU+TTL)   │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Model       │  │ Eviction    │       │
│  │ Version     │  │ Policy      │       │
│  │ Tracker     │  │ (LRU+LFU)   │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
```

**职责**：
- Embedding 缓存（LRU + TTL）
- Query 缓存（完整检索结果）
- 模型版本感知（切换模型时清理缓存）
- 混合驱逐策略（LRU + LFU）

**改进点**：
- v1: 内存 Dict + JSON 文件，无驱逐，无版本感知
- v2: Redis 或内存 LRU 缓存，自动驱逐，模型版本追踪

### 5. Concurrency Layer (并发层)

```
┌─────────────────────────────────────────┐
│         ConcurrencyManager              │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Embedding   │  │ Rerank      │       │
│  │ Pool        │  │ Pool        │       │
│  │ (Promise)   │  │ (Promise)   │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Request     │  │ Rate        │       │
│  │ Queue       │  │ Limiter     │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
```

**职责**：
- Embedding 请求池（并发控制）
- Rerank 请求池（批处理）
- 请求队列（排队机制）
- 速率限制（避免 API 过载）

**改进点**：
- v1: 单进程，逐个请求
- v2: 并发池，批处理，速率限制

## 数据流图

### 完整检索流程

```
User Query
    │
    ▼
┌─────────────┐
│ QueryParser │  解析查询，提取意图
└─────────────┘
    │
    ▼
┌─────────────┐
│ CacheCheck  │  检查 Query Cache
└─────────────┘
    │ ┌───────┐ (命中)
    │ │Cache  │───────▶ Return Cached Result
    │ └───────┘
    │ (未命中)
    ▼
┌─────────────┐
│ LayerSelect │  根据查询复杂度选择层
└─────────────┘
    │
    ├───── L0 (简单查询) ──────▶ Fast Path
    ├───── L1 (中等查询) ──────▶ Standard Path
    └───── L2 (复杂查询) ──────▶ Deep Path
    │
    ▼ (L1 标准路径)
┌─────────────────────────────────────────┐
│       Parallel Retrieval                │
│  ┌───────────┐        ┌───────────┐     │
│  │ BM25      │        │ Vector    │     │
│  │ Search    │        │ Search    │     │
│  │ (Async)   │        │ (Async)   │     │
│  └───────────┘        └───────────┘     │
│       │                    │            │
│       └─────────┬──────────┘            │
│                 │                      │
│                 ▼                      │
│         ┌───────────┐                  │
│         │ RRF Fusion│                  │
│         └───────────┘                  │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│         Batch Rerank                    │
│  ┌───────────────────────────────┐      │
│  │ Prepare Batch Request (top20) │      │
│  └───────────────────────────────┘      │
│                 │                      │
│                 ▼                      │
│  ┌───────────────────────────────┐      │
│  │ Single API Call (Ollama)      │      │
│  └───────────────────────────────┘      │
│                 │                      │
│                 ▼                      │
│  ┌───────────────────────────────┐      │
│  │ Parse Scores (0-1)            │      │
│  └───────────────────────────────┘      │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│       Quality Weighting                 │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Load Quality│  │ Apply       │       │
│  │ Scores      │  │ Weights     │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  FinalScore = RerankScore × QualityScore│
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────┐
│ LayerLoad   │  加载对应层内容
└─────────────┘
    │
    ▼
┌─────────────┐
│ CacheStore  │  存入 Query Cache
└─────────────┘
    │
    ▼
Return Ranked Results
```

### 记忆存储流程

```
Raw Memory
    │
    ▼
┌─────────────┐
│ LayerSplit  │  分割为 L0/L1/L2
└─────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│       Quality Scoring                   │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Calculate   │  │ Adaptive    │       │
│  │ Dimensions  │  │ Weights     │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  QualityScore = Σ(Dimension × Weight)   │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────┐
│ Embedding   │  并发生成三层向量
│ Generation  │  (Promise.all)
└─────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│       LanceDB Storage                   │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Vector Index│  │ Metadata    │       │
│  │ Store       │  │ Store       │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Layer Index │  │ Quality     │       │
│  │ Update      │  │ Index       │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
    │
    ▼
Memory Stored
```

## 集成方案

### 与 OpenClaw 集成

```typescript
// OpenClaw 插件接口
interface MemQPlugin {
  name: 'memq-v2';
  
  // 初始化
  async init(ctx: OpenClawContext): Promise<void>;
  
  // 钩子
  hooks: {
    'memory:store': (event: MemoryStoreEvent) => Promise<void>;
    'memory:retrieve': (event: MemoryRetrieveEvent) => Promise<MemoryResult>;
    'memory:cleanup': (event: MemoryCleanupEvent) => Promise<void>;
    'agent:start': (event: AgentStartEvent) => Promise<void>;
    'agent:end': (event: AgentEndEvent) => Promise<void>;
  };
  
  // 配置
  config: MemQConfig;
}
```

### 与 Context Manager 集成

```typescript
// Context Manager 钩子
interface ContextManagerIntegration {
  // Token Budget 共享
  tokenBudget: TokenBudget;
  
  // Priority Layer 对齐
  priorityLayers: PriorityLayerConfig[];
  
  // 截断策略复用
  truncator: PriorityTruncator;
  
  // 质量分影响截断
  qualityAwareTruncation: boolean;
}

// 截断时考虑质量分
class QualityAwareTruncator extends PriorityTruncator {
  truncate(
    messages: MessageWithPriority[],
    targetTokens: number
  ): TruncationResult {
    // 先按优先级分层
    const layered = this.groupByLayer(messages);
    
    // 每层内按质量分排序
    for (const layer of layered.values()) {
      layer.sort((a, b) => b.qualityScore - a.qualityScore);
    }
    
    // 执行截断
    return super.truncate(messages, targetTokens);
  }
}
```

### 与 Claude Plugin 集成

```typescript
// Coordinator Mode Task Notification
interface TaskNotificationIntegration {
  // Worker 结果存储到 MemQ
  storeWorkerResult(result: TaskResult): Promise<void>;
  
  // Coordinator 查询历史结果
  querySimilarTasks(query: string): Promise<TaskNotification[]>;
  
  // 质量反馈
  recordTaskQuality(taskId: string, quality: number): Promise<void>;
}
```

## 技术选型

| 模块 | v1 实现 | v2 实现 | 原因 |
|------|---------|---------|------|
| Vector Store | 内存 Dict | LanceDB | 真正的向量索引，O(log n) |
| Cache | JSON 文件 | Redis / 内存 LRU | 驱逐策略，版本感知 |
| Rerank | 逐个调用 | 批处理 API | 性能提升 10-20x |
| Quality | 固定规则 | 自适应+反馈 | 减少误伤，提升准确率 |
| Concurrency | 单进程 | Promise Pool | 并发检索，降低延迟 |

## 性能目标

| 指标 | v1 性能 | v2 目标 | 改进 |
|------|---------|---------|------|
| 检索延迟 | 500-1000ms | <200ms | 5x |
| Recall@5 | 0.63 | 0.80+ | +27% |
| 噪声识别 | 80% | 95%+ | +19% |
| 缓存命中率 | 0% | 60%+ | 新增 |
| 并发能力 | 1 | 10+ | 新增 |

## 总结

MemQ v2 架构设计解决了 v1 的核心缺陷：

1. **并发处理** - 异步检索池，批处理 rerank
2. **智能缓存** - LRU 驱逐，模型版本感知
3. **真正分层** - L0/L1/L2 影响检索路径
4. **自适应质量** - 反馈闭环，上下文感知
5. **向量索引** - LanceDB 替换内存遍历

下一步：详见 QUALITY_SCORING.md、RETRIEVAL_PIPELINE.md、VALIDATION.md。