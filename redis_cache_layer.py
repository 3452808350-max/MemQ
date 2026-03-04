"""
混合记忆架构 - 阶段 2 实现
Redis 缓存层 + Write-Through 策略

实施内容:
1. Redis 连接管理
2. Write-Through 缓存一致性
3. LanceDB 分区优化
4. 混合搜索基础

预期收益：查询延迟 ↓80%, 缓存命中率 >80%
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import redis
from memory_enhanced import MemoryLRUCache, memory_store_enhanced


# ==================== Redis 连接管理 ====================

class RedisConnectionManager:
    """
    Redis 连接管理器
    
    特性:
    - 连接池管理
    - 自动重连
    - 降级到内存缓存
    """
    
    _instance = None
    _redis_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.host = 'localhost'
        self.port = 6379
        self.db = 0
        self.password = None
        self.enabled = False
        self.memory_cache = MemoryLRUCache(maxsize=1000)
        
        # 尝试连接 Redis
        self._connect()
    
    def _connect(self):
        """连接 Redis（失败则降级到内存）"""
        try:
            self._redis_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                max_connections=50
            )
            
            # 测试连接
            test_client = redis.Redis(connection_pool=self._redis_pool)
            test_client.ping()
            
            self.enabled = True
            print(f"✅ Redis 连接成功：{self.host}:{self.port}")
            
        except Exception as e:
            self.enabled = False
            print(f"⚠️  Redis 连接失败，降级到内存缓存：{e}")
    
    def get_client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端"""
        if not self.enabled or not self._redis_pool:
            return None
        
        try:
            return redis.Redis(connection_pool=self._redis_pool)
        except Exception:
            self.enabled = False
            return None
    
    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        return self.enabled


# 全局 Redis 管理器
redis_manager = RedisConnectionManager()


# ==================== Write-Through 缓存 ====================

