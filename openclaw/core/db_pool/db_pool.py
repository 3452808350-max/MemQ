# @file: db_pool.py
# @module: openclaw.core.db_pool
# @purpose: "Database connection pool for optimized database access"
# @ai_maintained: true
# @version: "1.0.0"

from typing import Optional, Any, Dict, List
from dataclasses import dataclass
from datetime import datetime
import asyncio
import sqlite3

# @schema: PoolConfig
# @ai_readable: true
@dataclass
class PoolConfig:
    """@purpose: Database pool configuration"""
    
    # @field: database_path
    # @type: str
    database_path: str = ":memory:"
    
    # @field: max_connections
    # @type: int
    # @default: 10
    max_connections: int = 10
    
    # @field: min_connections
    # @type: int
    # @default: 2
    min_connections: int = 2
    
    # @field: max_idle_time
    # @type: int
    # @default: 300
    max_idle_time: int = 300  # seconds

# @class: DatabaseConnection
# @purpose: "Wrapper for database connection"
# @ai_testable: true
class DatabaseConnection:
    """@summary: Database connection wrapper"""
    
    # @attribute: conn
    # @type: sqlite3.Connection
    conn: sqlite3.Connection
    
    # @attribute: created_at
    # @type: datetime
    created_at: datetime
    
    # @attribute: last_used
    # @type: datetime
    last_used: datetime
    
    # @attribute: in_use
    # @type: bool
    in_use: bool
    
    # @constructor
    def __init__(self, database_path: str):
        """@purpose: Initialize connection"""
        self.conn = sqlite3.connect(database_path, check_same_thread=False)
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.in_use = False
    
    # @function: execute
    # @purpose: "Execute SQL query"
    # @input: query: str, params: Optional[Tuple]
    # @output: List[Dict[str, Any]]
    # @async: true
    # @ai_testable: true
    async def execute(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """@purpose: Execute query async"""
        
        def _execute():
            self.last_used = datetime.now()
            cursor = self.conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                columns = [desc[0] for desc in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                return results
            else:
                self.conn.commit()
                return []
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _execute)
    
    # @function: close
    # @purpose: "Close connection"
    # @side_effects: ["Close connection"]
    # @ai_testable: true
    def close(self) -> None:
        """@purpose: Close connection"""
        self.conn.close()

# @class: DatabasePool
# @purpose: "Database connection pool manager"
# @ai_testable: true
class DatabasePool:
    """
    @summary: Database connection pool with automatic management
    
    @features:
      - Connection pooling
      - Automatic scaling
      - Idle connection cleanup
      - Thread-safe
    """
    
    # @attribute: config
    # @type: PoolConfig
    config: PoolConfig
    
    # @attribute: connections
    # @type: List[DatabaseConnection]
    connections: List[DatabaseConnection]
    
    # @attribute: _lock
    # @type: asyncio.Lock
    _lock: asyncio.Lock
    
    # @constructor
    def __init__(self, config: Optional[PoolConfig] = None):
        """@purpose: Initialize database pool"""
        
        self.config = config or PoolConfig()
        self.connections = []
        self._lock = asyncio.Lock()
    
    # @function: initialize
    # @purpose: "Initialize connection pool"
    # @side_effects: ["Create initial connections"]
    # @async: true
    # @ai_testable: true
    async def initialize(self) -> None:
        """
        @summary: Initialize pool
        
        @steps:
          1. Create minimum connections
          2. Add to pool
        """
        
        # @step: 1
        for _ in range(self.config.min_connections):
            conn = DatabaseConnection(self.config.database_path)
            self.connections.append(conn)
    
    # @function: acquire
    # @purpose: "Acquire connection from pool"
    # @output: DatabaseConnection
    # @async: true
    # @ai_testable: true
    async def acquire(self) -> DatabaseConnection:
        """
        @summary: Acquire connection
        
        @steps:
          1. Find available connection
          2. Create new if needed
          3. Mark as in use
        """
        
        async with self._lock:
            # @step: 1
            for conn in self.connections:
                if not conn.in_use:
                    conn.in_use = True
                    return conn
            
            # @step: 2
            if len(self.connections) < self.config.max_connections:
                conn = DatabaseConnection(self.config.database_path)
                conn.in_use = True
                self.connections.append(conn)
                return conn
            
            # Wait for available connection
            await asyncio.sleep(0.1)
            return await self.acquire()
    
    # @function: release
    # @purpose: "Release connection back to pool"
    # @input: conn: DatabaseConnection
    # @side_effects: ["Mark connection as available"]
    # @async: true
    # @ai_testable: true
    async def release(self, conn: DatabaseConnection) -> None:
        """@purpose: Release connection"""
        
        async with self._lock:
            conn.in_use = False
            conn.last_used = datetime.now()
    
    # @function: execute
    # @purpose: "Execute query using pooled connection"
    # @input: query: str, params: Optional[Tuple]
    # @output: List[Dict[str, Any]]
    # @async: true
    # @ai_testable: true
    async def execute(
        self,
        query: str,
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        @summary: Execute query
        
        @steps:
          1. Acquire connection
          2. Execute query
          3. Release connection
        """
        
        # @step: 1
        conn = await self.acquire()
        
        try:
            # @step: 2
            result = await conn.execute(query, params)
            return result
        finally:
            # @step: 3
            await self.release(conn)
    
    # @function: cleanup_idle
    # @purpose: "Cleanup idle connections"
    # @side_effects: ["Remove idle connections"]
    # @async: true
    # @ai_testable: true
    async def cleanup_idle(self) -> None:
        """@purpose: Cleanup idle connections"""
        
        async with self._lock:
            now = datetime.now()
            to_remove = []
            
            for conn in self.connections:
                if not conn.in_use:
                    idle_time = (now - conn.last_used).total_seconds()
                    if idle_time > self.config.max_idle_time:
                        to_remove.append(conn)
            
            # Keep minimum connections
            while len(self.connections) - len(to_remove) < self.config.min_connections:
                to_remove.pop()
            
            # Remove idle connections
            for conn in to_remove:
                conn.close()
                self.connections.remove(conn)
    
    # @function: get_stats
    # @purpose: "Get pool statistics"
    # @output: Dict[str, Any]
    # @async: true
    # @ai_testable: true
    async def get_stats(self) -> Dict[str, Any]:
        """@purpose: Get statistics"""
        
        in_use = sum(1 for c in self.connections if c.in_use)
        idle = len(self.connections) - in_use
        
        return {
            "total": len(self.connections),
            "in_use": in_use,
            "idle": idle,
            "max": self.config.max_connections,
            "min": self.config.min_connections
        }
    
    # @function: close_all
    # @purpose: "Close all connections"
    # @side_effects: ["Close all connections"]
    # @async: true
    # @ai_testable: true
    async def close_all(self) -> None:
        """@purpose: Close all connections"""
        
        async with self._lock:
            for conn in self.connections:
                conn.close()
            self.connections.clear()

# @class: DatabasePoolManager
# @purpose: "Global database pool manager"
# @ai_testable: true
class DatabasePoolManager:
    """@summary: Global database pool manager"""
    
    # @attribute: _instance
    # @type: Optional[DatabasePoolManager]
    _instance: Optional['DatabasePoolManager'] = None
    
    # @attribute: pools
    # @type: Dict[str, DatabasePool]
    pools: Dict[str, DatabasePool]
    
    # @function: get_instance
    # @purpose: "Get singleton instance"
    # @output: DatabasePoolManager
    # @ai_testable: true
    @classmethod
    def get_instance(cls) -> 'DatabasePoolManager':
        """@purpose: Get singleton"""
        
        if cls._instance is None:
            cls._instance = cls()
        
        return cls._instance
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize pool manager"""
        self.pools = {}
    
    # @function: get_pool
    # @purpose: "Get or create pool"
    # @input: name: str, config: Optional[PoolConfig]
    # @output: DatabasePool
    # @ai_testable: true
    def get_pool(
        self,
        name: str,
        config: Optional[PoolConfig] = None
    ) -> DatabasePool:
        """@purpose: Get pool"""
        
        if name not in self.pools:
            self.pools[name] = DatabasePool(config)
        
        return self.pools[name]
    
    # @function: close_all
    # @purpose: "Close all pools"
    # @side_effects: ["Close all pools"]
    # @async: true
    # @ai_testable: true
    async def close_all(self) -> None:
        """@purpose: Close all pools"""
        
        for pool in self.pools.values():
            await pool.close_all()
        
        self.pools.clear()
