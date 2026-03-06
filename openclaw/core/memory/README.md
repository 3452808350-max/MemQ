# Memory Manager - 内存管理器

> **AI-First 试点模块**  
> **版本**: 1.0.0  
> **状态**: ✅ 完成

---

## 📖 功能说明

内存管理器负责 AI 的长期记忆存储和检索，支持：

- ✅ 键值存储
- ✅ TTL (过期时间)
- ✅ 语义搜索
- ✅ 自动压缩
- ✅ 线程安全

---

## 🚀 快速开始

### 1. 导入模块

```python
from openclaw.core.memory import MemoryManager, MemoryConfig
```

### 2. 创建配置

```python
config = MemoryConfig(
    database_path="./data/memory.db",
    max_tokens=4000,
    compression_enabled=True,
    default_ttl=3600
)
```

### 3. 初始化和使用

```python
manager = MemoryManager(config)
await manager.initialize()

# 存储记忆
memory_id = await manager.store("user_name", "Alice")

# 检索记忆
value = await manager.retrieve("user_name")

# 搜索记忆
results = await manager.search("user information")
```

---

## 📐 API 参考

### MemoryConfig

配置内存管理器参数。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `database_path` | str | 必需 | 数据库路径 |
| `max_tokens` | int | 4000 | 最大 token 数 |
| `compression_enabled` | bool | True | 启用压缩 |
| `compression_threshold` | float | 0.8 | 压缩阈值 |
| `default_ttl` | Optional[int] | 3600 | 默认过期时间 |

### MemoryManager

#### store(key, value, ttl)

存储记忆。

**参数**:
- `key` (str): 唯一键
- `value` (Any): 存储值
- `ttl` (Optional[int]): 过期时间 (秒)

**返回**: str (记忆 ID)

**示例**:
```python
memory_id = await manager.store("user_name", "Alice", ttl=3600)
```

#### retrieve(key)

检索记忆。

**参数**:
- `key` (str): 记忆键

**返回**: Optional[Any]

**示例**:
```python
value = await manager.retrieve("user_name")
```

#### search(query, limit, threshold)

语义搜索记忆。

**参数**:
- `query` (str): 搜索词
- `limit` (int): 返回数量
- `threshold` (float): 相关性阈值

**返回**: List[MemorySearchResult]

**示例**:
```python
results = await manager.search("user information", limit=10)
```

#### delete(key)

删除记忆。

**参数**:
- `key` (str): 记忆键

**返回**: bool

#### clear(pattern)

清除记忆。

**参数**:
- `pattern` (Optional[str]): 匹配模式

**返回**: int (清除数量)

#### get_stats()

获取统计信息。

**返回**: MemoryStats

---

## 🤖 AI 元数据

本模块完全采用 AI 专用格式，包含：

- `@module`, `@purpose` - 模块元数据
- `@schema` - 数据结构定义
- `@function`, `@input`, `@output` - 函数签名
- `@error` - 错误定义
- `@test_for` - 测试定义

AI 可以完全理解并自动生成代码、测试和文档。

---

## 📝 相关文件

- [schemas.py](schemas.py) - Schema 定义
- [errors.py](errors.py) - 错误定义
- [manager.py](manager.py) - 管理器实现

---

## 🧪 测试

运行测试：

```bash
python -m pytest tests/test_memory.py -v
```

测试覆盖率目标：95%+

---

*最后更新：2026-03-06*  
*状态：✅ 完成*
