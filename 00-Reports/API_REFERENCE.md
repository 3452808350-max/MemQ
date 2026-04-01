# OpenClaw API 参考文档

> **版本**: 2026.3.7  
> **生成时间**: 2026-03-07  
> **状态**: ✅ 完成

---

## 📦 核心模块

### cache - 缓存系统

#### CacheManager

```python
from openclaw.core.cache import CacheManager
```

**方法**:

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_instance()` | - | CacheManager | 获取单例实例 |
| `get(key: str)` | key: str | Optional[Any] | 获取缓存 |
| `set(key, value, ttl)` | key: str, value: Any, ttl: Optional[int] | None | 设置缓存 |
| `delete(key: str)` | key: str | bool | 删除缓存 |
| `clear()` | - | None | 清空缓存 |
| `get_stats()` | - | Dict[str, Any] | 获取统计 |

**示例**:

```python
cache = CacheManager.get_instance()
cache.set("key", "value", ttl=3600)
value = cache.get("key")
```

---

#### AsyncMultiLayerCache

```python
from openclaw.core.cache.async_cache import AsyncMultiLayerCache
```

**方法**:

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get(key: str)` | key: str | Optional[Any] | 异步获取 |
| `set(key, value, ttl)` | key: str, value: Any, ttl: Optional[int] | None | 异步设置 |
| `delete(key: str)` | key: str | bool | 异步删除 |
| `clear()` | - | None | 异步清空 |
| `get_stats()` | - | Dict[str, Any] | 获取统计 |

**示例**:

```python
cache = AsyncMultiLayerCache()
await cache.set("key", "value")
value = await cache.get("key")
```

---

#### AsyncBatchCache

```python
from openclaw.core.cache.async_cache import AsyncBatchCache
```

**方法**:

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_batch(keys)` | keys: List[str] | Dict[str, Any] | 批量获取 |
| `set_batch(items, ttl)` | items: Dict[str, Any], ttl: Optional[int] | None | 批量设置 |
| `delete_batch(keys)` | keys: List[str] | Dict[str, bool] | 批量删除 |

**示例**:

```python
batch = AsyncBatchCache(cache)
items = {"key1": "value1", "key2": "value2"}
await batch.set_batch(items)
results = await batch.get_batch(["key1", "key2"])
```

---

### context - 上下文系统

#### HierarchicalContextManager

```python
from openclaw.core.context import HierarchicalContextManager, ContextLevel, ContextEntry
```

**方法**:

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `initialize()` | - | None | 初始化 |
| `shutdown()` | - | None | 关闭 |
| `get_context(level, key)` | level: ContextLevel, key: Optional[str] | List[ContextEntry] | 获取上下文 |
| `set_context(entry)` | entry: ContextEntry | None | 设置上下文 |
| `query_context(query, levels, limit)` | query: str, levels: List[ContextLevel], limit: int | List[ContextEntry] | 查询上下文 |
| `compress_context(level, target_tokens)` | level: ContextLevel, target_tokens: int | List[ContextEntry] | 压缩上下文 |
| `get_stats()` | - | Dict[str, Any] | 获取统计 |

**示例**:

```python
context = HierarchicalContextManager()
await context.initialize()

await context.set_context(ContextEntry(
    key="rule",
    value="Be helpful",
    level=ContextLevel.SYSTEM,
    priority=10
))

entries = await context.get_context(ContextLevel.SYSTEM)
```

---

### config - 配置系统

#### OpenClawConfig

```python
from openclaw.core.config.schemas import OpenClawConfig
```

**方法**:

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get(key, default)` | key: str, default: Any | Any | 获取配置 |
| `set(key, value)` | key: str, value: Any | None | 设置配置 |
| `validate_all()` | - | List[str] | 验证配置 |
| `export_schema()` | - | Dict[str, Any] | 导出 Schema |
| `save(path)` | path: str | None | 保存配置 |

**示例**:

```python
config = OpenClawConfig()
app_name = config.get("app_name")
config.set("debug", True)
errors = config.validate_all()
```

---

### db_pool - 数据库连接池

#### DatabasePool

```python
from openclaw.core.db_pool import DatabasePool, PoolConfig
```

**方法**:

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `initialize()` | - | None | 初始化 |
| `acquire()` | - | DatabaseConnection | 获取连接 |
| `release(conn)` | conn: DatabaseConnection | None | 释放连接 |
| `execute(query, params)` | query: str, params: Optional[tuple] | List[Dict[str, Any]] | 执行查询 |
| `cleanup_idle()` | - | None | 清理空闲连接 |
| `get_stats()` | - | Dict[str, Any] | 获取统计 |
| `close_all()` | - | None | 关闭所有连接 |

**示例**:

```python
config = PoolConfig(database_path="./data.db")
pool = DatabasePool(config)
await pool.initialize()

results = await pool.execute(
    "SELECT * FROM users WHERE id = ?",
    (user_id,)
)

stats = await pool.get_stats()
await pool.close_all()
```

---

## 📊 数据结构

### ContextEntry

```python
@dataclass
class ContextEntry:
    key: str
    value: Any
    level: ContextLevel
    priority: int = 0
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[int] = 3600
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**字段**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `key` | str | - | 唯一键 |
| `value` | Any | - | 值 |
| `level` | ContextLevel | - | 层级 |
| `priority` | int | 0 | 优先级 |
| `timestamp` | float | time.time() | 创建时间 |
| `ttl` | Optional[int] | 3600 | 过期时间 |
| `metadata` | Dict[str, Any] | {} | 元数据 |

---

### ContextLevel

```python
class ContextLevel(str, Enum):
    SYSTEM = "system"      # 系统级
    MODULE = "module"      # 模块级
    FUNCTION = "function"  # 功能级
    EXECUTION = "execution" # 执行级
```

---

### PoolConfig

```python
@dataclass
class PoolConfig:
    database_path: str = ":memory:"
    max_connections: int = 10
    min_connections: int = 2
    max_idle_time: int = 300
```

**字段**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `database_path` | str | ":memory:" | 数据库路径 |
| `max_connections` | int | 10 | 最大连接数 |
| `min_connections` | int | 2 | 最小连接数 |
| `max_idle_time` | int | 300 | 最大空闲时间 (秒) |

---

## 🎯 使用模式

### 模式 1: 缓存热点数据

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

### 模式 2: 管理 AI 上下文

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

# 查询上下文
results = await context.query_context(
    query="rules",
    levels=[ContextLevel.SYSTEM],
    limit=10
)
```

### 模式 3: 批量操作

```python
from openclaw.core.cache.async_cache import AsyncMultiLayerCache, AsyncBatchCache

cache = AsyncMultiLayerCache()
batch = AsyncBatchCache(cache)

# 批量写入
items = {f"key_{i}": f"value_{i}" for i in range(1000)}
await batch.set_batch(items)

# 批量读取
keys = [f"key_{i}" for i in range(1000)]
results = await batch.get_batch(keys)
```

### 模式 4: 数据库事务

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

## 📚 参考文档

- [使用指南](USAGE_GUIDE.md)
- [性能基准报告](BENCHMARK_REPORT.md)
- [性能优化报告](PERFORMANCE_OPTIMIZATION_FINAL.md)

---

**API 版本**: 2026.3.7  
**最后更新**: 2026-03-07  
**状态**: ✅ 完成

---

*OpenClaw API 参考文档完成！* 📖
