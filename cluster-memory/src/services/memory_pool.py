"""
Memory Pool 服务

提供 Memory 的 CRUD 操作和向量搜索功能。
使用 LanceDB 进行向量存储和搜索，SQLite 作为辅助存储。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import lancedb
from lancedb.embeddings import EmbeddingFunctionConfig, EmbeddingFunctionRegistry
from lancedb.pydantic import LanceModel, Vector
from pydantic import BaseModel

from ..models.memory import (
    Memory,
    MemoryCreate,
    MemoryPoolStats,
    MemorySearchResult,
    MemoryUpdate,
)


class MemoryVector(LanceModel):
    """Memory 向量存储模型 (LanceDB)"""
    id: str
    """Memory UUID 字符串"""
    vector: Vector(1536)  # OpenAI text-embedding-ada-002 维度
    """向量嵌入"""
    content: str
    """记忆内容 (用于全文搜索)"""


class MemoryPoolConfig(BaseModel):
    """Memory Pool 配置"""
    db_path: str = "./data/cluster_memory"
    """数据库路径"""
    table_name: str = "memories"
    """向量表名称"""
    embedding_model: str = "text-embedding-ada-002"
    """嵌入模型名称"""


class MemoryPool:
    """
    Memory Pool 服务
    
    管理 Memory 的存储、检索和搜索。
    
    Attributes:
        config: 配置对象
        db: LanceDB 连接
        sqlite_conn: SQLite 连接
        memories: 内存中的 Memory 缓存
    """
    
    def __init__(self, config: Optional[MemoryPoolConfig] = None):
        """
        初始化 Memory Pool
        
        Args:
            config: 配置对象，如果为 None 则使用默认配置
        """
        self.config = config or MemoryPoolConfig()
        self._memories: dict[UUID, Memory] = {}
        self._db: Optional[lancedb.DBConnection] = None
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._table: Optional[lancedb.table.Table] = None
    
    async def initialize(self) -> None:
        """
        初始化数据库连接
        
        创建必要的目录、表和索引。
        """
        # 创建数据目录
        db_path = Path(self.config.db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化 LanceDB
        self._db = lancedb.connect(str(db_path / "vectors"))
        
        # 创建或获取向量表
        if self.config.table_name not in self._db.table_names():
            self._table = self._db.create_table(
                self.config.table_name,
                schema=MemoryVector.to_arrow_schema()
            )
        else:
            self._table = self._db.open_table(self.config.table_name)
        
        # 初始化 SQLite
        sqlite_path = db_path / "memories.db"
        self._sqlite_conn = sqlite3.connect(str(sqlite_path))
        self._init_sqlite_tables()
        
        # 加载已有数据到内存缓存
        await self._load_cache()
    
    def _init_sqlite_tables(self) -> None:
        """初始化 SQLite 表"""
        cursor = self._sqlite_conn.cursor()
        
        # Memory 主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                cluster_ids TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 标签索引表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_tags (
                memory_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (memory_id, tag)
            )
        """)
        
        # Cluster 关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_clusters (
                memory_id TEXT NOT NULL,
                cluster_id TEXT NOT NULL,
                PRIMARY KEY (memory_id, cluster_id)
            )
        """)
        
        self._sqlite_conn.commit()
    
    async def _load_cache(self) -> None:
        """从 SQLite 加载数据到内存缓存"""
        cursor = self._sqlite_conn.cursor()
        cursor.execute("SELECT * FROM memories")
        
        for row in cursor.fetchall():
            memory = Memory(
                id=UUID(row[0]),
                content=row[1],
                tags=json.loads(row[2]),
                cluster_ids=[UUID(cid) for cid in json.loads(row[3])],
                metadata=json.loads(row[4]),
                created_at=datetime.fromisoformat(row[5]),
                updated_at=datetime.fromisoformat(row[6])
            )
            self._memories[memory.id] = memory
    
    async def _embed(self, text: str) -> list[float]:
        """
        生成文本的向量嵌入
        
        Args:
            text: 要嵌入的文本
            
        Returns:
            向量嵌入列表
            
        Note:
            实际实现需要调用嵌入服务（如 OpenAI 或阿里云）
            这里提供一个占位符实现
        """
        # TODO: 实现真实的嵌入服务调用
        # 示例：使用 OpenAI API
        # import openai
        # response = openai.Embedding.create(
        #     model=self.config.embedding_model,
        #     input=text
        # )
        # return response['data'][0]['embedding']
        
        # 占位符：返回零向量 (实际使用时替换为真实嵌入)
        return [0.0] * 1536
    
    async def add(self, memory_create: MemoryCreate) -> Memory:
        """
        添加 Memory 到 Pool
        
        Args:
            memory_create: 创建 Memory 的请求数据
            
        Returns:
            创建的 Memory 对象
        """
        # 创建 Memory 对象
        memory = Memory(
            content=memory_create.content,
            tags=memory_create.tags,
            metadata=memory_create.metadata,
            cluster_ids=memory_create.cluster_ids
        )
        
        # 生成嵌入向量
        embedding = await self._embed(memory.content)
        memory.embedding = embedding
        
        # 存储到 LanceDB
        vector_record = MemoryVector(
            id=str(memory.id),
            vector=embedding,
            content=memory.content
        )
        self._table.add([vector_record])
        
        # 存储到 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT INTO memories (id, content, tags, cluster_ids, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(memory.id),
                memory.content,
                json.dumps(memory.tags),
                json.dumps([str(cid) for cid in memory.cluster_ids]),
                memory.metadata.model_dump_json(),
                memory.created_at.isoformat(),
                memory.updated_at.isoformat()
            )
        )
        
        # 插入标签索引
        for tag in memory.tags:
            cursor.execute(
                "INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                (str(memory.id), tag)
            )
        
        # 插入 Cluster 关联
        for cluster_id in memory.cluster_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO memory_clusters (memory_id, cluster_id) VALUES (?, ?)",
                (str(memory.id), str(cluster_id))
            )
        
        self._sqlite_conn.commit()
        
        # 更新内存缓存
        self._memories[memory.id] = memory
        
        return memory
    
    async def get(self, memory_id: UUID) -> Optional[Memory]:
        """
        获取单个 Memory
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory 对象，如果不存在返回 None
        """
        return self._memories.get(memory_id)
    
    async def update(self, memory_id: UUID, memory_update: MemoryUpdate) -> Optional[Memory]:
        """
        更新 Memory
        
        Args:
            memory_id: Memory ID
            memory_update: 更新数据
            
        Returns:
            更新后的 Memory 对象，如果不存在返回 None
        """
        memory = self._memories.get(memory_id)
        if not memory:
            return None
        
        # 更新字段
        if memory_update.content is not None:
            memory.content = memory_update.content
            # 重新生成嵌入向量
            embedding = await self._embed(memory.content)
            memory.embedding = embedding
            # 更新向量表
            self._table.update(
                where=f"id = '{memory_id}'",
                values={
                    "vector": embedding,
                    "content": memory.content
                }
            )
        
        if memory_update.tags is not None:
            # 删除旧标签
            cursor = self._sqlite_conn.cursor()
            cursor.execute("DELETE FROM memory_tags WHERE memory_id = ?", (str(memory_id),))
            # 插入新标签
            for tag in memory_update.tags:
                cursor.execute(
                    "INSERT INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                    (str(memory_id), tag)
                )
            memory.tags = memory_update.tags
        
        if memory_update.metadata is not None:
            memory.metadata = memory_update.metadata
        
        if memory_update.cluster_ids is not None:
            # 删除旧关联
            cursor = self._sqlite_conn.cursor()
            cursor.execute("DELETE FROM memory_clusters WHERE memory_id = ?", (str(memory_id),))
            # 插入新关联
            for cluster_id in memory_update.cluster_ids:
                cursor.execute(
                    "INSERT INTO memory_clusters (memory_id, cluster_id) VALUES (?, ?)",
                    (str(memory_id), str(cluster_id))
                )
            memory.cluster_ids = memory_update.cluster_ids
        
        memory.updated_at = datetime.now()
        
        # 更新 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            """
            UPDATE memories
            SET content = ?, tags = ?, cluster_ids = ?, metadata = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                memory.content,
                json.dumps(memory.tags),
                json.dumps([str(cid) for cid in memory.cluster_ids]),
                memory.metadata.model_dump_json(),
                memory.updated_at.isoformat(),
                str(memory_id)
            )
        )
        self._sqlite_conn.commit()
        
        return memory
    
    async def delete(self, memory_id: UUID) -> bool:
        """
        删除 Memory
        
        Args:
            memory_id: Memory ID
            
        Returns:
            是否成功删除
        """
        if memory_id not in self._memories:
            return False
        
        # 从向量表删除
        self._table.delete(f"id = '{memory_id}'")
        
        # 从 SQLite 删除
        cursor = self._sqlite_conn.cursor()
        cursor.execute("DELETE FROM memories WHERE id = ?", (str(memory_id),))
        cursor.execute("DELETE FROM memory_tags WHERE memory_id = ?", (str(memory_id),))
        cursor.execute("DELETE FROM memory_clusters WHERE memory_id = ?", (str(memory_id),))
        self._sqlite_conn.commit()
        
        # 从内存缓存删除
        del self._memories[memory_id]
        
        return True
    
    async def search(
        self,
        query: str,
        k: int = 10,
        tags: Optional[list[str]] = None,
        cluster_ids: Optional[list[UUID]] = None
    ) -> list[MemorySearchResult]:
        """
        搜索 Memory
        
        Args:
            query: 搜索查询
            k: 返回数量
            tags: 标签过滤
            cluster_ids: Cluster ID 过滤
            
        Returns:
            搜索结果列表
        """
        # 生成查询向量
        query_vector = await self._embed(query)
        
        # 向量搜索
        results = self._table.search(query_vector).limit(k * 2).to_pydantic(MemoryVector)
        
        # 构建结果
        search_results = []
        for result in results:
            memory_id = UUID(result.id)
            memory = self._memories.get(memory_id)
            if not memory:
                continue
            
            # 应用标签过滤
            if tags and not any(tag in memory.tags for tag in tags):
                continue
            
            # 应用 Cluster 过滤
            if cluster_ids and not any(cid in memory.cluster_ids for cid in cluster_ids):
                continue
            
            search_results.append(MemorySearchResult(
                memory=memory,
                score=1.0,  # TODO: 使用实际的相似度分数
                highlights={"content": [query]}  # TODO: 实现高亮
            ))
            
            if len(search_results) >= k:
                break
        
        return search_results
    
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[list[str]] = None,
        cluster_ids: Optional[list[UUID]] = None
    ) -> list[Memory]:
        """
        列出所有 Memory
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            tags: 标签过滤
            cluster_ids: Cluster ID 过滤
            
        Returns:
            Memory 列表
        """
        memories = list(self._memories.values())
        
        # 应用标签过滤
        if tags:
            memories = [m for m in memories if any(tag in m.tags for tag in tags)]
        
        # 应用 Cluster 过滤
        if cluster_ids:
            memories = [m for m in memories if any(cid in m.cluster_ids for cid in cluster_ids)]
        
        # 按更新时间倒序排序
        memories.sort(key=lambda m: m.updated_at, reverse=True)
        
        return memories[offset:offset + limit]
    
    async def get_stats(self) -> MemoryPoolStats:
        """
        获取 Memory Pool 统计信息
        
        Returns:
            统计信息对象
        """
        memories = list(self._memories.values())
        
        if not memories:
            return MemoryPoolStats(
                total_memories=0,
                total_tags=0,
                total_clusters=0,
                avg_content_length=0.0,
                oldest_memory=None,
                newest_memory=None,
                tag_distribution={}
            )
        
        # 统计标签
        tag_counts: dict[str, int] = {}
        for memory in memories:
            for tag in memory.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # 统计 Cluster
        cluster_ids: set[UUID] = set()
        for memory in memories:
            cluster_ids.update(memory.cluster_ids)
        
        return MemoryPoolStats(
            total_memories=len(memories),
            total_tags=len(tag_counts),
            total_clusters=len(cluster_ids),
            avg_content_length=sum(len(m.content) for m in memories) / len(memories),
            oldest_memory=min(m.created_at for m in memories),
            newest_memory=max(m.created_at for m in memories),
            tag_distribution=tag_counts
        )
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None
        
        self._db = None
        self._table = None
        self._memories.clear()