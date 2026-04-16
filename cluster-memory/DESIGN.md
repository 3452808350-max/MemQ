# Cluster Memory 系统架构设计

## 1. 系统概述

### 1.1 核心概念
- **Memory Pool**: 存储所有 Memory 的核心数据池，支持向量搜索
- **Cluster**: Memory 的逻辑分组，支持层级嵌套
- **Conversation Timeline**: 对话历史与 Memory 关联的时间线视图

### 1.2 设计目标
- 高效的知识管理和检索
- 自动聚类和智能推荐
- 可视化的 Timeline 导航

## 2. 架构设计

### 2.1 系统架构图
```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Search UI    │  │ Cluster UI   │  │ Timeline UI      │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway                           │
│                    (REST + WebSocket)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ MemoryService│  │ClusterService│  │TimelineService   │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ SearchService│  │ EmbedService │  │ ClusterAI        │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Storage Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ VectorDB     │  │ GraphDB      │  │ TimeSeriesDB     │   │
│  │ (LanceDB)    │  │ (Neo4j Lite) │  │ (SQLite)         │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Memory Pool 设计
```python
class MemoryPool:
    """Memory Pool 数据结构"""
    
    def __init__(self):
        self.memories: Dict[UUID, Memory] = {}
        self.embeddings: LanceDBTable  # 向量索引
        self.cluster_index: Dict[UUID, Set[UUID]]  # Cluster → Memories
    
    async def add(self, memory: Memory) -> UUID:
        # 1. 生成 embedding
        embedding = await self.embed_service.embed(memory.content)
        # 2. 存储向量
        await self.embeddings.add({
            "id": memory.id,
            "vector": embedding,
            "content": memory.content
        })
        # 3. 存储 Memory
        self.memories[memory.id] = memory
        return memory.id
    
    async def search(self, query: str, k: int = 10) -> List[Memory]:
        # 1. 查询向量
        query_vec = await self.embed_service.embed(query)
        # 2. 向量搜索
        results = await self.embeddings.search(query_vec, k)
        # 3. 返回 Memory
        return [self.memories[r["id"]] for r in results]
```

### 2.3 Cluster 组织方式
```python
class ClusterManager:
    """Cluster 管理器"""
    
    def __init__(self):
        self.clusters: Dict[UUID, Cluster] = {}
        self.graph: ClusterGraph  # Cluster 关系图
    
    async def create_cluster(
        self, 
        name: str,
        memory_ids: List[UUID],
        parent_id: Optional[UUID] = None
    ) -> Cluster:
        cluster = Cluster(
            id=uuid4(),
            name=name,
            memory_ids=set(memory_ids),
            parent_cluster_id=parent_id
        )
        self.clusters[cluster.id] = cluster
        await self.graph.add_node(cluster)
        if parent_id:
            await self.graph.add_edge(parent_id, cluster.id)
        return cluster
    
    async def auto_cluster(self, memories: List[Memory]) -> List[Cluster]:
        # 使用 embedding 相似度自动聚类
        embeddings = [m.embedding for m in memories]
        # K-means 或 HDBSCAN 聚类
        labels = await self.cluster_ai.cluster(embeddings)
        # 创建 Cluster
        clusters = []
        for label in set(labels):
            cluster_memories = [m for m, l in zip(memories, labels) if l == label]
            cluster = await self.create_cluster(
                name=f"Auto Cluster {label}",
                memory_ids=[m.id for m in cluster_memories]
            )
            clusters.append(cluster)
        return clusters
```

### 2.4 Conversation Timeline 流程
```python
class ConversationTimeline:
    """对话时间线"""
    
    def __init__(self, conversation_id: UUID):
        self.conversation_id = conversation_id
        self.nodes: List[TimelineNode] = []
        self.memory_refs: Dict[UUID, TimelineNode] = {}
    
    async def add_node(
        self,
        event_type: str,
        content: Optional[str] = None,
        memory_id: Optional[UUID] = None
    ) -> TimelineNode:
        node = TimelineNode(
            timestamp=datetime.now(),
            event_type=event_type,
            content=content,
            memory_id=memory_id
        )
        self.nodes.append(node)
        if memory_id:
            self.memory_refs[memory_id] = node
        return node
    
    async def get_memory_at(self, memory_id: UUID) -> TimelineNode:
        return self.memory_refs.get(memory_id)
    
    async def get_range(
        self, 
        start: datetime, 
        end: datetime
    ) -> List[TimelineNode]:
        return [
            n for n in self.nodes 
            if start <= n.timestamp <= end
        ]