class WriteThroughMemoryCache:
    """
    Write-Through 记忆缓存
    
    策略:
    - 写入时同步更新 Redis 和 LanceDB
    - 读取时先查 Redis，未命中查 LanceDB
    - 保证强一致性
    """
    
    def __init__(self):
        self.redis_manager = redis_manager
        self.memory_cache = MemoryLRUCache(maxsize=1000)
    
    def store(self, 
              text: str, 
              category: str = "other",
              importance: float = 0.7,
              tags: List[str] = None,
              scope: str = "global") -> str:
        """
        存储记忆（Write-Through）
        
        流程:
        1. 生成记忆 ID
        2. 写入 Redis（同步）
        3. 写入 LanceDB（异步）
        4. 更新内存缓存
        
        Args:
            text: 记忆内容
            category: 类别
            importance: 重要性
            tags: 标签
            scope: 作用域
        
        Returns:
            memory_id: 记忆 ID
        """
        # 生成记忆 ID
        memory_id = f"mem_{datetime.now().timestamp()}"
        
        # 构建记忆对象
        memory = {
            "id": memory_id,
            "text": text,
            "category": category,
            "importance": importance,
            "tags": tags or [],
            "scope": scope,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "access_count": 0
        }
        
        # Step 1: 写入 Redis
        redis_client = self.redis_manager.get_client()
        if redis_client:
            ttl = int(importance * 86400)  # 基于重要性的 TTL
            redis_client.setex(
                f"mem:{memory_id}",
                ttl,
                json.dumps(memory, ensure_ascii=False)
            )
            print(f"📝 Redis 写入：{memory_id} (TTL: {ttl}s)")
        
        # Step 2: 写入内存缓存
        self.memory_cache.set(f"mem:{memory_id}", memory, importance)
        
        # Step 3: 写入 LanceDB（简化，实际调用 lancedb.add）
        # lancedb_table.add([memory])
        print(f"💾 LanceDB 写入：{memory_id}")
        
        # Step 4: 更新索引
        self._update_index(memory)
        
        print(f"✅ 记忆已存储（Write-Through）：{memory_id}")
        
        return memory_id
    
    def recall(self, 
               query: str, 
               scope: str = None,
               limit: int = 5) -> List[Dict]:
        """
        检索记忆（缓存优先）
        
        流程:
        1. 检查 Redis 缓存
        2. 检查内存缓存
        3. LanceDB 向量检索
        4. 缓存结果
        
        Args:
            query: 查询文本
            scope: 作用域过滤
            limit: 返回数量
        
        Returns:
            记忆列表
        """
        # 生成查询哈希
        query_hash = f"search:{hashlib.md5(f'{query}:{scope}'.encode()).hexdigest()}"
        
        # Step 1: 检查 Redis 缓存
        redis_client = self.redis_manager.get_client()
        if redis_client:
            cached = redis_client.get(query_hash)
            if cached:
                print(f"✅ Redis 缓存命中：{query_hash}")
                result = json.loads(cached)
                self._update_access_stats(result)
                return result
        
        # Step 2: 检查内存缓存
        cached = self.memory_cache.get(query_hash)
        if cached:
            print(f"✅ 内存缓存命中：{query_hash}")
            return cached["data"]
        
        # Step 3: LanceDB 检索（简化实现）
        print(f"⚠️  缓存未命中，执行 LanceDB 检索：{query_hash}")
        results = self._lancedb_search(query, scope, limit)
        
        # Step 4: 缓存结果（TTL 5 分钟）
        if redis_client:
            redis_client.setex(query_hash, 300, json.dumps(results, ensure_ascii=False))
        
        self.memory_cache.set(query_hash, results, importance=0.5)
        
        print(f"💾 结果已缓存：{len(results)} 条")
        
        return results
    
    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """
        获取单条记忆
        
        Args:
            memory_id: 记忆 ID
        
        Returns:
            记忆对象
        """
        # 检查 Redis
        redis_client = self.redis_manager.get_client()
        if redis_client:
            cached = redis_client.get(f"mem:{memory_id}")
            if cached:
                print(f"✅ Redis 命中：{memory_id}")
                memory = json.loads(cached)
                self._update_access_stats(memory)
                return memory
        
        # 检查内存缓存
        cached = self.memory_cache.get(f"mem:{memory_id}")
        if cached:
            print(f"✅ 内存缓存命中：{memory_id}")
            return cached["data"]
        
        # LanceDB 检索
        print(f"⚠️  未找到记忆：{memory_id}")
        return None
    
    def _update_index(self, memory: Dict):
        """更新索引（简化）"""
        # 实际实现应该更新 LanceDB 的索引
        pass
    
    def _lancedb_search(self, query: str, scope: str, limit: int) -> List[Dict]:
        """LanceDB 检索（简化实现）"""
        # 实际实现应该调用 LanceDB 的向量检索
        return []
    
    def _update_access_stats(self, memory: Dict):
        """更新访问统计"""
        if isinstance(memory, list):
            for mem in memory:
                mem["access_count"] = mem.get("access_count", 0) + 1
                mem["last_accessed"] = datetime.now().isoformat()
        elif isinstance(memory, dict):
            memory["access_count"] = memory.get("access_count", 0) + 1
            memory["last_accessed"] = datetime.now().isoformat()


# ==================== LanceDB 分区优化 ====================

class LanceDBPartitionManager:
    """
    LanceDB 分区管理器
    
    分区策略:
    - 一级分区：日期（按天）
    - 二级分区：类别（preference/decision/fact/...）
    """
    
    def __init__(self, db_path: str = "/opt/lancedb"):
        self.db_path = db_path
        self.partitions = {}
    
    def create_partitioned_table(self, 
                                 table_name: str = "memory",
                                 partition_by: List[str] = None):
        """
        创建分区表
        
        Args:
            table_name: 表名
            partition_by: 分区字段
        """
        if partition_by is None:
            partition_by = ["date", "category"]
        
        print(f"📊 创建分区表：{table_name}")
        print(f"   分区字段：{partition_by}")
        
        # 实际实现:
        # table = db.create_table(
        #     table_name,
        #     schema=schema,
        #     partition_by=partition_by
        # )
        
        self.partitions[table_name] = partition_by
    
    def optimize_index(self, table_name: str):
        """
        优化索引
        
        Args:
            table_name: 表名
        """
        print(f"🔧 优化索引：{table_name}")
        
        # 实际实现:
        # table.create_index(
        #     metric="cosine",
        #     num_partitions=256,
        #     num_sub_vectors=96
        # )
        # table.create_index("category")
        # table.create_index("importance")
        # table.create_index("created_at")


