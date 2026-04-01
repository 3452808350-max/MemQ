# 📚 OpenClaw 记忆读写时机策略

> **设计时间**: 2026-03-08  
> **状态**: ✅ 完成  
> **版本**: 1.0

---

## 🎯 核心原则

### 写入时机 (When to Write)

| 场景 | 时机 | 优先级 |
|------|------|--------|
| **用户明确要求** | 立即写入 | 🔴 高 |
| **重要对话结束** | 会话结束时 | 🔴 高 |
| **关键信息** | 识别后立即 | 🔴 高 |
| **定期总结** | 每 10 轮对话 | 🟡 中 |
| **上下文压缩** | 超过阈值时 | 🟡 中 |

---

### 读取时机 (When to Read)

| 场景 | 时机 | 优先级 |
|------|------|--------|
| **用户提问** | 立即读取 | 🔴 高 |
| **上下文相关** | 检测到相关话题 | 🔴 高 |
| **定期回顾** | 每 5 轮对话 | 🟡 中 |
| **上下文不足** | 需要更多信息 | 🟡 中 |

---

## 📊 记忆写入策略

### 1. 立即写入 (Immediate Write)

**触发条件**:
- 用户明确说"记住..."
- 用户说"这是重要的..."
- 检测到关键信息 (姓名、偏好、重要日期)

**示例**:
```python
if user_says("记住我的生日是 3 月 15 日"):
    memory.write(
        content="用户生日：3 月 15 日",
        category="preference",
        importance=0.9,
        immediate=True  # 立即写入
    )
```

---

### 2. 会话结束写入 (Session End Write)

**触发条件**:
- 会话结束
- 话题转换
- 用户离开

**示例**:
```python
@on_session_end
def save_session_summary():
    summary = generate_session_summary()
    memory.write(
        content=summary,
        category="session_summary",
        importance=0.7,
        immediate=False  # 可以批量写入
    )
```

---

### 3. 定期总结写入 (Periodic Summary)

**触发条件**:
- 每 10 轮对话
- 每 30 分钟
- 上下文超过阈值

**示例**:
```python
@on_every_n_turns(10)
def periodic_summary():
    if conversation_turns % 10 == 0:
        summary = summarize_recent_conversation()
        memory.write(
            content=summary,
            category="periodic_summary",
            importance=0.6
        )
```

---

### 4. 重要性阈值写入 (Importance Threshold)

**触发条件**:
- 重要性 > 0.8: 立即写入
- 重要性 0.5-0.8: 批量写入
- 重要性 < 0.5: 丢弃或延迟

**示例**:
```python
def write_with_priority(content, importance):
    if importance > 0.8:
        memory.write(content, importance=importance, immediate=True)
    elif importance > 0.5:
        batch_queue.append(content)
        if len(batch_queue) >= 10:
            memory.write_batch(batch_queue)
    else:
        # 低重要性，可选择丢弃
        pass
```

---

## 📖 记忆读取策略

### 1. 问题触发读取 (Question Trigger)

**触发条件**:
- 用户提问
- 用户提到"我记得..."
- 用户提到之前的对话

**示例**:
```python
if user_asks_question():
    # 从记忆中检索相关信息
    relevant_memories = memory.search(
        query=user_question,
        top_k=5,
        min_importance=0.5
    )
    
    # 注入到上下文
    context.inject(relevant_memories)
```

---

### 2. 话题相关读取 (Topic Relevant)

**触发条件**:
- 检测到特定话题
- 话题转换
- 关键词匹配

**示例**:
```python
@on_topic_detected("股票")
def load_stock_memory():
    memories = memory.search_by_topic("stock", top_k=3)
    context.inject(memories)
```

---

### 3. 定期回顾读取 (Periodic Review)

**触发条件**:
- 每 5 轮对话
- 每 15 分钟
- 上下文不足时

**示例**:
```python
@on_every_n_turns(5)
def periodic_review():
    # 回顾最近的重要记忆
    recent_memories = memory.search_by_time(
        since="last_5_turns",
        min_importance=0.7
    )
    
    if recent_memories:
        context.inject(recent_memories)
```

---

### 4. 上下文不足读取 (Context Insufficient)

**触发条件**:
- 当前上下文 token < 阈值
- 需要更多信息
- 用户要求回忆

**示例**:
```python
if context.token_count < 1000:
    # 从记忆中补充相关上下文
    additional_context = memory.search(
        query=current_topic,
        top_k=3,
        min_importance=0.6
    )
    context.inject(additional_context)
```

---

## 🎯 上下文压缩策略

### 触发条件

| 条件 | 阈值 | 操作 |
|------|------|------|
| **Token 数** | > 4000 | 压缩旧对话 |
| **对话轮数** | > 20 轮 | 总结早期对话 |
| **时间跨度** | > 30 分钟 | 总结早期对话 |
| **重要性低** | < 0.3 | 丢弃或压缩 |

---

### 压缩策略

