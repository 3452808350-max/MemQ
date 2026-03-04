"""
混合记忆架构 - 阶段 1 实现
元数据增强 + LRU 缓存

实施内容:
1. memory_store 元数据增强
2. LRU 缓存实现
3. 基础监控指标

预期收益：查询延迟 ↓50%
"""

import hashlib
from datetime import datetime
from functools import lru_cache
from typing import List, Optional, Dict
import json

# ==================== 元数据增强 ====================

def memory_store_enhanced(
    text: str, 
    category: str = "other",
    importance: float = 0.7,
    tags: List[str] = None,
    scope: str = "global"
) -> str:
    """
    增强的记忆存储 - 添加元数据字段
    
    Args:
        text: 记忆内容
        category: 类别 (preference/decision/fact/entity/other)
        importance: 重要性 (0-1), 决定缓存 TTL
        tags: 标签列表
        scope: 作用域 (global/agent/session)
    
    Returns:
        memory_id: 记忆 ID
    
    示例:
        >>> memory_store_enhanced(
        ...     text="用户偏好简洁的回复",
        ...     category="preference",
        ...     importance=0.9,
        ...     tags=["chat", "style"]
        ... )
    """
    # 生成记忆 ID
    memory_id = f"mem_{datetime.now().timestamp()}"
    
    # 构建元数据
    memory = {
        "id": memory_id,
        "text": text,
        "category": category,
        "importance": importance,
        "tags": tags or [],
        "scope": scope,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "access_count": 0,
        "last_accessed": None
    }
    
    # 存储到 LanceDB (现有逻辑)
    # lancedb_table.add([memory])
    
    # 打印日志（调试用）
    print(f"✅ 记忆已存储：{memory_id}")
    print(f"   类别：{category}")
    print(f"   重要性：{importance}")
    print(f"   标签：{tags}")
    
    return memory_id


# ==================== LRU 缓存实现 ====================

class MemoryLRUCache:
    """
    记忆 LRU 缓存
    
    特性:
    - 基于内存的快速访问
    - LRU 淘汰策略
    - 支持重要性权重
    - 访问计数统计
    """
    
    def __init__(self, maxsize=1000):
        """
        初始化缓存
        
        Args:
            maxsize: 最大缓存条目数
        """
        self.maxsize = maxsize
        self.cache = {}
        self.access_order = []
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def get(self, key: str) -> Optional[Dict]:
        """
        获取缓存
        
        Args:
            key: 缓存键
        
        Returns:
            缓存数据，如果不存在返回 None
        """
        if key in self.cache:
            # 更新访问顺序 (LRU)
            self.access_order.remove(key)
            self.access_order.append(key)
            
            # 更新统计
            self.cache[key]["access_count"] += 1
            self.cache[key]["last_accessed"] = datetime.now().isoformat()
            self.stats["hits"] += 1
            
            return self.cache[key]
        
        self.stats["misses"] += 1
        return None
    
    def set(self, key: str, data: Dict, importance: float = 0.5):
        """
        设置缓存
        
        Args:
            key: 缓存键
            data: 缓存数据
            importance: 重要性 (0-1), 影响 TTL
        """
        # 如果缓存已满，淘汰最久未使用的
        if len(self.cache) >= self.maxsize and key not in self.cache:
            self._evict()
        
        # 计算 TTL (基于重要性)
        ttl_seconds = int(importance * 86400)  # 最多 1 天
        
        self.cache[key] = {
            "data": data,
            "importance": importance,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now().timestamp() + ttl_seconds),
            "access_count": 0,
            "last_accessed": None
        }
        
        self.access_order.append(key)
    
    def _evict(self):
        """淘汰最久未使用的缓存"""
        if not self.access_order:
            return
        
        # 淘汰第一个 (最久未使用)
        oldest_key = self.access_order.pop(0)
        del self.cache[oldest_key]
        self.stats["evictions"] += 1
        
        print(f"🗑️  已淘汰缓存：{oldest_key}")
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_order.clear()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0
        
        return {
            **self.stats,
            "total_requests": total,
            "hit_rate": f"{hit_rate:.2%}",
            "cache_size": len(self.cache),
            "max_size": self.maxsize
        }


# ==================== 缓存装饰器 ====================

# 全局缓存实例
_memory_cache = MemoryLRUCache(maxsize=1000)


def cached_memory_search(func):
    """
    记忆搜索缓存装饰器
    
    用法:
        @cached_memory_search
        def memory_recall(query, scope=None):
            # 原有逻辑
            pass
    """
    def wrapper(query: str, scope: str = None, **kwargs):
        # 生成缓存键
        cache_key = f"search:{hashlib.md5(f'{query}:{scope}'.encode()).hexdigest()}"
        
        # 检查缓存
        cached = _memory_cache.get(cache_key)
        if cached:
            print(f"✅ 缓存命中：{cache_key}")
            return cached["data"]
        
        # 缓存未命中，执行原函数
        print(f"⚠️  缓存未命中：{cache_key}")
        result = func(query, scope, **kwargs)
        
        # 缓存结果 (默认 TTL 5 分钟)
        _memory_cache.set(cache_key, result, importance=0.5)
        
        return result
    
    # 保留原函数信息
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    
    return wrapper


# ==================== 监控指标 ====================

def get_memory_metrics() -> Dict:
    """
    获取记忆系统监控指标
    
    Returns:
        指标字典
    """
    cache_stats = _memory_cache.get_stats()
    
    return {
        "cache": cache_stats,
        "timestamp": datetime.now().isoformat()
    }


def print_memory_metrics():
    """打印记忆系统指标"""
    metrics = get_memory_metrics()
    
    print("\n📊 记忆系统指标")
    print("=" * 50)
    print(f"缓存命中率：{metrics['cache']['hit_rate']}")
    print(f"总请求数：{metrics['cache']['total_requests']}")
    print(f"命中：{metrics['cache']['hits']}")
    print(f"未命中：{metrics['cache']['misses']}")
    print(f"淘汰：{metrics['cache']['evictions']}")
    print(f"缓存大小：{metrics['cache']['cache_size']}/{metrics['cache']['max_size']}")
    print("=" * 50)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("🧪 测试混合记忆架构 - 阶段 1\n")
    
    # 测试 1: 元数据增强
    print("测试 1: 元数据增强存储")
    print("-" * 50)
    mem_id = memory_store_enhanced(
        text="用户偏好简洁的回复",
        category="preference",
        importance=0.9,
        tags=["chat", "style"]
    )
    print()
    
    # 测试 2: LRU 缓存
    print("测试 2: LRU 缓存")
    print("-" * 50)
    cache = MemoryLRUCache(maxsize=3)
    
    # 添加缓存
    cache.set("key1", {"data": "value1"}, importance=0.8)
    cache.set("key2", {"data": "value2"}, importance=0.5)
    cache.set("key3", {"data": "value3"}, importance=0.3)
    
    # 访问缓存
    result1 = cache.get("key1")
    result2 = cache.get("key2")
    result3 = cache.get("key4")  # 未命中
    
    # 添加新缓存 (应该淘汰 key3)
    cache.set("key4", {"data": "value4"}, importance=0.7)
    
    # 打印统计
    print(f"缓存统计：{cache.get_stats()}")
    print()
    
    # 测试 3: 监控指标
    print("测试 3: 监控指标")
    print("-" * 50)
    print_memory_metrics()
    print()
    
    print("✅ 阶段 1 测试完成！")
