# OpenClaw 混合记忆架构设计

> **主题**: 对象存储 + 向量检索的分层记忆系统  
> **日期**: 2026-03-04  
> **目标**: 优化 LanceDB Pro + Markdown 混合架构

---

## 📋 当前架构分析

### 现有配置

```
OpenClaw Memory System
├── LanceDB Pro              # 向量检索层
│   ├── Vector Store         # 语义嵌入
│   ├── BM25                # 全文检索
│   └── Cross-Encoder Rerank # 重排序
│
├── Markdown Files           # 对象存储层
│   ├── memory/             # 每日记忆
│   ├── MEMORY.md           # 长期记忆索引
│   └── memory-*.md         # 分类记忆
│
└── Session Memory          # 短期缓存
    └── sessions/*.jsonl    # 对话历史
```

### 当前问题

| 问题 | 影响 | 原因 |
|------|------|------|
| **文件碎片化** | 检索慢 | Markdown 文件过多 |
| **元数据缺失** | 过滤困难 | 缺少结构化索引 |
| **无版本控制** | 无法追溯 | 文件直接覆盖 |
| **缓存缺失** | 重复查询 | 每次重新向量检索 |
| **无 TTL** | 存储膨胀 | 旧数据不自动清理 |

---

## 🏗️ 混合架构设计

### 三层架构

```
┌─────────────────────────────────────────┐
│          Query Interface Layer          │
│  (自然语言查询 → 路由 → 结果融合)        │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│ 热数据层 │ │温数据层 │ │ 冷数据层 │
│ (缓存)  │ │(向量检索)│ │(对象存储)│
│ Redis/  │ │LanceDB  │ │S3/MinIO  │
│ Memory  │ │Pro      │ │+ 索引    │
└─────────┘ └─────────┘ └──────────┘
    │            │            │
    └────────────┼────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Metadata Index       │
    │   (PostgreSQL/SQLite)  │
    │   - 标签               │
    │   - 时间               │
    │   - 来源               │
    │   - 重要性             │
    └────────────────────────┘
```

---

## 📊 各层详细设计

### 1️⃣ 热数据层 (Hot Tier)

**技术选型**: Redis / 内存缓存

**存储内容**:
- 最近 10 次对话
- 高频访问记忆
- Session 上下文
- 常用嵌入向量

**数据结构**:
```json
{
  "key": "memory:hot:recent",
  "type": "list",
  "ttl": 3600,
  "data": [
    {
      "id": "mem_20260304_001",
      "content": "用户偏好简洁的回复",
      "category": "preference",
      "importance": 0.9,
      "access_count": 15,
      "last_access": "2026-03-04T10:00:00Z"
    }
  ]
}
```

**淘汰策略**:
- LRU (最近最少使用)
- TTL 自动过期
- 重要性阈值（<0.3 淘汰）

---

### 2️⃣ 温数据层 (Warm Tier)

**技术选型**: LanceDB Pro (现有)

**优化点**:

#### A. 分区策略
```python
# 按时间 + 类别分区
partition_by = ["date", "category"]

# 示例分区结构
lancedb/
├── date=2026-03-04/
│   └── category=preference/
│       └── data.lance
├── date=2026-03-04/
│   └── category=decision/
│       └── data.lance
└── ...
```

#### B. 元数据增强
```python
schema = pa.schema([
    pa.field('id', pa.string()),
    pa.field('content', pa.string()),
    pa.field('embedding', pa.list_(pa.float32(), 768)),
    pa.field('category', pa.string()),      # 类别
    pa.field('importance', pa.float32()),   # 重要性 (0-1)
    pa.field('source', pa.string()),        # 来源 (session/cron/user)
    pa.field('created_at', pa.timestamp()), # 创建时间
    pa.field('updated_at', pa.timestamp()), # 更新时间
    pa.field('access_count', pa.int32()),   # 访问次数
    pa.field('tags', pa.list_(pa.string())),# 标签
    pa.field('related_ids', pa.list_(pa.string())) # 关联记忆
])
```

#### C. 索引优化
```python
# 向量索引 (IVF_PQ)
table.create_index(
    metric="cosine",
    num_partitions=256,
    num_sub_vectors=96
)

# 标量索引 (加速过滤)
table.create_index("category")
table.create_index("importance")
table.create_index("created_at")
```

---

### 3️⃣ 冷数据层 (Cold Tier)

**技术选型**: 对象存储 (S3/MinIO) + 索引文件

