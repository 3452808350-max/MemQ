# @file: temporal_index.py
# @module: openclaw.core.index.temporal_index
# @purpose: "Temporal index for time-range queries"
# @ai_maintained: true
# @version: "1.0.0"

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

# @schema: TemporalItem
# @ai_readable: true
@dataclass
class TemporalItem:
    """@purpose: Temporal index item"""
    
    # @field: id
    # @type: str
    id: str
    
    # @field: timestamp
    # @type: datetime
    timestamp: datetime
    
    # @field: metadata
    # @type: Dict[str, any]
    metadata: Dict[str, any] = field(default_factory=dict)

# @class: TemporalIndex
# @purpose: "Temporal index for time-range queries"
# @ai_testable: true
class TemporalIndex:
    """
    @summary: Temporal index
    
    @features:
      - Time-range queries
      - Efficient time-based filtering
      - Automatic time bucketing
    """
    
    # @attribute: items
    # @type: Dict[str, TemporalItem]
    items: Dict[str, TemporalItem]
    
    # @attribute: time_buckets
    # @type: Dict[str, List[str]]
    time_buckets: Dict[str, List[str]]
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize index"""
        
        self.items = {}
        self.time_buckets = defaultdict(list)
    
    # @function: add
    # @purpose: "Add item to temporal index"
    # @input: id: str, timestamp: datetime, metadata: Dict
    # @side_effects: ["Add item to index"]
    # @ai_testable: true
    def add(
        self,
        id: str,
        timestamp: datetime,
        metadata: Dict = None
    ) -> None:
        """@purpose: Add item"""
        
        item = TemporalItem(id=id, timestamp=timestamp, metadata=metadata or {})
        self.items[id] = item
        
        # Add to time bucket (by date)
        bucket_key = timestamp.strftime('%Y-%m-%d')
        self.time_buckets[bucket_key].append(id)
    
    # @function: search
    # @purpose: "Time-range search"
    # @input: start: datetime, end: datetime, limit: int
    # @output: List[Tuple[str, datetime]]
    # @ai_testable: true
    def search(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Tuple[str, datetime]]:
        """
        @summary: Time-range search
        
        @steps:
          1. Filter by time range
          2. Sort by timestamp
          3. Return limited results
        """
        
        # @step: 1
        results = []
        
        for id, item in self.items.items():
            # Check time range
            if start and item.timestamp < start:
                continue
            
            if end and item.timestamp > end:
                continue
            
            results.append((id, item.timestamp))
        
        # @step: 2
        results.sort(key=lambda x: x[1], reverse=True)
        
        # @step: 3
        return results[:limit]
    
    # @function: get_recent
    # @purpose: "Get recent items"
    # @input: limit: int
    # @output: List[Tuple[str, datetime]]
    # @ai_testable: true
    def get_recent(self, limit: int = 10) -> List[Tuple[str, datetime]]:
        """@purpose: Get recent items"""
        
        return self.search(limit=limit)
    
    # @function: remove
    # @purpose: "Remove item from index"
    # @input: id: str
    # @output: bool
    # @ai_testable: true
    def remove(self, id: str) -> bool:
        """@purpose: Remove item"""
        
        if id not in self.items:
            return False
        
        # Remove from time buckets
        timestamp = self.items[id].timestamp
        bucket_key = timestamp.strftime('%Y-%m-%d')
        
        if id in self.time_buckets[bucket_key]:
            self.time_buckets[bucket_key].remove(id)
        
        # Remove item
        del self.items[id]
        
        return True
    
    # @function: clear
    # @purpose: "Clear index"
    # @side_effects: ["Clear index"]
    # @ai_testable: true
    def clear(self) -> None:
        """@purpose: Clear index"""
        
        self.items.clear()
        self.time_buckets.clear()
    
    # @function: get_stats
    # @purpose: "Get index statistics"
    # @output: Dict[str, any]
    # @ai_testable: true
    def get_stats(self) -> Dict[str, any]:
        """@purpose: Get statistics"""
        
        if not self.items:
            return {
                "total_items": 0,
                "date_range": None
            }
        
        timestamps = [item.timestamp for item in self.items.values()]
        
        return {
            "total_items": len(self.items),
            "earliest": min(timestamps),
            "latest": max(timestamps),
            "date_range": f"{min(timestamps).date()} to {max(timestamps).date()}"
        }
