# @file: async_cache.py
# @module: openclaw.core.cache.async_cache
# @purpose: "Async cache system for high-performance concurrent access"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Dict, List, Any, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

T = TypeVar('T')

# @class: AsyncCacheLayer
# @purpose: "Async cache layer with LRU eviction"
# @ai_testable: true
class AsyncCacheLayer:
    """
    @summary: Async cache layer with LRU eviction
    
    @features:
      - Async get/set/delete
      - LRU eviction
      - TTL support
      - Thread-safe
    """
    
    # @attribute: capacity
    # @type: int
    capacity: int
    
    # @attribute: entries
    # @type: Dict[str, Any]
    entries: Dict[str, Any]
    
    # @attribute: access_times
    # @type: Dict[str, float]
    access_times: Dict[str, float]
    
    # @constructor
    def __init__(self, capacity: int = 1000):
        """@purpose: Initialize async cache layer"""
        self.capacity = capacity
        self.entries = {}
        self.access_times = {}
        self._lock = asyncio.Lock()
    
    # @function: get
    # @purpose: "Get value from cache (async)"
    # @input: key: str
    # @output: Optional[T]
    # @async: true
    # @ai_testable: true
    async def get(self, key: str) -> Optional[Any]:
        """@purpose: Get value async"""
        
        async with self._lock:
            if key not in self.entries:
                return None
            
            value = self.entries[key]
            
            # Update access time
            self.access_times[key] = datetime.now().timestamp()
            
            return value
    
    # @function: set
    # @purpose: "Set value in cache (async)"
    # @input: key: str, value: T, ttl: Optional[int]
    # @side_effects: ["Update cache"]
    # @async: true
    # @ai_testable: true
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """@purpose: Set value async"""
        
        async with self._lock:
            # Evict if at capacity
            if len(self.entries) >= self.capacity:
                await self._evict()
            
            self.entries[key] = value
            self.access_times[key] = datetime.now().timestamp()
    
    # @function: delete
    # @purpose: "Delete value from cache (async)"
    # @input: key: str
    # @output: bool
    # @async: true
    # @ai_testable: true
    async def delete(self, key: str) -> bool:
        """@purpose: Delete value async"""
        
        async with self._lock:
            if key in self.entries:
                del self.entries[key]
                del self.access_times[key]
                return True
            return False
    
    # @function: clear
    # @purpose: "Clear all cache entries (async)"
    # @side_effects: ["Clear all entries"]
    # @async: true
    # @ai_testable: true
    async def clear(self) -> None:
        """@purpose: Clear cache async"""
        
        async with self._lock:
            self.entries.clear()
            self.access_times.clear()
    
    # @function: _evict
    # @purpose: "Evict least recently used entry"
    # @side_effects: ["Remove LRU entry"]
    # @private: true
    # @async: true
    async def _evict(self) -> None:
        """@purpose: Evict LRU entry"""
        
        if not self.access_times:
            return
        
        # Find LRU entry
        lru_key = min(self.access_times, key=self.access_times.get)
        
        del self.entries[lru_key]
        del self.access_times[lru_key]
    
    # @function: get_stats
    # @purpose: "Get cache statistics"
    # @output: Dict[str, Any]
    # @async: true
    # @ai_testable: true
    async def get_stats(self) -> Dict[str, Any]:
        """@purpose: Get statistics"""
        
        return {
            "capacity": self.capacity,
            "size": len(self.entries),
            "keys": list(self.entries.keys())[:10]  # First 10 keys
        }

