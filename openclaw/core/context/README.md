# Context Manager - 上下文管理器

> **4 层上下文系统**  
> **版本**: 1.0.0  
> **状态**: ✅ 完成

---

## 📖 功能说明

上下文管理器负责 AI 的 4 层上下文管理，支持：

- ✅ 4 层结构 (System/Module/Function/Execution)
- ✅ 智能压缩
- ✅ 语义查询
- ✅ TTL 支持

---

## 🚀 快速开始

### 1. 导入模块

```python
from openclaw.core.context import (
    HierarchicalContextManager,
    ContextLevel,
    ContextEntry
)
```

### 2. 创建和初始化

```python
manager = HierarchicalContextManager()
await manager.initialize()
```

### 3. 使用上下文

```python
# 设置上下文
await manager.set_context(ContextEntry(
    key="system_rule",
    value="Be helpful and harmless",
    level=ContextLevel.SYSTEM,
    priority=10
))

# 获取上下文
entries = await manager.get_context(ContextLevel.SYSTEM)

# 查询上下文
results = await manager.query_context(
    query="system rules",
    levels=[ContextLevel.SYSTEM, ContextLevel.MODULE],
    limit=10
)
```

---

## 📐 4 层结构

### Level 1: SYSTEM (系统级)

全局规则、安全策略、跨模块共享规则。

```python
ContextEntry(
    key="safety_policy",
    value="Never harm humans",
    level=ContextLevel.SYSTEM,
    priority=100  # 最高优先级
)
```

### Level 2: MODULE (模块级)

模块配置、能力声明、模块间接口定义。

```python
ContextEntry(
    key="memory_capabilities",
    value=["store", "retrieve", "search"],
    level=ContextLevel.MODULE,
    priority=50
)
```

### Level 3: FUNCTION (功能级)

函数定义、参数说明、返回值规范。

```python
ContextEntry(
    key="store_signature",
    value="store(key: str, value: Any) -> str",
    level=ContextLevel.FUNCTION,
    priority=30
)
```

### Level 4: EXECUTION (执行级)

运行时状态、历史记录、临时数据。

```python
ContextEntry(
    key="current_task",
    value="Processing user request",
    level=ContextLevel.EXECUTION,
    ttl=300  # 5 分钟过期
)
```

---

## 📊 API 参考

### ContextLevel

上下文层级枚举。

| 值 | 说明 |
|------|------|
| `SYSTEM` | 系统级 |
| `MODULE` | 模块级 |
| `FUNCTION` | 功能级 |
| `EXECUTION` | 执行级 |

### ContextEntry

上下文条目数据类。

| 字段 | 类型 | 说明 |
|------|------|------|
| `key` | str | 唯一键 |
| `value` | Any | 值 |
| `level` | ContextLevel | 层级 |
| `priority` | int | 优先级 (0-100) |
| `ttl` | Optional[int] | 过期时间 (秒) |

### HierarchicalContextManager

上下文管理器主类。

#### set_context(entry)

设置上下文条目。

**参数**:
- `entry` (ContextEntry): 上下文条目

#### get_context(level, key)

获取上下文。

**参数**:
- `level` (ContextLevel): 层级
- `key` (Optional[str]): 键

**返回**: List[ContextEntry]

#### query_context(query, levels, limit)

语义查询上下文。

**参数**:
- `query` (str): 查询词
- `levels` (List[ContextLevel]): 层级列表
- `limit` (int): 返回数量

**返回**: List[ContextEntry]

#### compress_context(level, target_tokens)

压缩上下文。

**参数**:
- `level` (ContextLevel): 层级
- `target_tokens` (int): 目标 token 数

**返回**: List[ContextEntry]

---

## 🤖 AI 元数据

本模块完全采用 AI 专用格式：

- `@module`, `@purpose` - 模块元数据
- `@enum` - 枚举定义
- `@schema` - Schema 定义
- `@class`, `@function` - 类和函数
- `@test_for` - 测试定义

AI 可以完全理解并自动生成代码、测试和文档。

---

*最后更新：2026-03-07*  
*状态：✅ 完成*