```

## 3. API 设计

### 3.1 Memory API
```
POST   /api/memories          # 创建 Memory
GET    /api/memories/:id      # 获取单个 Memory
PUT    /api/memories/:id      # 更新 Memory
DELETE /api/memories/:id      # 删除 Memory
GET    /api/memories/search   # 搜索 Memory
POST   /api/memories/batch    # 批量创建
```

### 3.2 Cluster API
```
POST   /api/clusters              # 创建 Cluster
GET    /api/clusters/:id          # 获取 Cluster
PUT    /api/clusters/:id          # 更新 Cluster
DELETE /api/clusters/:id          # 删除 Cluster
GET    /api/clusters/:id/memories # 获取 Cluster 内所有 Memory
POST   /api/clusters/auto         # 自动聚类
POST   /api/clusters/:id/merge    # 合并 Cluster
POST   /api/clusters/:id/split    # 拆分 Cluster
```

### 3.3 Timeline API
```
POST   /api/timelines                 # 创建 Timeline
GET    /api/timelines/:id             # 获取 Timeline
GET    /api/timelines/:id/range       # 获取时间范围节点
GET    /api/timelines/:id/memory/:mid # 获取 Memory 关联节点
POST   /api/timelines/:id/node        # 添加节点
```

### 3.4 Search API
```
GET    /api/search?q=query&type=all     # 全局搜索
GET    /api/search?q=query&type=memory  # 搜索 Memory
GET    /api/search?q=query&type=cluster # 搜索 Cluster
POST   /api/search/suggest              # 搜索建议
```

## 4. 数据模型

### 4.1 Memory Schema
```typescript
interface Memory {
  id: string;           // UUID
  content: string;      // 文本内容
  cluster_ids: string[]; // 所属 Cluster
  created_at: Date;
  updated_at: Date;
  tags: string[];
  metadata: {
    source?: string;
    author?: string;
    priority?: number;
    [key: string]: any;
  };
  embedding?: number[]; // 向量 (可选，内部使用)
}
```

### 4.2 Cluster Schema
```typescript
interface Cluster {
  id: string;
  name: string;
  description?: string;
  memory_ids: string[];
  tags: string[];
  created_at: Date;
  updated_at: Date;
  parent_cluster_id?: string;
  children?: string[];
  stats: {
    memory_count: number;
    avg_similarity: number;
  };
}
```

### 4.3 Conversation Schema
```typescript
interface Conversation {
  id: string;
  timeline: TimelineNode[];
  memory_refs: string[];
  created_at: Date;
  updated_at: Date;
  metadata: {
    title?: string;
    participants?: string[];
  };
}

interface TimelineNode {
  id: string;
  timestamp: Date;
  memory_id?: string;
  event_type: 'create' | 'update' | 'delete' | 'reference' | 'query';
  content?: string;
  position: number;
}
```

## 5. UI 组件设计

### 5.1 搜索栏组件
```tsx
<SearchBar>
  <Input placeholder="Search memories, clusters..." />
  <SearchTypeSelector options={['all', 'memory', 'cluster']} />
  <SearchSuggestions />
</SearchBar>
```

### 5.2 分类侧边栏
```tsx
<Sidebar>
  <ClusterTree clusters={clusters} onSelect={handleSelect} />
  <TagList tags={tags} onSelect={handleFilter} />
  <QuickActions>
    <Button>Create Memory</Button>
    <Button>Create Cluster</Button>
  </QuickActions>
</Sidebar>
```

### 5.3 内容卡片
```tsx
<MemoryCard memory={memory}>
  <CardContent>
    <Title>{memory.content.slice(0, 100)}</Title>
    <Tags>{memory.tags}</Tags>
    <Meta>
      <Date>{memory.created_at}</Date>
      <ClusterBadge>{cluster.name}</ClusterBadge>
    </Meta>
  </CardContent>
  <CardActions>
    <Button>Edit</Button>
    <Button>Delete</Button>
    <Button>Move to Cluster</Button>
  </CardActions>
</MemoryCard>
```

### 5.4 Timeline 视图
```tsx
<TimelineView conversation={conversation}>
  <TimelineAxis>
    {nodes.map(node => (
      <TimelineNode 
        key={node.id}
        type={node.event_type}
        timestamp={node.timestamp}
        memoryId={node.memory_id}
        onClick={() => navigateToMemory(node.memory_id)}
      />
    ))}
  </TimelineAxis>
  <TimeRangeSlider />
  <MemoryPreview memory={selectedMemory} />
</TimelineView>
```

## 6. 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| Frontend | React + TypeScript | 组件化 UI |
| API | FastAPI | Python 异步框架 |
| Vector DB | LanceDB | 嵌入式向量数据库 |
| Graph DB | SQLite + Adjacency List | 轻量图存储 |
| Time Series | SQLite | 时间线存储 |
| Embedding | text-embedding-v2 (阿里云) | 向量化服务 |

## 7. 实现计划

### Phase 1: Core Storage (Week 1)
- Memory Pool 数据结构
- LanceDB 向量索引
- SQLite 存储

### Phase 2: Services (Week 2)
- MemoryService CRUD
- EmbedService 向量化
- SearchService 搜索

### Phase 3: Clustering (Week 3)
- Cluster 数据结构
- AutoCluster 聚类算法
- ClusterGraph 关系管理

### Phase 4: Timeline (Week 4)
- Timeline 数据结构
- Conversation 关联
- 导航功能

### Phase 5: Frontend (Week 5)
- Search UI
- Cluster UI
- Timeline UI

---
*创建时间: 2026-04-16*