**存储内容**:
- 30 天前的记忆
- 完整对话记录
- 大型文档
- 归档数据

**目录结构**:
```
s3://openclaw-memory/
├── raw/                    # 原始数据
│   ├── sessions/
│   │   └── 2026-03/
│   │       └── session_001.jsonl
│   └── memories/
│       └── 2026-03/
│           └── memory_001.json
│
├── indexed/                # 索引数据
│   ├── metadata_index.parquet
│   └── timeline_index.json
│
└── archive/                # 归档数据
    └── 2026-Q1/
        └── quarterly_archive.zip
```

**对象元数据**:
```json
{
  "object_key": "raw/memories/2026-03/memory_001.json",
  "metadata": {
    "content_type": "application/json",
    "memory_category": "preference",
    "importance": 0.8,
    "created_at": "2026-03-04T10:00:00Z",
    "ttl_days": 365,
    "compression": "gzip"
  },
  "tags": {
    "project": "dss",
    "user": "K",
    "quarter": "2026-Q1"
  }
}
```

---

## 🔗 层间数据流转

### 写入流程

```
新记忆产生
    ↓
[1] 写入热数据层 (Redis)
    ├─ 设置 TTL (1 小时)
    └─ 记录访问计数
    ↓
[2] 异步写入温数据层 (LanceDB)
    ├─ 生成嵌入向量
    ├─ 添加元数据
    └─ 建立索引
    ↓
[3] 定期归档到冷数据层 (S3)
    ├─ 压缩打包
    ├─ 上传对象存储
    └─ 更新索引
```

### 读取流程

```
查询请求
    ↓
[1] 热数据层缓存命中？
    ├─ 是 → 返回 (延迟 <1ms)
    └─ 否 → 继续
    ↓
[2] 温数据层向量检索
    ├─ 语义搜索 (LanceDB)
    ├─ 元数据过滤
    └─ 重排序
    ↓
[3] 冷数据层 (如需历史数据)
    ├─ 查询索引
    ├─ 下载对象
    └─ 解压返回
    ↓
[4] 结果融合 + 缓存
```

---

## 🎯 记忆分层策略

### 按重要性分层

| 重要性 | 层级 | 存储 | 保留期 |
|--------|------|------|--------|
| **0.8-1.0** | 热数据 | Redis + LanceDB | 永久 |
| **0.5-0.8** | 温数据 | LanceDB | 1 年 |
| **0.3-0.5** | 冷数据 | S3 | 90 天 |
| **0-0.3** | 归档 | S3 Glacier | 30 天 |

### 按时间分层

| 时间 | 层级 | 说明 |
|------|------|------|
| **<1 小时** | 热数据 | Session 上下文 |
| **1 小时 -30 天** | 温数据 | 活跃记忆 |
| **30 天 -1 年** | 冷数据 | 历史记忆 |
| **>1 年** | 归档 | 季度归档 |

### 按类别分层

| 类别 | 层级 | 说明 |
|------|------|------|
| **preference** | 热→温 | 用户偏好 (高频访问) |
| **decision** | 温 | 重要决策 |
| **fact** | 温→冷 | 事实信息 |
| **session** | 冷 | 对话记录 |

---

## 📈 性能优化

### 1. 缓存策略

```python
class MemoryCache:
    def __init__(self):
        self.hot_cache = Redis()  # L1 缓存
        self.lru_cache = {}       # L2 缓存
        
    def get(self, key):
        # L1 缓存
        data = self.hot_cache.get(f"mem:{key}")
        if data:
            return json.loads(data)
        
        # L2 缓存
        if key in self.lru_cache:
            # 提升回 L1
            self.hot_cache.set(f"mem:{key}", 
                             json.dumps(self.lru_cache[key]), 
                             ex=3600)
            return self.lru_cache[key]
        
        # 缓存未命中，从 LanceDB 加载
        return None
    
    def set(self, key, data, importance=0.5):
        # 根据重要性设置 TTL
        ttl = self._calculate_ttl(importance)
        self.hot_cache.set(f"mem:{key}", json.dumps(data), ex=ttl)
        
        if importance > 0.7:
            self.lru_cache[key] = data
    
    def _calculate_ttl(self, importance):
        # 重要性越高，TTL 越长
        return int(importance * 86400)  # 最多 1 天
```

### 2. 批量写入

