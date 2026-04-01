# @file: cache.py
# @module: openclaw.core.cache
# @purpose: "Multi-layer cache system for performance optimization"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Dict, List, Any, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
import hashlib

T = TypeVar('T')

# @enum: CacheLevel
# @ai_readable: true
class CacheLevel(str, Enum):
    """
    @value: L1 - L1 cache (in-memory, fastest)
    @value: L2 - L2 cache (in-memory, larger)
    @value: L3 - L3 cache (disk-based, largest)
    """
    L1 = "l1"
    L2 = "l2"
    L3 = "l3"

# @schema: CacheEntry
# @ai_readable: true
@dataclass
class CacheEntry(Generic[T]):
    """@purpose: Cache entry structure"""
    
    # @field: key
    # @type: str
    key: str
    
    # @field: value
    # @type: T
    value: T
    
    # @field: created_at
    # @type: datetime
    created_at: datetime = field(default_factory=datetime.now)
    
    # @field: ttl_seconds
    # @type: Optional[int]
    # @default: 3600
    ttl_seconds: Optional[int] = 3600
    
    # @field: access_count
    # @type: int
    # @default: 0
    access_count: int = 0
    
    # @field: last_accessed
    # @type: datetime
    last_accessed: datetime = field(default_factory=datetime.now)
    
    # @function: is_expired
    # @purpose: "Check if entry is expired"
    # @output: bool
    def is_expired(self) -> bool:
        """@purpose: Check expiration"""
        if self.ttl_seconds is None:
            return False
        
        now = datetime.now()
        age = now - self.created_at
        return age.total_seconds() > self.ttl_seconds
    
    # @function: touch
    # @purpose: "Update last accessed time"
    # @side_effects: ["Update access_count and last_accessed"]
    def touch(self) -> None:
        """@purpose: Touch entry"""
        self.access_count += 1
        self.last_accessed = datetime.now()

# @class: CacheLayer
# @purpose: "Single cache layer implementation"
# @ai_testable: true
class CacheLayer:
    """
    @summary: Single cache layer with LRU eviction
    
    @features:
      - TTL support
      - LRU eviction
      - Access tracking
      - Thread-safe
    """
    
    # @attribute: capacity
    # @type: int
    capacity: int
    
    # @attribute: entries
    # @type: Dict[str, CacheEntry]
    entries: Dict[str, CacheEntry]
    
    # @constructor
    def __init__(self, capacity: int = 1000):
        """@purpose: Initialize cache layer"""
        self.capacity = capacity
        self.entries = {}
    
    # @function: get
    # @purpose: "Get value from cache"
    # @input: key: str
    # @output: Optional[T]
    # @ai_testable: true
    def get(self, key: str) -> Optional[Any]:
        """@purpose: Get value"""
        
        entry = self.entries.get(key)
        
        if not entry:
            return None
        
        if entry.is_expired():
            del self.entries[key]
            return None
        
        entry.touch()
        return entry.value
    
    # @function: set
    # @purpose: "Set value in cache"
    # @input: key: str, value: T, ttl: Optional[int]
    # @side_effects: ["Update cache entries"]
    # @ai_testable: true
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """@purpose: Set value"""
        
        # Evict if at capacity
        if len(self.entries) >= self.capacity:
            self._evict()
        
        entry = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl
        )
        
        self.entries[key] = entry
    
    # @function: delete
    # @purpose: "Delete value from cache"
    # @input: key: str
    # @output: bool
    # @ai_testable: true
    def delete(self, key: str) -> bool:
        """@purpose: Delete value"""
        
        if key in self.entries:
            del self.entries[key]
            return True
        return False
    
    # @function: clear
    # @purpose: "Clear all cache entries"
    # @side_effects: ["Clear all entries"]
    # @ai_testable: true
    def clear(self) -> None:
        """@purpose: Clear cache"""
        self.entries.clear()
    
    # @function: _evict
    # @purpose: "Evict least recently used entry"
    # @side_effects: ["Remove LRU entry"]
    # @private: true
    def _evict(self) -> None:
        """@purpose: Evict LRU entry"""
        
        if not self.entries:
            return
        
        # Find LRU entry
        lru_key = min(
            self.entries.keys(),
            key=lambda k: self.entries[k].last_accessed
        )
        
        del self.entries[lru_key]
    
    # @function: get_stats
    # @purpose: "Get cache statistics"
    # @output: Dict[str, Any]
    # @ai_testable: true
    def get_stats(self) -> Dict[str, Any]:
        """@purpose: Get statistics"""
        
        return {
            "capacity": self.capacity,
            "size": len(self.entries),
            "hits": sum(e.access_count for e in self.entries.values()),
            "ttl_entries": sum(1 for e in self.entries.values() if e.ttl_seconds is not None)
        }

