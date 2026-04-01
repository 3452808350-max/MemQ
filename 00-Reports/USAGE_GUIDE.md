# OpenClaw 使用指南

> **版本**: 2026.3.7  
> **状态**: ✅ 完成  
> **适用**: 开发者和管理员

---

## 📖 目录

1. [快速开始](#快速开始)
2. [核心组件](#核心组件)
3. [使用示例](#使用示例)
4. [最佳实践](#最佳实践)
5. [性能优化](#性能优化)
6. [故障排查](#故障排查)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /home/kyj/.openclaw/workspace
pip install -r requirements.txt
```

### 2. 导入模块

```python
from openclaw.core.cache import CacheManager
from openclaw.core.context import HierarchicalContextManager
from openclaw.core.config.schemas import OpenClawConfig
from openclaw.core.db_pool import DatabasePool
```

### 3. 基本使用

```python
# 缓存
cache = CacheManager.get_instance()
cache.set("key", "value")
value = cache.get("key")

# 上下文
context = HierarchicalContextManager()
await context.initialize()
await context.set_context(ContextEntry(
    key="rule",
    value="Be helpful",
    level=ContextLevel.SYSTEM
))

# 数据库
pool = DatabasePool()
await pool.initialize()
results = await pool.execute("SELECT * FROM users")
```

---

## 📦 核心组件

### 1. 缓存系统

#### 3 层缓存架构

```
L1 (100 条)  - 最快 <1ms
L2 (1000 条) - 快 <5ms
L3 (10000 条) - 中等 <10ms
```

#### 使用方法

```python
from openclaw.core.cache import CacheManager

# 获取缓存实例
cache = CacheManager.get_instance()

# 设置缓存
cache.set("key", "value", ttl=3600)

# 获取缓存
value = cache.get("key")

# 删除缓存
cache.delete("key")

# 查看统计
stats = cache.get_stats()
```

#### 异步缓存

```python
from openclaw.core.cache.async_cache import AsyncMultiLayerCache

cache = AsyncMultiLayerCache()
await cache.set("key", "value")
value = await cache.get("key")
```

#### 批处理

```python
from openclaw.core.cache.async_cache import AsyncBatchCache

batch = AsyncBatchCache(cache)

# 批量写入
items = {"key1": "value1", "key2": "value2"}
await batch.set_batch(items)

# 批量读取
keys = ["key1", "key2"]
results = await batch.get_batch(keys)
```

---

### 2. 上下文系统

#### 4 层上下文架构

```
SYSTEM    - 全局规则、安全策略
MODULE    - 模块配置、能力声明
FUNCTION  - 函数定义、参数说明
EXECUTION - 运行时状态、历史记录
```

#### 使用方法

```python
from openclaw.core.context import (
    HierarchicalContextManager,
    ContextLevel,
    ContextEntry
)

context = HierarchicalContextManager()
await context.initialize()

# 设置上下文
await context.set_context(ContextEntry(
    key="system_rule",
    value="Be helpful",
    level=ContextLevel.SYSTEM,
    priority=10
))

# 获取上下文
entries = await context.get_context(ContextLevel.SYSTEM)

# 查询上下文
results = await context.query_context(
    query="system rules",
    levels=[ContextLevel.SYSTEM],
    limit=10
)
```

---

### 3. 配置系统

#### Pydantic Schema

```python
from openclaw.core.config.schemas import OpenClawConfig

# 创建配置
config = OpenClawConfig()

# 验证配置
errors = config.validate_all()

# 导出 Schema
schema = config.export_schema()
```

#### 使用配置

```python
# 获取配置值
app_name = config.get("app_name")
version = config.get("version")

# 设置配置值
config.set("debug", True)

# 保存配置
config.save("config.yaml")
```

---

### 4. 数据库连接池

#### 连接池管理

```python
from openclaw.core.db_pool import DatabasePool, PoolConfig

config = PoolConfig(
    database_path="./data.db",
    max_connections=10,
    min_connections=2
)

pool = DatabasePool(config)
await pool.initialize()

# 执行查询
results = await pool.execute(
    "SELECT * FROM users WHERE id = ?",
    (user_id,)
)

# 查看统计
stats = await pool.get_stats()

# 关闭连接池
await pool.close_all()
```

#### 并发访问

```python
async def insert_data(i):
    await pool.execute(
        "INSERT INTO test VALUES (?, ?)",
        (i, f"value_{i}")
    )

# 并发插入
await asyncio.gather(*[insert_data(i) for i in range(100)])
```

---

## 💡 使用示例

### 示例 1: 缓存热点数据

```python
from openclaw.core.cache import CacheManager

cache = CacheManager.get_instance()

# 检查缓存
data = cache.get("user_123")
if data is None:
    # 从数据库加载
    data = await load_from_database("user_123")
    # 存入缓存
    cache.set("user_123", data, ttl=3600)
```

### 示例 2: 管理 AI 上下文

```python
from openclaw.core.context import HierarchicalContextManager, ContextLevel

context = HierarchicalContextManager()
await context.initialize()

# 设置系统规则
await context.set_context(ContextEntry(
    key="safety_rule",
    value="Never harm humans",
    level=ContextLevel.SYSTEM,
    priority=100
))

# 设置模块配置
await context.set_context(ContextEntry(
    key="memory_capabilities",
    value=["store", "retrieve", "search"],
    level=ContextLevel.MODULE
))

# 查询上下文
results = await context.query_context(
    query="rules",
    levels=[ContextLevel.SYSTEM, ContextLevel.MODULE],
    limit=10
)
```

### 示例 3: 批量操作

```python
from openclaw.core.cache.async_cache import AsyncMultiLayerCache, AsyncBatchCache

cache = AsyncMultiLayerCache()
batch = AsyncBatchCache(cache)

# 批量写入 1000 条
items = {f"key_{i}": f"value_{i}" for i in range(1000)}
await batch.set_batch(items)

# 批量读取
keys = [f"key_{i}" for i in range(1000)]
results = await batch.get_batch(keys)
```

### 示例 4: 数据库事务

```python
from openclaw.core.db_pool import DatabasePool

pool = DatabasePool()
await pool.initialize()

# 执行事务
await pool.execute("BEGIN TRANSACTION")
try:
    await pool.execute("INSERT INTO users VALUES (?, ?)", (1, "Alice"))
    await pool.execute("INSERT INTO users VALUES (?, ?)", (2, "Bob"))
    await pool.execute("COMMIT")
except Exception as e:
    await pool.execute("ROLLBACK")
    raise
```

---

## 🎯 最佳实践

### 1. 缓存使用

✅ **推荐**:
- 热点数据使用 L1 缓存
- 常用数据使用 L2 缓存
- 一般数据使用 L3 缓存
- 设置合理的 TTL

❌ **避免**:
- 缓存过大对象
- 不设置 TTL
- 缓存敏感数据

### 2. 上下文管理

✅ **推荐**:
- 系统规则设置高优先级
- 设置合理的 TTL
- 定期清理过期上下文

❌ **避免**:
- 上下文层级混乱
- 不设置优先级
- 无限增长

### 3. 数据库访问

✅ **推荐**:
- 使用连接池
- 使用参数化查询
- 及时释放连接

❌ **避免**:
- 直接创建连接
- SQL 注入风险
- 连接泄漏

### 4. 性能优化

✅ **推荐**:
- 批量操作
- 异步访问
- 并发处理

❌ **避免**:
- 单次循环访问
- 同步阻塞
- 串行处理

---

## 📊 性能优化

### 缓存策略

| 数据类型 | 推荐层级 | TTL |
|---------|---------|-----|
| **热点数据** | L1 | 5 分钟 |
| **常用数据** | L2 | 1 小时 |
| **一般数据** | L3 | 1 天 |
| **静态数据** | L3 | 永久 |

### 批量操作

```python
# 推荐：批量操作
await batch.set_batch(items)  # 0.069ms/条

# 避免：单次操作
for key, value in items.items():
    await cache.set(key, value)  # 0.085ms/条
```

### 并发访问

```python
# 推荐：并发访问
await asyncio.gather(*[task(i) for i in range(100)])

# 避免：串行访问
for i in range(100):
    await task(i)
```

---

## 🐛 故障排查

### 问题 1: 缓存未命中

**症状**: `cache.get(key)` 返回 `None`

**解决**:
1. 检查 key 是否正确
2. 检查 TTL 是否过期
3. 检查缓存是否被清理

### 问题 2: 连接池耗尽

**症状**: 等待连接超时

**解决**:
1. 增加 `max_connections`
2. 检查连接泄漏
3. 减少并发量

### 问题 3: 上下文丢失

**症状**: 上下文查询不到

**解决**:
1. 检查上下文层级
2. 检查 TTL 是否过期
3. 检查优先级设置

---

## 📚 参考文档

- [性能基准报告](BENCHMARK_REPORT.md)
- [性能优化报告](PERFORMANCE_OPTIMIZATION_FINAL.md)
- [AI-First 架构报告](AI_FIRST_FINAL_REPORT.md)

---

**文档版本**: 2026.3.7  
**最后更新**: 2026-03-07  
**状态**: ✅ 完成

---

*OpenClaw 使用指南完成！* 📖
