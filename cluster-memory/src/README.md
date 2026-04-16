# Cluster Memory System

一个基于 FastAPI + LanceDB + SQLite 的知识管理和检索系统。

## 功能特性

- **Memory Pool**: 存储和管理记忆，支持向量搜索
- **Cluster**: 记忆的逻辑分组，支持层级嵌套
- **Conversation Timeline**: 对话历史与记忆关联的时间线视图
- **REST API**: 完整的 RESTful API 接口

## 技术栈

- Python 3.11+
- FastAPI
- LanceDB (向量数据库)
- SQLite (辅助存储)
- Pydantic (数据验证)

## 项目结构

```
src/
├── models/           # 数据模型
│   ├── __init__.py
│   ├── memory.py     # Memory 模型
│   ├── cluster.py    # Cluster 模型
│   └── timeline.py   # Timeline 模型
├── services/         # 服务层
│   ├── __init__.py
│   ├── memory_pool.py      # Memory Pool 服务
│   ├── cluster_manager.py  # Cluster 管理服务
│   └── timeline_service.py # Timeline 服务
├── api/              # API 层
│   ├── __init__.py
│   ├── main.py       # FastAPI 应用入口
│   └── routes/       # API 路由
│       ├── __init__.py
│       ├── memory.py
│       ├── cluster.py
│       ├── timeline.py
│       └── search.py
└── requirements.txt
```

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
cd src
uvicorn api.main:app --reload
```

## API 文档

启动后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### Memory
- `POST /memories` - 创建 Memory
- `GET /memories/{id}` - 获取 Memory
- `PUT /memories/{id}` - 更新 Memory
- `DELETE /memories/{id}` - 删除 Memory
- `GET /memories/search?q=query` - 搜索 Memory
- `POST /memories/batch` - 批量创建

### Cluster
- `POST /clusters` - 创建 Cluster
- `GET /clusters/{id}` - 获取 Cluster
- `PUT /clusters/{id}` - 更新 Cluster
- `DELETE /clusters/{id}` - 删除 Cluster
- `GET /clusters/{id}/memories` - 获取 Cluster 内 Memory
- `POST /clusters/{id}/memories/{memory_id}` - 添加 Memory
- `DELETE /clusters/{id}/memories/{memory_id}` - 移除 Memory
- `GET /clusters/tree` - 获取 Cluster 树
- `POST /clusters/auto` - 自动聚类
- `POST /clusters/merge` - 合并 Cluster

### Timeline
- `POST /timelines` - 创建 Timeline
- `GET /timelines/{id}` - 获取 Timeline
- `DELETE /timelines/{id}` - 删除 Timeline
- `POST /timelines/{id}/node` - 添加节点
- `GET /timelines/{id}/range` - 获取时间范围节点
- `POST /timelines/conversations` - 创建 Conversation
- `GET /timelines/conversations/{id}` - 获取 Conversation

### Search
- `GET /search?q=query` - 全局搜索
- `GET /search/memories` - 搜索 Memory
- `GET /search/clusters` - 搜索 Cluster
- `POST /search/suggest` - 搜索建议
- `GET /search/tags` - 标签分布

## 数据模型

### Memory
```python
{
    "id": UUID,
    "content": str,
    "tags": list[str],
    "cluster_ids": list[UUID],
    "metadata": {
        "source": str,
        "author": str,
        "priority": int
    },
    "created_at": datetime,
    "updated_at": datetime
}
```

### Cluster
```python
{
    "id": UUID,
    "name": str,
    "description": str,
    "tags": list[str],
    "color": str,
    "memory_ids": list[UUID],
    "parent_cluster_id": UUID,
    "children": list[UUID],
    "stats": {
        "memory_count": int,
        "avg_similarity": float
    },
    "created_at": datetime,
    "updated_at": datetime
}
```

### Timeline
```python
{
    "id": UUID,
    "conversation_id": UUID,
    "title": str,
    "created_at": datetime,
    "updated_at": datetime
}
```

### TimelineNode
```python
{
    "id": UUID,
    "timeline_id": UUID,
    "event_type": "create" | "update" | "delete" | "reference" | "query",
    "content": str,
    "memory_id": UUID,
    "cluster_id": UUID,
    "timestamp": datetime,
    "position": int
}
```

## 注意事项

1. **嵌入服务**: 当前使用占位符实现，需要接入真实的嵌入服务（如 OpenAI 或阿里云 text-embedding-v2）
2. **自动聚类**: 当前基于标签聚类，需要实现基于相似度的聚类算法
3. **数据持久化**: 数据存储在 `./data/cluster_memory/` 目录下