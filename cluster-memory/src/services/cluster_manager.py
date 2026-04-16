"""
Cluster 管理服务

提供 Cluster 的 CRUD 操作、层级管理和自动聚类功能。
使用 SQLite 存储 Cluster 数据和关系。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from ..models.cluster import (
    Cluster,
    ClusterCreate,
    ClusterMergeRequest,
    ClusterSplitRequest,
    ClusterTree,
    ClusterUpdate,
)
from ..models.memory import Memory


class ClusterManagerConfig(BaseModel):
    """Cluster Manager 配置"""
    db_path: str = "./data/cluster_memory"
    """数据库路径"""
    auto_cluster_threshold: float = 0.75
    """自动聚类的相似度阈值"""


class ClusterManager:
    """
    Cluster 管理服务
    
    管理 Cluster 的创建、更新、删除、层级关系和自动聚类。
    
    Attributes:
        config: 配置对象
        sqlite_conn: SQLite 连接
        clusters: 内存中的 Cluster 缓存
    """
    
    def __init__(self, config: Optional[ClusterManagerConfig] = None):
        """
        初始化 Cluster Manager
        
        Args:
            config: 配置对象，如果为 None 则使用默认配置
        """
        self.config = config or ClusterManagerConfig()
        self._clusters: dict[UUID, Cluster] = {}
        self._sqlite_conn: Optional[sqlite3.Connection] = None
    
    async def initialize(self) -> None:
        """
        初始化数据库连接
        
        创建必要的目录和表。
        """
        # 创建数据目录
        db_path = Path(self.config.db_path)
        db_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化 SQLite
        sqlite_path = db_path / "clusters.db"
        self._sqlite_conn = sqlite3.connect(str(sqlite_path))
        self._init_sqlite_tables()
        
        # 加载已有数据到内存缓存
        await self._load_cache()
    
    def _init_sqlite_tables(self) -> None:
        """初始化 SQLite 表"""
        cursor = self._sqlite_conn.cursor()
        
        # Cluster 主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clusters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                color TEXT,
                memory_ids TEXT NOT NULL DEFAULT '[]',
                parent_cluster_id TEXT,
                children TEXT NOT NULL DEFAULT '[]',
                stats TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Cluster 层级关系索引
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cluster_hierarchy (
                parent_id TEXT NOT NULL,
                child_id TEXT NOT NULL,
                PRIMARY KEY (parent_id, child_id)
            )
        """)
        
        # Cluster-Memory 关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cluster_memories (
                cluster_id TEXT NOT NULL,
                memory_id TEXT NOT NULL,
                PRIMARY KEY (cluster_id, memory_id)
            )
        """)
        
        self._sqlite_conn.commit()
    
    async def _load_cache(self) -> None:
        """从 SQLite 加载数据到内存缓存"""
        cursor = self._sqlite_conn.cursor()
        cursor.execute("SELECT * FROM clusters")
        
        for row in cursor.fetchall():
            cluster = Cluster(
                id=UUID(row[0]),
                name=row[1],
                description=row[2],
                tags=json.loads(row[3]),
                color=row[4],
                memory_ids=[UUID(mid) for mid in json.loads(row[5])],
                parent_cluster_id=UUID(row[6]) if row[6] else None,
                children=[UUID(cid) for cid in json.loads(row[7])],
                stats=json.loads(row[8]),
                created_at=datetime.fromisoformat(row[9]),
                updated_at=datetime.fromisoformat(row[10])
            )
            self._clusters[cluster.id] = cluster
    
    async def create(self, cluster_create: ClusterCreate) -> Cluster:
        """
        创建 Cluster
        
        Args:
            cluster_create: 创建 Cluster 的请求数据
            
        Returns:
            创建的 Cluster 对象
        """
        # 创建 Cluster 对象
        cluster = Cluster(
            name=cluster_create.name,
            description=cluster_create.description,
            tags=cluster_create.tags,
            color=cluster_create.color,
            memory_ids=cluster_create.memory_ids,
            parent_cluster_id=cluster_create.parent_cluster_id
        )
        
        # 存储到 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT INTO clusters (
                id, name, description, tags, color, memory_ids,
                parent_cluster_id, children, stats, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(cluster.id),
                cluster.name,
                cluster.description,
                json.dumps(cluster.tags),
                cluster.color,
                json.dumps([str(mid) for mid in cluster.memory_ids]),
                str(cluster.parent_cluster_id) if cluster.parent_cluster_id else None,
                json.dumps([str(cid) for cid in cluster.children]),
                json.dumps(cluster.stats.model_dump()),
                cluster.created_at.isoformat(),
                cluster.updated_at.isoformat()
            )
        )
        
        # 插入层级关系
        if cluster.parent_cluster_id:
            cursor.execute(
                "INSERT OR IGNORE INTO cluster_hierarchy (parent_id, child_id) VALUES (?, ?)",
                (str(cluster.parent_cluster_id), str(cluster.id))
            )
            # 更新父 Cluster 的 children
            parent = self._clusters.get(cluster.parent_cluster_id)
            if parent:
                parent.add_child(cluster.id)
                await self._update_parent_children(parent)
        
        # 插入 Memory 关联
        for memory_id in cluster.memory_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO cluster_memories (cluster_id, memory_id) VALUES (?, ?)",
                (str(cluster.id), str(memory_id))
            )
        
        self._sqlite_conn.commit()
        
        # 更新内存缓存
        self._clusters[cluster.id] = cluster
        
        return cluster
    
    async def _update_parent_children(self, parent: Cluster) -> None:
        """更新父 Cluster 的 children 字段"""
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            "UPDATE clusters SET children = ?, updated_at = ? WHERE id = ?",
            (
                json.dumps([str(cid) for cid in parent.children]),
                parent.updated_at.isoformat(),
                str(parent.id)
            )
        )
        self._sqlite_conn.commit()
    
    async def get(self, cluster_id: UUID) -> Optional[Cluster]:
        """
        获取单个 Cluster
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            Cluster 对象，如果不存在返回 None
        """
        return self._clusters.get(cluster_id)
    
    async def update(self, cluster_id: UUID, cluster_update: ClusterUpdate) -> Optional[Cluster]:
        """
        更新 Cluster
        
        Args:
            cluster_id: Cluster ID
            cluster_update: 更新数据
            
        Returns:
            更新后的 Cluster 对象，如果不存在返回 None
        """
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return None
        
        # 更新字段
        if cluster_update.name is not None:
            cluster.name = cluster_update.name
        
        if cluster_update.description is not None:
            cluster.description = cluster_update.description
        
        if cluster_update.tags is not None:
            cluster.tags = cluster_update.tags
        
        if cluster_update.color is not None:
            cluster.color = cluster_update.color
        
        # 处理父 Cluster 变化
        old_parent_id = cluster.parent_cluster_id
        new_parent_id = cluster_update.parent_cluster_id
        
        if old_parent_id != new_parent_id:
            # 从旧父 Cluster 移除
            if old_parent_id:
                old_parent = self._clusters.get(old_parent_id)
                if old_parent:
                    old_parent.remove_child(cluster_id)
                    await self._update_parent_children(old_parent)
            
            # 添加到新父 Cluster
            if new_parent_id:
                new_parent = self._clusters.get(new_parent_id)
                if new_parent:
                    new_parent.add_child(cluster_id)
                    await self._update_parent_children(new_parent)
            
            cluster.parent_cluster_id = new_parent_id
        
        cluster.updated_at = datetime.now()
        
        # 更新 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            """
            UPDATE clusters
            SET name = ?, description = ?, tags = ?, color = ?, 
                parent_cluster_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                cluster.name,
                cluster.description,
                json.dumps(cluster.tags),
                cluster.color,
                str(cluster.parent_cluster_id) if cluster.parent_cluster_id else None,
                cluster.updated_at.isoformat(),
                str(cluster_id)
            )
        )
        
        # 更新层级关系
        if old_parent_id != new_parent_id:
            if old_parent_id:
                cursor.execute(
                    "DELETE FROM cluster_hierarchy WHERE parent_id = ? AND child_id = ?",
                    (str(old_parent_id), str(cluster_id))
                )
            if new_parent_id:
                cursor.execute(
                    "INSERT OR IGNORE INTO cluster_hierarchy (parent_id, child_id) VALUES (?, ?)",
                    (str(new_parent_id), str(cluster_id))
                )
        
        self._sqlite_conn.commit()
        
        return cluster
    
    async def delete(self, cluster_id: UUID) -> bool:
        """
        删除 Cluster
        
        Args:
            cluster_id: Cluster ID
            
        Returns:
            是否成功删除
        """
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return False
        
        # 检查是否有子 Cluster
        if cluster.children:
            # 可选：递归删除子 Cluster 或抛出错误
            # 这里选择先删除子 Cluster
            for child_id in cluster.children:
                await self.delete(child_id)
        
        # 从父 Cluster 移除
        if cluster.parent_cluster_id:
            parent = self._clusters.get(cluster.parent_cluster_id)
            if parent:
                parent.remove_child(cluster_id)
                await self._update_parent_children(parent)
        
        # 从 SQLite 删除
        cursor = self._sqlite_conn.cursor()
        cursor.execute("DELETE FROM clusters WHERE id = ?", (str(cluster_id),))
        cursor.execute("DELETE FROM cluster_hierarchy WHERE child_id = ?", (str(cluster_id),))
        cursor.execute("DELETE FROM cluster_memories WHERE cluster_id = ?", (str(cluster_id),))
        self._sqlite_conn.commit()
        
        # 从内存缓存删除
        del self._clusters[cluster_id]
        
        return True
    
    async def add_memory(self, cluster_id: UUID, memory_id: UUID) -> Optional[Cluster]:
        """
        将 Memory 添加到 Cluster
        
        Args:
            cluster_id: Cluster ID
            memory_id: Memory ID
            
        Returns:
            更新后的 Cluster 对象，如果不存在返回 None
        """
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return None
        
        cluster.add_memory(memory_id)
        
        # 更新 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            "UPDATE clusters SET memory_ids = ?, stats = ?, updated_at = ? WHERE id = ?",
            (
                json.dumps([str(mid) for mid in cluster.memory_ids]),
                json.dumps(cluster.stats.model_dump()),
                cluster.updated_at.isoformat(),
                str(cluster_id)
            )
        )
        cursor.execute(
            "INSERT OR IGNORE INTO cluster_memories (cluster_id, memory_id) VALUES (?, ?)",
            (str(cluster_id), str(memory_id))
        )
        self._sqlite_conn.commit()
        
        return cluster
    
    async def remove_memory(self, cluster_id: UUID, memory_id: UUID) -> Optional[Cluster]:
        """
        从 Cluster 移除 Memory
        
        Args:
            cluster_id: Cluster ID
            memory_id: Memory ID
            
        Returns:
            更新后的 Cluster 对象，如果不存在返回 None
        """
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return None
        
        if not cluster.remove_memory(memory_id):
            return cluster
        
        # 更新 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            "UPDATE clusters SET memory_ids = ?, stats = ?, updated_at = ? WHERE id = ?",
            (
                json.dumps([str(mid) for mid in cluster.memory_ids]),
                json.dumps(cluster.stats.model_dump()),
                cluster.updated_at.isoformat(),
                str(cluster_id)
            )
        )
        cursor.execute(
            "DELETE FROM cluster_memories WHERE cluster_id = ? AND memory_id = ?",
            (str(cluster_id), str(memory_id))
        )
        self._sqlite_conn.commit()
        
        return cluster
    
    async def list_all(self, parent_id: Optional[UUID] = None) -> list[Cluster]:
        """
        列出所有 Cluster
        
        Args:
            parent_id: 父 Cluster ID 过滤 (None 表示根 Cluster)
            
        Returns:
            Cluster 列表
        """
        if parent_id is None:
            return [c for c in self._clusters.values() if c.is_root()]
        else:
            return [c for c in self._clusters.values() if c.parent_cluster_id == parent_id]
    
    async def get_tree(self, root_id: Optional[UUID] = None) -> list[ClusterTree]:
        """
        获取 Cluster 树结构
        
        Args:
            root_id: 根 Cluster ID (None 表示从根 Cluster 开始)
            
        Returns:
            ClusterTree 列表
        """
        if root_id is None:
            roots = [c for c in self._clusters.values() if c.is_root()]
        else:
            root = self._clusters.get(root_id)
            if not root:
                return []
            roots = [root]
        
        trees = []
        for root in roots:
            tree = await self._build_tree(root)
            trees.append(tree)
        
        return trees
    
    async def _build_tree(self, cluster: Cluster) -> ClusterTree:
        """
        构建 Cluster 树
        
        Args:
            cluster: 当前 Cluster
            
        Returns:
            ClusterTree 对象
        """
        children = []
        for child_id in cluster.children:
            child = self._clusters.get(child_id)
            if child:
                child_tree = await self._build_tree(child)
                children.append(child_tree)
        
        return ClusterTree(cluster=cluster, children=children)
    
    async def merge(self, merge_request: ClusterMergeRequest) -> Optional[Cluster]:
        """
        合并多个 Cluster
        
        Args:
            merge_request: 合并请求
            
        Returns:
            合并后的 Cluster 对象
        """
        target = self._clusters.get(merge_request.target_cluster_id)
        if not target:
            return None
        
        for source_id in merge_request.source_cluster_ids:
            source = self._clusters.get(source_id)
            if not source:
                continue
            
            # 合合 Memory
            for memory_id in source.memory_ids:
                target.add_memory(memory_id)
            
            # 合合标签
            if merge_request.keep_source_tags:
                for tag in source.tags:
                    if tag not in target.tags:
                        target.tags.append(tag)
            
            # 删除源 Cluster
            await self.delete(source_id)
        
        # 更新名称
        if merge_request.new_name:
            target.name = merge_request.new_name
        
        target.updated_at = datetime.now()
        
        # 更新 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            """
            UPDATE clusters
            SET name = ?, tags = ?, memory_ids = ?, stats = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                target.name,
                json.dumps(target.tags),
                json.dumps([str(mid) for mid in target.memory_ids]),
                json.dumps(target.stats.model_dump()),
                target.updated_at.isoformat(),
                str(target.id)
            )
        )
        self._sqlite_conn.commit()
        
        return target
    
    async def auto_cluster(
        self,
        memories: list[Memory],
        method: str = "similarity"
    ) -> list[Cluster]:
        """
        自动聚类
        
        Args:
            memories: 要聚类的 Memory 列表
            method: 聚类方法 ('similarity', 'tag', 'kmeans')
            
        Returns:
            创建的 Cluster 列表
            
        Note:
            这里提供占位符实现，实际聚类算法需要根据需求实现
        """
        # TODO: 实现真实的聚类算法
        # 示例：基于相似度的聚类
        # 1. 计算所有 Memory 之间的相似度
        # 2. 使用阈值或 HDBSCAN 进行聚类
        # 3. 创建 Cluster 并分配 Memory
        
        # 占位符：每个标签创建一个 Cluster
        tag_groups: dict[str, list[UUID]] = {}
        for memory in memories:
            for tag in memory.tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(memory.id)
        
        clusters = []
        for tag, memory_ids in tag_groups.items():
            if len(memory_ids) >= 2:  # 至少 2 个 Memory 才创建 Cluster
                cluster = await self.create(
                    ClusterCreate(
                        name=f"Auto: {tag}",
                        description=f"自动聚类: 标签 {tag}",
                        tags=[tag],
                        memory_ids=memory_ids
                    )
                )
                clusters.append(cluster)
        
        return clusters
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None
        
        self._clusters.clear()