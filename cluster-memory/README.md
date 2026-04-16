# Cluster Memory System

基于用户设计图片实现的 Cluster Memory 系统。

## 系统概述

- **Memory Pool**: 存储 Memory 的核心数据池，支持向量搜索
- **Cluster**: Memory 的逻辑分组，支持层级嵌套
- **Conversation Timeline**: 对话历史与 Memory 关联的时间线视图

## 项目结构

```
cluster-memory/
├── REQUIREMENTS.md       # 需求文档
├── DESIGN.md             # 架构设计文档
├── README.md             # 项目说明
├── pyproject.toml        # Python 项目配置
├── src/
│   ├── models/
│   │   ├── memory.py     # Memory 数据模型
│   │   ├── cluster.py    # Cluster 数据模型
│   │   └── timeline.py   # Timeline 数据模型
│   │   └── __init__.py
│   ├── services/
│   │   ├── memory_pool.py    # Memory Pool 服务 (LanceDB + SQLite)
│   │   ├── cluster_manager.py # Cluster 管理服务
│   │   ├── timeline_service.py # Timeline 服务
│   │   └── __init__.py
│   └── api/
│   │   ├── main.py       # FastAPI 应用入口
│       │   ├── routes/
│       │   │   ├── memory.py  # Memory API 路由
│       │   │   ├── cluster.py # Cluster API 路由
│       │   │   ├── timeline.py # Timeline API 路由
│       │   │   ├── search.py  # Search API 路由
│       │   └── __init__.py
└── tests/
    └── test_api.py       # 单元测试
```

## API 端点

### Memory API
- `POST /api/memories` - 创建 Memory
- `GET /api/memories/{id}` - 获取 Memory
- `PUT /api/memories/{id}` - 更新 Memory
- `DELETE /api/memories/{id}` - 删除 Memory
- `GET /api/memories/search` - 搜索 Memory

### Cluster API
- `POST /api/clusters` - 创建 Cluster
- `GET /api/clusters/{id}` - 获取 Cluster
- `POST /api/clusters/auto` - 自动聚类

### Timeline API
- `POST /api/timelines` - 创建 Timeline
- `GET /api/timelines/{id}` - 获取 Timeline
- `GET /api/timelines/{id}/range` - 获取时间范围节点

### Search API
- `GET /api/search?q=query` - 全局搜索

## 技术栈

- **API**: FastAPI
- **Vector DB**: LanceDB
- **Storage**: SQLite
- **Models**: Pydantic

## 安装

```bash
cd cluster-memory
pip install -e .
```

## 运行

```bash
uvicorn src.api.main:app --reload --port 8000
```

## 测试

```bash
pytest tests/
```

---
*创建时间: 2026-04-16*