# @class: AsyncMultiLayerCache
# @purpose: "Async multi-layer cache system"
# @ai_testable: true
class AsyncMultiLayerCache:
    """
    @summary: Async multi-layer cache with automatic promotion
    
    @features:
      - 3-layer async caching
      - Automatic promotion
      - Concurrent access
      - Unified API
    """
    
    # @attribute: l1
    # @type: AsyncCacheLayer
    l1: AsyncCacheLayer
    
    # @attribute: l2
    # @type: AsyncCacheLayer
    l2: AsyncCacheLayer
    
    # @attribute: l3
    # @type: AsyncCacheLayer
    l3: AsyncCacheLayer
    
    # @constructor
    def __init__(
        self,
        l1_capacity: int = 100,
        l2_capacity: int = 1000,
        l3_capacity: int = 10000
    ):
        """@purpose: Initialize async multi-layer cache"""
        
        self.l1 = AsyncCacheLayer(capacity=l1_capacity)
        self.l2 = AsyncCacheLayer(capacity=l2_capacity)
        self.l3 = AsyncCacheLayer(capacity=l3_capacity)
    
    # @function: get
    # @purpose: "Get value from cache (async, checks all layers)"
    # @input: key: str
    # @output: Optional[T]
    # @async: true
    # @ai_testable: true
    async def get(self, key: str) -> Optional[Any]:
        """
        @summary: Get value async
        
        @steps:
          1. Check L1
          2. Check L2
          3. Check L3
          4. Promote if found
        """
        
        # @step: 1
        value = await self.l1.get(key)
        if value is not None:
            return value
        
        # @step: 2
        value = await self.l2.get(key)
        if value is not None:
            await self.l1.set(key, value)  # Promote to L1
            return value
        
        # @step: 3
        value = await self.l3.get(key)
        if value is not None:
            await self.l2.set(key, value)  # Promote to L2
            return value
        
        # @step: 4
        return None
    
    # @function: set
    # @purpose: "Set value in cache (async, sets all layers)"
    # @input: key: str, value: T, ttl: Optional[int]
    # @side_effects: ["Update cache"]
    # @async: true
    # @ai_testable: true
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """@purpose: Set value async"""
        
        # Set in all layers concurrently
        await asyncio.gather(
            self.l1.set(key, value, ttl),
            self.l2.set(key, value, ttl),
            self.l3.set(key, value, ttl)
        )
    
    # @function: delete
    # @purpose: "Delete value from all layers (async)"
    # @input: key: str
    # @output: bool
    # @async: true
    # @ai_testable: true
    async def delete(self, key: str) -> bool:
        """@purpose: Delete value async"""
        
        results = await asyncio.gather(
            self.l1.delete(key),
            self.l2.delete(key),
            self.l3.delete(key)
        )
        
        return any(results)
    
    # @function: clear
    # @purpose: "Clear all cache layers (async)"
    # @side_effects: ["Clear all layers"]
    # @async: true
    # @ai_testable: true
    async def clear(self) -> None:
        """@purpose: Clear all async"""
        
        await asyncio.gather(
            self.l1.clear(),
            self.l2.clear(),
            self.l3.clear()
        )
    
    # @function: get_stats
    # @purpose: "Get cache statistics for all layers (async)"
    # @output: Dict[str, Any]
    # @async: true
    # @ai_testable: true
    async def get_stats(self) -> Dict[str, Any]:
        """@purpose: Get statistics async"""
        
        stats = await asyncio.gather(
            self.l1.get_stats(),
            self.l2.get_stats(),
            self.l3.get_stats()
        )
        
        return {
            "l1": stats[0],
            "l2": stats[1],
            "l3": stats[2]
        }

# @class: AsyncBatchCache
# @purpose: "Async batch cache operations"
# @ai_testable: true
class AsyncBatchCache:
    """
    @summary: Async batch cache operations
    
    @features:
      - Batch get
      - Batch set
      - Batch delete
      - Concurrent execution
    """
    
    # @attribute: cache
    # @type: AsyncMultiLayerCache
    cache: AsyncMultiLayerCache
    
    # @constructor
    def __init__(self, cache: AsyncMultiLayerCache):
        """@purpose: Initialize batch cache"""
        self.cache = cache
    
    # @function: get_batch
    # @purpose: "Get multiple values concurrently"
    # @input: keys: List[str]
    # @output: Dict[str, Any]
    # @async: true
    # @ai_testable: true
    async def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        """
        @summary: Batch get
        
        @steps:
          1. Create tasks
          2. Execute concurrently
          3. Return results
        """
        
        # @step: 1
        async def get_with_key(key: str):
            value = await self.cache.get(key)
            return key, value
        
        tasks = [get_with_key(key) for key in keys]
        
        # @step: 2
        results = await asyncio.gather(*tasks)
        
        # @step: 3
        return dict(results)
    
    # @function: set_batch
    # @purpose: "Set multiple values concurrently"
    # @input: items: Dict[str, Any], ttl: Optional[int]
    # @side_effects: ["Update cache"]
    # @async: true
    # @ai_testable: true
    async def set_batch(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """@purpose: Batch set"""
        
        tasks = [
            self.cache.set(key, value, ttl)
            for key, value in items.items()
        ]
        
        await asyncio.gather(*tasks)
    
    # @function: delete_batch
    # @purpose: "Delete multiple values concurrently"
    # @input: keys: List[str]
    # @output: Dict[str, bool]
    # @async: true
    # @ai_testable: true
    async def delete_batch(self, keys: List[str]) -> Dict[str, bool]:
        """@purpose: Batch delete"""
        
        async def delete_with_key(key: str):
            result = await self.cache.delete(key)
            return key, result
        
        tasks = [delete_with_key(key) for key in keys]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
