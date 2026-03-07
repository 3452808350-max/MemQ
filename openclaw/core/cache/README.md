# Cache - 缓存系统

> **3 层缓存优化**  
> **版本**: 1.0.0  
> **状态**: ✅ 完成

---

## 📖 功能说明

缓存系统负责 OpenClaw 的性能优化，支持：

- ✅ 3 层缓存 (L1/L2/L3)
- ✅ LRU 淘汰
- ✅ TTL 支持
- ✅ 自动晋升
- ✅ 统计监控

---

## 🚀 快速开始

### 1. 导入模块

```python
from openclaw.core.cache import CacheManager
```

### 2. 获取缓存实例

```python
cache = CacheManager.get_instance()
```

### 3. 使用缓存

```python
# 设置缓存
cache.set("key", "value", ttl=3600)

# 获取缓存
value = cache.get("key")

# 删除缓存
cache.delete("key")

# 查看统计
stats = cache.get_stats()
```

---

## 📐 缓存层级

### L1 缓存 (100 条)

- **速度**: 最快 (<1ms)
- **容量**: 100 条
- **用途**: 热点数据

### L2 缓存 (1000 条)

- **速度**: 快 (<5ms)
- **容量**: 1000 条
- **用途**: 常用数据

### L3 缓存 (10000 条)

- **速度**: 中等 (<10ms)
- **容量**: 10000 条
- **用途**: 一般数据

---

## 🤖 AI 元数据

本模块完全采用 AI 专用格式：

- `@module`, `@purpose` - 模块元数据
- `@schema` - Schema 定义
- `@class`, `@function` - 类和函数
- `@test_for` - 测试定义

AI 可以完全理解并自动生成代码、测试和文档。

---

*最后更新：2026-03-07*  
*状态：✅ 完成*