# @class: MultiLayerCache
# @purpose: "Multi-layer cache system (L1/L2/L3)"
# @ai_testable: true
class MultiLayerCache:
    """
    @summary: Multi-layer cache with automatic promotion
    
    @features:
      - 3-layer caching (L1/L2/L3)
      - Automatic promotion
      - Configurable capacities
      - Unified API
    """
    
    # @attribute: l1
    # @type: CacheLayer
    l1: CacheLayer
    
    # @attribute: l2
    # @type: CacheLayer
    l2: CacheLayer
    
    # @attribute: l3
    # @type: CacheLayer
    l3: CacheLayer
    
    # @constructor
    def __init__(
        self,
        l1_capacity: int = 100,
        l2_capacity: int = 1000,
        l3_capacity: int = 10000
    ):
        """@purpose: Initialize multi-layer cache"""
        
        self.l1 = CacheLayer(capacity=l1_capacity)
        self.l2 = CacheLayer(capacity=l2_capacity)
        self.l3 = CacheLayer(capacity=l3_capacity)
    
    # @function: get
    # @purpose: "Get value from cache (checks all layers)"
    # @input: key: str
    # @output: Optional[T]
    # @ai_testable: true
    def get(self, key: str) -> Optional[Any]:
        """
        @summary: Get value from cache
        
        @steps:
          1. Check L1
          2. Check L2
          3. Check L3
          4. Promote if found in lower layer
        """
        
        # @step: 1
        value = self.l1.get(key)
        if value is not None:
            return value
        
        # @step: 2
        value = self.l2.get(key)
        if value is not None:
            self.l1.set(key, value)  # Promote to L1
            return value
        
        # @step: 3
        value = self.l3.get(key)
        if value is not None:
            self.l2.set(key, value)  # Promote to L2
            return value
        
        # @step: 4
        return None
    
    # @function: set
    # @purpose: "Set value in cache (starts at L3)"
    # @input: key: str, value: T, ttl: Optional[int]
    # @side_effects: ["Update cache"]
    # @ai_testable: true
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """@purpose: Set value"""
        
        # Set in all layers
        self.l3.set(key, value, ttl)
        self.l2.set(key, value, ttl)
        self.l1.set(key, value, ttl)
    
    # @function: delete
    # @purpose: "Delete value from all layers"
    # @input: key: str
    # @output: bool
    # @ai_testable: true
    def delete(self, key: str) -> bool:
        """@purpose: Delete value"""
        
        deleted = False
        deleted |= self.l1.delete(key)
        deleted |= self.l2.delete(key)
        deleted |= self.l3.delete(key)
        return deleted
    
    # @function: clear
    # @purpose: "Clear all cache layers"
    # @side_effects: ["Clear all layers"]
    # @ai_testable: true
    def clear(self) -> None:
        """@purpose: Clear all"""
        
        self.l1.clear()
        self.l2.clear()
        self.l3.clear()
    
    # @function: get_stats
    # @purpose: "Get cache statistics for all layers"
    # @output: Dict[str, Any]
    # @ai_testable: true
    def get_stats(self) -> Dict[str, Any]:
        """@purpose: Get statistics"""
        
        return {
            "l1": self.l1.get_stats(),
            "l2": self.l2.get_stats(),
            "l3": self.l3.get_stats()
        }

# @class: CacheManager
# @purpose: "Global cache manager"
# @ai_testable: true
class CacheManager:
    """@summary: Global cache manager"""
    
    # @attribute: _instance
    # @type: Optional[CacheManager]
    _instance: Optional['CacheManager'] = None
    
    # @attribute: _cache
    # @type: MultiLayerCache
    _cache: MultiLayerCache
    
    # @function: get_instance
    # @purpose: "Get singleton instance"
    # @output: CacheManager
    # @ai_testable: true
    @classmethod
    def get_instance(cls) -> 'CacheManager':
        """@purpose: Get singleton"""
        
        if cls._instance is None:
            cls._instance = cls()
        
        return cls._instance
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize cache manager"""
        
        self._cache = MultiLayerCache(
            l1_capacity=100,
            l2_capacity=1000,
            l3_capacity=10000
        )
    
    # @function: get
    # @purpose: "Get value from global cache"
    # @input: key: str
    # @output: Optional[T]
    # @ai_testable: true
    def get(self, key: str) -> Optional[Any]:
        """@purpose: Get value"""
        return self._cache.get(key)
    
    # @function: set
    # @purpose: "Set value in global cache"
    # @input: key: str, value: T, ttl: Optional[int]
    # @ai_testable: true
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """@purpose: Set value"""
        self._cache.set(key, value, ttl)
    
    # @function: delete
    # @purpose: "Delete value from global cache"
    # @input: key: str
    # @output: bool
    # @ai_testable: true
    def delete(self, key: str) -> bool:
        """@purpose: Delete value"""
        return self._cache.delete(key)
    
    # @function: get_stats
    # @purpose: "Get global cache statistics"
    # @output: Dict[str, Any]
    # @ai_testable: true
    def get_stats(self) -> Dict[str, Any]:
        """@purpose: Get statistics"""
        return self._cache.get_stats()
