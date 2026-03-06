# @file: schemas.py
# @module: openclaw.core.memory.schemas
# @purpose: "Define memory-related data schemas"
# @ai_maintained: true
# @version: "1.0.0"
# @test_coverage: 0.95

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

# @schema: MemoryConfig
# @ai_readable: true
# @purpose: "Memory manager configuration"
@dataclass
class MemoryConfig:
    """
    @field: database_path - Path to database file
    @field: max_tokens - Maximum tokens before compression
    @field: compression_enabled - Whether to enable compression
    @field: compression_threshold - Threshold for auto-compression (0.0-1.0)
    @field: default_ttl - Default time-to-live in seconds
    """
    
    # @field: database_path
    # @type: str
    # @required: true
    # @example: "./data/memory.db"
    database_path: str
    
    # @field: max_tokens
    # @type: int
    # @default: 4000
    # @range: [1000, 200000]
    max_tokens: int = 4000
    
    # @field: compression_enabled
    # @type: bool
    # @default: true
    compression_enabled: bool = True
    
    # @field: compression_threshold
    # @type: float
    # @default: 0.8
    # @range: [0.5, 0.95]
    compression_threshold: float = 0.8
    
    # @field: default_ttl
    # @type: Optional[int]
    # @default: 3600
    default_ttl: Optional[int] = 3600

# @schema: MemoryEntry
# @ai_readable: true
# @purpose: "Single memory entry structure"
@dataclass
class MemoryEntry:
    """
    @field: key - Unique identifier
    @field: value - Stored value
    @field: embedding - Vector embedding for semantic search
    @field: metadata - Additional metadata
    @field: timestamp - Creation timestamp
    @field: ttl - Time-to-live in seconds (None = no expiry)
    """
    
    # @field: key
    # @type: str
    # @required: true
    key: str
    
    # @field: value
    # @type: Any
    # @required: true
    value: Any
    
    # @field: embedding
    # @type: Optional[List[float]]
    # @default: None
    embedding: Optional[List[float]] = None
    
    # @field: metadata
    # @type: Dict[str, Any]
    # @default: {}
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # @field: timestamp
    # @type: float
    # @default: time.time()
    timestamp: float = 0.0
    
    # @field: ttl
    # @type: Optional[int]
    # @default: None
    ttl: Optional[int] = None
    
    def is_expired(self) -> bool:
        """@purpose: Check if entry is expired"""
        if self.ttl is None:
            return False
        
        import time
        return time.time() - self.timestamp > self.ttl

# @schema: MemorySearchResult
# @ai_readable: true
# @purpose: "Memory search result structure"
@dataclass
class MemorySearchResult:
    """
    @field: key - Memory key
    @field: value - Memory value
    @field: score - Similarity score (0.0-1.0)
    @field: metadata - Additional metadata
    """
    
    # @field: key
    # @type: str
    key: str
    
    # @field: value
    # @type: Any
    value: Any
    
    # @field: score
    # @type: float
    # @range: [0.0, 1.0]
    score: float
    
    # @field: metadata
    # @type: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

# @schema: MemoryStats
# @ai_readable: true
# @purpose: "Memory statistics structure"
@dataclass
class MemoryStats:
    """
    @field: total_entries - Total number of entries
    @field: total_tokens - Estimated total tokens
    @field: expired_entries - Number of expired entries
    @field: compression_enabled - Whether compression is enabled
    """
    
    # @field: total_entries
    # @type: int
    total_entries: int
    
    # @field: total_tokens
    # @type: int
    total_tokens: int
    
    # @field: expired_entries
    # @type: int
    expired_entries: int
    
    # @field: compression_enabled
    # @type: bool
    compression_enabled: bool