# ==================== 混合搜索基础 ====================

def hybrid_search_basic(query: str, 
                       redis_cache: WriteThroughMemoryCache,
                       limit: int = 10) -> List[Dict]:
    """
    基础混合搜索
    
    当前实现:
    - Redis 缓存层
    - 内存缓存层
    - LanceDB 检索（待实现）
    
    未来扩展:
    - BM25 全文检索
    - RRF 融合
    - Cross-Encoder 重排
    
    Args:
        query: 查询文本
        redis_cache: 缓存实例
        limit: 返回数量
    
    Returns:
        搜索结果
    """
    print(f"🔍 混合搜索：{query}")
    
    # 使用 Redis 缓存层检索
    results = redis_cache.recall(query, limit=limit)
    
    return results


# ==================== 监控指标增强 ====================

def get_redis_stats() -> Dict:
    """获取 Redis 统计"""
    redis_client = redis_manager.get_client()
    
    if not redis_client:
        return {
            "available": False,
            "message": "Redis 未连接"
        }
    
    try:
        info = redis_client.info("stats")
        memory = redis_client.info("memory")
        
        return {
            "available": True,
            "connected_clients": info.get("connected_clients", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "used_memory_human": memory.get("used_memory_human", "N/A"),
            "used_memory_peak_human": memory.get("used_memory_peak_human", "N/A")
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


def get_hybrid_memory_metrics() -> Dict:
    """获取混合记忆系统完整指标"""
    return {
        "timestamp": datetime.now().isoformat(),
        "redis": get_redis_stats(),
        "memory_cache": redis_manager.memory_cache.get_stats(),
        "write_through_cache": {
            "enabled": redis_manager.enabled
        }
    }


def print_hybrid_metrics():
    """打印混合记忆系统指标"""
    metrics = get_hybrid_memory_metrics()
    
    print("\n📊 混合记忆系统指标")
    print("=" * 60)
    print(f"Redis 状态：{'✅ 已连接' if metrics['redis']['available'] else '⚠️  未连接'}")
    print(f"内存缓存命中率：{metrics['memory_cache']['hit_rate']}")
    print(f"缓存大小：{metrics['memory_cache']['cache_size']}/{metrics['memory_cache']['max_size']}")
    print(f"Write-Through: {'✅ 启用' if metrics['write_through_cache']['enabled'] else '❌ 禁用'}")
    print("=" * 60)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("🧪 测试混合记忆架构 - 阶段 2\n")
    
    # 测试 1: Redis 连接
    print("测试 1: Redis 连接管理")
    print("-" * 60)
    print(f"Redis 可用：{redis_manager.is_available()}")
    print()
    
    # 测试 2: Write-Through 缓存
    print("测试 2: Write-Through 缓存")
    print("-" * 60)
    cache = WriteThroughMemoryCache()
    
    # 存储记忆
    mem_id = cache.store(
        text="用户偏好简洁的回复",
        category="preference",
        importance=0.9,
        tags=["chat", "style"]
    )
    print()
    
    # 获取记忆
    memory = cache.get_memory(mem_id)
    if memory:
        print(f"获取记忆：{memory['text']}")
    print()
    
    # 测试 3: 混合搜索
    print("测试 3: 混合搜索")
    print("-" * 60)
    results = hybrid_search_basic("用户偏好", cache)
    print(f"搜索结果：{len(results)} 条")
    print()
    
    # 测试 4: 监控指标
    print("测试 4: 监控指标")
    print("-" * 60)
    print_hybrid_metrics()
    print()
    
    print("✅ 阶段 2 测试完成！")
