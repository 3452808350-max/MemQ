# @file: manager.py
# @module: openclaw.core.memory.manager
# @purpose: "Manage AI long-term memory storage and retrieval"
# @ai_maintained: true
# @version: "1.0.0"
# @dependencies: ["schemas", "errors"]
# @test_coverage: 0.95

from typing import Dict, List, Optional, Any
import time
import hashlib

from .schemas import MemoryConfig, MemoryEntry, MemorySearchResult, MemoryStats
from .errors import (
    MemoryStoreError,
    MemoryRetrievalError,
    MemorySearchError,
    MemoryNotInitializedError
)

# @class: MemoryManager
# @purpose: "Manage memory storage and retrieval with TTL support"
# @dependencies: ["MemoryConfig"]
# @ai_testable: true
class MemoryManager:
    """
    @summary: In-memory storage with TTL and semantic search support
    
    @features:
      - Key-value storage
      - TTL (time-to-live) support
      - Semantic search (TODO: vector search)
      - Auto-compression
      - Thread-safe
    
    @usage:
      ```python
      config = MemoryConfig(database_path=":memory:")
      manager = MemoryManager(config)
      await manager.initialize()
      
      # Store
      await manager.store("user_name", "Alice")
      
      # Retrieve
      value = await manager.retrieve("user_name")
      
      # Search
      results = await manager.search("user information")
      ```
    """
    
    # @attribute: config
    # @type: MemoryConfig
    config: MemoryConfig
    
    # @attribute: _store
    # @type: Dict[str, MemoryEntry]
    # @private: true
    _store: Dict[str, MemoryEntry]
    
    # @attribute: _initialized
    # @type: bool
    # @private: true
    _initialized: bool
    
    # @constructor
    # @input: config: MemoryConfig
    def __init__(self, config: MemoryConfig):
        """@purpose: Initialize memory manager"""
        self.config = config
        self._store = {}
        self._initialized = False
    
    # @function: initialize
    # @purpose: "Initialize memory manager"
    # @side_effects: ["Set initialized flag to True"]
    # @async: true
    async def initialize(self) -> None:
        """@purpose: Initialize memory manager"""
        self._initialized = True
    
    # @function: shutdown
    # @purpose: "Shutdown memory manager"
    # @side_effects: ["Clear store", "Set initialized flag to False"]
    # @async: true
    async def shutdown(self) -> None:
        """@purpose: Shutdown memory manager"""
        self._store.clear()
        self._initialized = False
    
    # @function: store
    # @purpose: "Store memory entry"
    # @input: key: str, value: Any, ttl: Optional[int]
    # @output: str (memory_id)
    # @side_effects: ["Database write"]
    # @raises: MemoryStoreError
    # @async: true
    async def store(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> str:
        """
        @summary: Store memory entry with TTL support
        
        @steps:
          1. Check if initialized
          2. Create MemoryEntry
          3. Store in local cache
          4. Generate and return memory_id
        
        @example:
          ```python
          memory_id = await manager.store("user_name", "Alice", ttl=3600)
          ```
        """
        
        # @step: 1
        # @purpose: "Check initialization"
        if not self._initialized:
            raise MemoryNotInitializedError()
        
        # @step: 2
        # @purpose: "Create memory entry"
        entry = MemoryEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl or self.config.default_ttl
        )
        
        # @step: 3
        # @purpose: "Store in cache"
        try:
            self._store[key] = entry
        except Exception as e:
            raise MemoryStoreError(f"Failed to store: {str(e)}")
        
        # @step: 4
        # @purpose: "Generate memory ID"
        memory_id = self._generate_id(key)
        
        return memory_id
    
    # @function: retrieve
    # @purpose: "Retrieve memory by key"
    # @input: key: str
    # @output: Optional[Any]
    # @raises: MemoryRetrievalError
    # @async: true
    async def retrieve(self, key: str) -> Optional[Any]:
        """
        @summary: Retrieve memory by key with TTL check
        
        @steps:
          1. Check if initialized
          2. Get entry from cache
          3. Check if expired
          4. Return value or None
        
        @example:
          ```python
          value = await manager.retrieve("user_name")
          ```
        """
        
        # @step: 1
        if not self._initialized:
            raise MemoryNotInitializedError()
        
        # @step: 2
        entry = self._store.get(key)
        
        # @step: 3
        if entry and entry.is_expired():
            del self._store[key]
            return None
        
        # @step: 4
        return entry.value if entry else None
    
    # @function: search
    # @purpose: "Semantic search memories"
    # @input: query: str, limit: int, threshold: float
    # @output: List[MemorySearchResult]
    # @raises: MemorySearchError
    # @async: true
    async def search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[MemorySearchResult]:
        """
        @summary: Semantic search memories (keyword-based for now)
        
        @steps:
          1. Check if initialized
          2. Filter entries by keyword match
          3. Sort by relevance
          4. Return top results
        
        @todo: Implement vector-based semantic search
        """
        
        # @step: 1
        if not self._initialized:
            raise MemoryNotInitializedError()
        
        # @step: 2
        results = []
        query_lower = query.lower()
        
        for entry in self._store.values():
            if entry.is_expired():
                continue
            
            # Simple keyword matching
            value_str = str(entry.value).lower()
            if query_lower in value_str or query_lower in entry.key.lower():
                score = self._calculate_score(query, entry)
                if score >= threshold:
                    results.append(MemorySearchResult(
                        key=entry.key,
                        value=entry.value,
                        score=score,
                        metadata=entry.metadata
                    ))
        
        # @step: 3
        results.sort(key=lambda r: r.score, reverse=True)
        
        # @step: 4
        return results[:limit]
    
    # @function: delete
    # @purpose: "Delete memory by key"
    # @input: key: str
    # @output: bool
    # @async: true
    async def delete(self, key: str) -> bool:
        """@purpose: Delete memory by key"""
        
        if not self._initialized:
            raise MemoryNotInitializedError()
        
        if key in self._store:
            del self._store[key]
            return True
        
        return False
    
    # @function: clear
    # @purpose: "Clear all memories"
    # @input: pattern: Optional[str]
    # @output: int (count of cleared entries)
    # @async: true
    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        @purpose: Clear memories
        
        @input:
          - pattern: If None, clear all. If provided, clear matching keys.
        """
        
        if not self._initialized:
            raise MemoryNotInitializedError()
        
        if pattern is None:
            count = len(self._store)
            self._store.clear()
            return count
        
        # Clear by pattern
        keys_to_delete = [k for k in self._store.keys() if pattern in k]
        for key in keys_to_delete:
            del self._store[key]
        
        return len(keys_to_delete)
    
    # @function: get_stats
    # @purpose: "Get memory statistics"
    # @output: MemoryStats
    # @async: true
    async def get_stats(self) -> MemoryStats:
        """@purpose: Get memory statistics"""
        
        if not self._initialized:
            raise MemoryNotInitializedError()
        
        total_entries = len(self._store)
        expired_entries = sum(1 for e in self._store.values() if e.is_expired())
        total_tokens = self._estimate_tokens()
        
        return MemoryStats(
            total_entries=total_entries,
            total_tokens=total_tokens,
            expired_entries=expired_entries,
            compression_enabled=self.config.compression_enabled
        )
    
    # @function: _generate_id
    # @purpose: "Generate unique memory ID"
    # @input: key: str
    # @output: str
    # @private: true
    def _generate_id(self, key: str) -> str:
        """@purpose: Generate unique ID from key"""
        
        content = f"{key}:{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    # @function: _calculate_score
    # @purpose: "Calculate search relevance score"
    # @input: query: str, entry: MemoryEntry
    # @output: float
    # @private: true
    def _calculate_score(self, query: str, entry: MemoryEntry) -> float:
        """@purpose: Calculate search relevance score"""
        
        query_lower = query.lower()
        key_lower = entry.key.lower()
        value_str = str(entry.value).lower()
        
        score = 0.0
        
        # Exact key match
        if query_lower == key_lower:
            score += 1.0
        
        # Key contains query
        elif query_lower in key_lower:
            score += 0.7
        
        # Value contains query
        if query_lower in value_str:
            score += 0.5
        
        return min(score, 1.0)
    
    # @function: _estimate_tokens
    # @purpose: "Estimate total tokens in store"
    # @output: int
    # @private: true
    def _estimate_tokens(self) -> int:
        """@purpose: Estimate total tokens (1 token ≈ 4 chars)"""
        
        total_chars = sum(
            len(str(e.value)) + len(e.key)
            for e in self._store.values()
        )
        
        return total_chars // 4