```python
def compress_context():
    # 1. 识别可压缩的部分
    compressible = context.get_items_by_importance(max_importance=0.3)
    
    # 2. 生成摘要
    if len(compressible) > 5:
        summary = generate_summary(compressible)
        
        # 3. 写入记忆
        memory.write(
            content=summary,
            category="context_summary",
            importance=0.5
        )
        
        # 4. 从上下文移除
        context.remove(compressible)
```

---

## 📊 完整流程图

```
用户输入
  ↓
检测意图
  ↓
┌─────────────────┐
│ 需要写入记忆？   │
└─────────────────┘
  ↓ 是
检查重要性
  ↓
┌─────────────────┐
│ 重要性 > 0.8？   │─── 是 ───> 立即写入
└─────────────────┘
  ↓ 否
┌─────────────────┐
│ 重要性 > 0.5？   │─── 是 ───> 批量写入
└─────────────────┘
  ↓ 否
丢弃或延迟

---

用户提问
  ↓
检测相关性
  ↓
┌─────────────────┐
│ 有相关记忆？     │─── 是 ───> 读取并注入
└─────────────────┘
  ↓ 否
使用当前上下文

---

检查上下文
  ↓
┌─────────────────┐
│ Token > 4000？   │─── 是 ───> 压缩旧对话
└─────────────────┘
  ↓ 否
保持不变
```

---

## 🎯 实现示例

### 记忆管理器

```python
class MemoryManager:
    def __init__(self):
        self.write_queue = []
        self.importance_threshold_immediate = 0.8
        self.importance_threshold_batch = 0.5
    
    def write(self, content, importance=0.5, immediate=False):
        """写入记忆"""
        if immediate or importance > self.importance_threshold_immediate:
            self._immediate_write(content, importance)
        elif importance > self.importance_threshold_batch:
            self._batch_write(content, importance)
        else:
            self._low_priority_write(content, importance)
    
    def _immediate_write(self, content, importance):
        """立即写入"""
        print(f"📝 立即写入 (重要性：{importance})")
        # 实际写入逻辑
        pass
    
    def _batch_write(self, content, importance):
        """批量写入"""
        self.write_queue.append((content, importance))
        if len(self.write_queue) >= 10:
            self._flush_batch()
    
    def _flush_batch(self):
        """刷新批量队列"""
        print(f"📝 批量写入 {len(self.write_queue)} 条记忆")
        self.write_queue.clear()
    
    def read(self, query, top_k=5):
        """读取记忆"""
        print(f"📖 读取记忆：{query}")
        # 实际读取逻辑
        pass
```

---

### 上下文管理器

```python
class ContextManager:
    def __init__(self, max_tokens=4000):
        self.max_tokens = max_tokens
        self.current_tokens = 0
        self.memory_manager = MemoryManager()
    
    def add(self, content):
        """添加内容到上下文"""
        tokens = count_tokens(content)
        
        # 检查是否需要压缩
        if self.current_tokens + tokens > self.max_tokens:
            self.compress()
        
        self.context.append(content)
        self.current_tokens += tokens
    
    def compress(self):
        """压缩上下文"""
        # 找出低重要性内容
        compressible = [
            item for item in self.context
            if item.importance < 0.3
        ]
        
        if compressible:
            # 生成摘要
            summary = self.generate_summary(compressible)
            
            # 写入记忆
            self.memory_manager.write(
                content=summary,
                category="context_summary",
                importance=0.5
            )
            
            # 从上下文移除
            for item in compressible:
                self.context.remove(item)
```

---

## 📊 性能优化

### 批量写入优化

```python
# 配置
BATCH_SIZE = 10
BATCH_TIMEOUT = 300  # 5 分钟

# 定时器刷新
async def auto_flush():
    while True:
        await asyncio.sleep(BATCH_TIMEOUT)
        if write_queue:
            memory_manager._flush_batch()
```

---

### 缓存优化

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_memory_search(query_hash):
    """缓存搜索结果"""
    return memory.search(query_hash)
```

---

## 🎊 总结

### 写入时机

| 时机 | 触发条件 | 优先级 |
|------|---------|--------|
| **立即写入** | 用户明确要求、重要性>0.8 | 🔴 高 |
| **批量写入** | 重要性 0.5-0.8、队列满 | 🟡 中 |
| **延迟写入** | 重要性<0.5 | 🟢 低 |

---

### 读取时机

| 时机 | 触发条件 | 优先级 |
|------|---------|--------|
| **问题触发** | 用户提问 | 🔴 高 |
| **话题相关** | 检测到相关话题 | 🔴 高 |
| **定期回顾** | 每 5 轮对话 | 🟡 中 |
| **上下文不足** | Token<阈值 | 🟡 中 |

---

### 压缩时机

| 条件 | 阈值 | 操作 |
|------|------|------|
| **Token 数** | >4000 | 压缩 |
| **对话轮数** | >20 轮 | 总结 |
| **时间跨度** | >30 分钟 | 总结 |

---

**设计完成！可以开始实现了！** 🚀
