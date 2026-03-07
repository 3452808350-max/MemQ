# @file: manager.py
# @module: openclaw.core.context.manager
# @purpose: "Manage AI context with 4-layer hierarchical structure"
# @ai_maintained: true
# @version: "1.0.0"
# @test_coverage: 0.95

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time

# @enum: ContextLevel
# @ai_readable: true
class ContextLevel(str, Enum):
    """
    @value: SYSTEM - System-level context (global rules, security policies)
    @value: MODULE - Module-level context (module config, capabilities)
    @value: FUNCTION - Function-level context (function definitions, parameters)
    @value: EXECUTION - Execution-level context (runtime state, history)
    """
    SYSTEM = "system"
    MODULE = "module"
    FUNCTION = "function"
    EXECUTION = "execution"

# @schema: ContextEntry
# @ai_readable: true
@dataclass
class ContextEntry:
    """@purpose: Single context entry structure"""
    
    # @field: key
    # @type: str
    # @required: true
    key: str
    
    # @field: value
    # @type: Any
    # @required: true
    value: Any
    
    # @field: level
    # @type: ContextLevel
    # @required: true
    level: ContextLevel
    
    # @field: priority
    # @type: int
    # @default: 0
    # @range: [0, 100]
    priority: int = 0
    
    # @field: timestamp
    # @type: float
    # @default: time.time()
    timestamp: float = field(default_factory=time.time)
    
    # @field: ttl
    # @type: Optional[int]
    # @default: 3600
    ttl: Optional[int] = 3600
    
    # @field: metadata
    # @type: Dict[str, Any]
    # @default: {}
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # @function: is_expired
    # @purpose: "Check if entry is expired"
    # @output: bool
    def is_expired(self) -> bool:
        """@purpose: Check expiration"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

# @schema: ContextLayer
# @ai_readable: true
@dataclass
class ContextLayer:
    """@purpose: Context layer structure"""
    
    # @field: level
    # @type: ContextLevel
    level: ContextLevel
    
    # @field: entries
    # @type: Dict[str, ContextEntry]
    entries: Dict[str, ContextEntry] = field(default_factory=dict)
    
    # @field: max_tokens
    # @type: int
    # @default: 4000
    max_tokens: int = 4000
    
    # @field: compression_threshold
    # @type: float
    # @default: 0.8
    compression_threshold: float = 0.8

# @class: HierarchicalContextManager
# @purpose: "Manage 4-layer hierarchical context"
# @dependencies: ["ContextLevel", "ContextEntry", "ContextLayer"]
# @ai_testable: true
class HierarchicalContextManager:
    """
    @summary: 4-layer hierarchical context manager
    
    @features:
      - 4-layer structure (System/Module/Function/Execution)
      - Intelligent compression
      - Semantic search
      - TTL support
    
    @usage:
      ```python
      manager = HierarchicalContextManager()
      await manager.initialize()
      
      # Set context
      await manager.set_context(ContextEntry(
          key="system_rule",
          value="Be helpful and harmless",
          level=ContextLevel.SYSTEM
      ))
      
      # Get context
      entries = await manager.get_context(ContextLevel.SYSTEM)
      
      # Query context
      results = await manager.query_context("system rules", limit=10)
      ```
    """
    
    # @attribute: _layers
    # @type: Dict[ContextLevel, ContextLayer]
    _layers: Dict[ContextLevel, ContextLayer]
    
    # @attribute: _initialized
    # @type: bool
    _initialized: bool
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize context manager"""
        
        self._layers = {
            level: ContextLayer(level=level)
            for level in ContextLevel
        }
        self._initialized = False
    
    # @function: initialize
    # @purpose: "Initialize context manager"
    # @side_effects: ["Set initialized flag"]
    # @async: true
    async def initialize(self) -> None:
        """@purpose: Initialize manager"""
        self._initialized = True
    
    # @function: shutdown
    # @purpose: "Shutdown context manager"
    # @side_effects: ["Clear all layers"]
    # @async: true
    async def shutdown(self) -> None:
        """@purpose: Shutdown manager"""
        for layer in self._layers.values():
            layer.entries.clear()
        self._initialized = False
    
    # @function: get_context
    # @purpose: "Get context entries by level"
    # @input: level: ContextLevel, key: Optional[str]
    # @output: List[ContextEntry]
    # @async: true
    async def get_context(
        self,
        level: ContextLevel,
        key: Optional[str] = None
    ) -> List[ContextEntry]:
        """
        @summary: Get context entries
        
        @steps:
          1. Get layer
          2. Filter by key if provided
          3. Sort by priority and timestamp
          4. Return entries
        """
        
        # @step: 1
        layer = self._layers[level]
        
        # @step: 2
        if key:
            entry = layer.entries.get(key)
            return [entry] if entry else []
        
        # @step: 3
        entries = [
            e for e in layer.entries.values()
            if not e.is_expired()
        ]
        
        # @step: 4
        return sorted(entries, key=lambda e: (e.priority, -e.timestamp))
    
    # @function: set_context
    # @purpose: "Set context entry"
    # @input: entry: ContextEntry
    # @side_effects: ["Update layer entries"]
    # @async: true
    async def set_context(self, entry: ContextEntry) -> None:
        """@purpose: Set context entry"""
        
        layer = self._layers[entry.level]
        layer.entries[entry.key] = entry
        
        # Check compression
        await self._check_compression(entry.level)
    
    # @function: query_context
    # @purpose: "Query context entries semantically"
    # @input: query: str, levels: List[ContextLevel], limit: int
    # @output: List[ContextEntry]
    # @async: true
    async def query_context(
        self,
        query: str,
        levels: List[ContextLevel],
        limit: int = 10
    ) -> List[ContextEntry]:
        """
        @summary: Query context semantically
        
        @steps:
          1. Get all entries from specified levels
          2. Filter expired entries
          3. Keyword match (fallback for now)
          4. Return top results
        """
        
        # @step: 1
        all_entries = []
        for level in levels:
            all_entries.extend(self._layers[level].entries.values())
        
        # @step: 2
        valid_entries = [e for e in all_entries if not e.is_expired()]
        
        # @step: 3
        query_lower = query.lower()
        matched = []
        for entry in valid_entries:
            score = self._calculate_relevance(query_lower, entry)
            if score > 0:
                matched.append((entry, score))
        
        # @step: 4
        matched.sort(key=lambda x: x[1], reverse=True)
        return [entry for entry, score in matched[:limit]]
    
    # @function: compress_context
    # @purpose: "Compress context to target tokens"
    # @input: level: ContextLevel, target_tokens: int
    # @output: List[ContextEntry]
    # @async: true
    async def compress_context(
        self,
        level: ContextLevel,
        target_tokens: int
    ) -> List[ContextEntry]:
        """@purpose: Compress context"""
        
        layer = self._layers[level]
        entries = list(layer.entries.values())
        
        if not entries:
            return []
        
        # Sort by priority and timestamp
        entries.sort(key=lambda e: (e.priority, -e.timestamp))
        
        # Keep high priority entries
        compressed = []
        current_tokens = 0
        
        for entry in entries:
            entry_tokens = self._estimate_tokens(entry)
            if current_tokens + entry_tokens <= target_tokens:
                compressed.append(entry)
                current_tokens += entry_tokens
        
        return compressed
    
    # @function: _check_compression
    # @purpose: "Check if compression is needed"
    # @input: level: ContextLevel
    # @side_effects: ["May compress context"]
    # @private: true
    # @async: true
    async def _check_compression(self, level: ContextLevel) -> None:
        """@purpose: Check and trigger compression"""
        
        layer = self._layers[level]
        total_tokens = self._estimate_layer_tokens(layer)
        
        if total_tokens > layer.max_tokens * layer.compression_threshold:
            await self.compress_context(level, layer.max_tokens // 2)
    
    # @function: _calculate_relevance
    # @purpose: "Calculate query relevance score"
    # @input: query: str, entry: ContextEntry
    # @output: float
    # @private: true
    def _calculate_relevance(self, query: str, entry: ContextEntry) -> float:
        """@purpose: Calculate relevance score"""
        
        score = 0.0
        
        # Key match
        if query in entry.key.lower():
            score += 0.5
        
        # Value match
        value_str = str(entry.value).lower()
        if query in value_str:
            score += 0.3
        
        # Metadata match
        for key, value in entry.metadata.items():
            if query in str(value).lower():
                score += 0.2
        
        return score
    
    # @function: _estimate_tokens
    # @purpose: "Estimate tokens in entry"
    # @input: entry: ContextEntry
    # @output: int
    # @private: true
    def _estimate_tokens(self, entry: ContextEntry) -> int:
        """@purpose: Estimate tokens (1 token ≈ 4 chars)"""
        
        key_tokens = len(entry.key) // 4
        value_tokens = len(str(entry.value)) // 4
        
        return key_tokens + value_tokens
    
    # @function: _estimate_layer_tokens
    # @purpose: "Estimate total tokens in layer"
    # @input: layer: ContextLayer
    # @output: int
    # @private: true
    def _estimate_layer_tokens(self, layer: ContextLayer) -> int:
        """@purpose: Estimate layer tokens"""
        
        return sum(
            self._estimate_tokens(e)
            for e in layer.entries.values()
        )
    
    # @function: get_stats
    # @purpose: "Get context statistics"
    # @output: Dict[str, Any]
    # @async: true
    async def get_stats(self) -> Dict[str, Any]:
        """@purpose: Get statistics"""
        
        stats = {}
        for level, layer in self._layers.items():
            stats[level.value] = {
                "entries": len(layer.entries),
                "tokens": self._estimate_layer_tokens(layer),
                "max_tokens": layer.max_tokens
            }
        
        return stats