```python
class BatchWriter:
    def __init__(self, batch_size=100):
        self.buffer = []
        self.batch_size = batch_size
    
    def write(self, memory):
        self.buffer.append(memory)
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def flush(self):
        if not self.buffer:
            return
        
        # 批量写入 LanceDB
        table.add(self.buffer)
        
        # 批量上传 S3
        s3.upload_batch(self.buffer)
        
        self.buffer = []
```

### 3. 智能预取

```python
def prefetch_related(memories):
    """预取相关记忆"""
    for mem in memories:
        # 根据标签预取
        related = lancedb.query()\
            .filter(f"tags IN {mem['tags']}")\
            .limit(5)\
            .to_list()
        
        # 加入缓存
        cache.set_many(related)
```

---

## 🔍 查询优化

### 混合查询示例

```python
def hybrid_search(query, filters=None):
    """混合检索：向量 + 标量过滤 + 缓存"""
    
    # 1. 检查缓存
    cached = cache.search(query)
    if cached:
        return cached
    
    # 2. 向量检索 (LanceDB)
    query_vector = embed(query)
    results = table.search(query_vector)\
        .where("importance > 0.5")\  # 标量过滤
        .limit(20)\
        .to_list()
    
    # 3. 重排序 (Cross-Encoder)
    reranked = reranker.rerank(query, results)
    
    # 4. 结果融合
    final = fuse_results(reranked)
    
    # 5. 缓存结果
    cache.set(query, final, ttl=300)
    
    return final
```

### 时间范围查询

```python
def search_by_time_range(start, end, category=None):
    """按时间范围查询"""
    
    # 温数据层 (最近 30 天)
    warm = table.search()\
        .where(f"created_at BETWEEN {start} AND {end}")\
        .to_list()
    
    # 冷数据层 (30 天前)
    if start < datetime.now() - timedelta(days=30):
        cold = s3_index.query_time_range(start, end, category)
        warm.extend(cold)
    
    return warm
```

---

## 📊 监控指标

### 关键指标

| 指标 | 目标值 | 监控方式 |
|------|--------|----------|
| **缓存命中率** | >80% | Prometheus |
| **P99 延迟** | <100ms | Grafana |
| **向量检索延迟** | <50ms | LanceDB stats |
| **存储成本** | <¥100/月 | S3 账单 |
| **数据新鲜度** | <5 分钟 | 最后更新时间 |

### 告警规则

```yaml
alerts:
  - name: LowCacheHitRate
    condition: cache_hit_rate < 0.6
    duration: 5m
    
  - name: HighQueryLatency
    condition: query_p99 > 200ms
    duration: 10m
    
  - name: StorageFull
    condition: storage_used > 0.9
    duration: 1m
```

---

## 🚀 实施路线图

### 阶段 1: 基础架构 (1 周)
- [ ] 部署 Redis 缓存
- [ ] 优化 LanceDB 分区
- [ ] 添加元数据索引

### 阶段 2: 数据流转 (1 周)
- [ ] 实现热→温自动迁移
- [ ] 实现温→冷归档
- [ ] 配置 TTL 策略

### 阶段 3: 查询优化 (1 周)
- [ ] 实现混合查询
- [ ] 添加缓存层
- [ ] 优化重排序

### 阶段 4: 监控告警 (3 天)
- [ ] 部署 Prometheus
- [ ] 配置 Grafana 仪表板
- [ ] 设置告警规则

---

## 💡 针对当前系统的建议

### 立即可做（无需大改）

1. **添加元数据字段**
```python
# memory_store 工具增强
def memory_store(text, category, importance=0.7, tags=None):
    memory = {
        "text": text,
        "category": category,
        "importance": importance,
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
        "access_count": 0
    }
    lancedb.add(memory)
```

2. **实现简单缓存**
```python
# 在 OpenClaw 中添加
@lru_cache(maxsize=1000)
def cached_memory_search(query_hash):
    return memory_recall(query_hash)
```

3. **定期归档脚本**
```bash
# 每天 3:00 归档 30 天前记忆
0 3 * * * python3 /opt/openclaw/archive_memory.py --days-ago 30
```

### 中期优化（需要架构调整）

1. **引入 Redis 缓存层**
2. **LanceDB 分区优化**
3. **对象存储集成**（MinIO/S3）

### 长期愿景

1. **多区域复制**（高可用）
2. **增量备份**（灾难恢复）
3. **AI 驱动的记忆重要性评估**

---

*架构设计版本：v1.0*  
*创建时间：2026-03-04*  
*适用于：OpenClaw + LanceDB Pro*
