"""
Timeline 服务

提供 Timeline 和 Conversation 的 CRUD 操作、节点管理和时间范围查询。
使用 SQLite 存储时间序列数据。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from ..models.timeline import (
    Conversation,
    ConversationCreate,
    EventType,
    Timeline,
    TimelineCreate,
    TimelineExport,
    TimelineNode,
    TimelineNodeCreate,
    TimelineRangeQuery,
    TimelineStats,
)


class TimelineServiceConfig(BaseModel):
    """Timeline 服务配置"""
    db_path: str = "./data/cluster_memory"
    """数据库路径"""


class TimelineService:
    """
    Timeline 服务
    
    管理 Timeline、Conversation 和 TimelineNode 的存储和查询。
    
    Attributes:
        config: 配置对象
        sqlite_conn: SQLite 连接
        timelines: 内存中的 Timeline 缓存
        conversations: 内存中的 Conversation 缓存
        nodes: 内存中的 TimelineNode 缓存
    """
    
    def __init__(self, config: Optional[TimelineServiceConfig] = None):
        """
        初始化 Timeline 服务
        
        Args:
            config: 配置对象，如果为 None 则使用默认配置
        """
        self.config = config or TimelineServiceConfig()
        self._timelines: dict[UUID, Timeline] = {}
        self._conversations: dict[UUID, Conversation] = {}
        self._nodes: dict[UUID, TimelineNode] = {}
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
        sqlite_path = db_path / "timelines.db"
        self._sqlite_conn = sqlite3.connect(str(sqlite_path))
        self._init_sqlite_tables()
        
        # 加载已有数据到内存缓存
        await self._load_cache()
    
    def _init_sqlite_tables(self) -> None:
        """初始化 SQLite 表"""
        cursor = self._sqlite_conn.cursor()
        
        # Timeline 主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timelines (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Conversation 主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                participants TEXT NOT NULL DEFAULT '[]',
                timeline_id TEXT,
                memory_refs TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # TimelineNode 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timeline_nodes (
                id TEXT PRIMARY KEY,
                timeline_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT,
                memory_id TEXT,
                cluster_id TEXT,
                timestamp TEXT NOT NULL,
                position INTEGER NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # 时间索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_nodes_timestamp
            ON timeline_nodes (timeline_id, timestamp)
        """)
        
        # Memory 关联索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_nodes_memory
            ON timeline_nodes (memory_id)
        """)
        
        self._sqlite_conn.commit()
    
    async def _load_cache(self) -> None:
        """从 SQLite 加载数据到内存缓存"""
        cursor = self._sqlite_conn.cursor()
        
        # 加载 Timeline
        cursor.execute("SELECT * FROM timelines")
        for row in cursor.fetchall():
            timeline = Timeline(
                id=UUID(row[0]),
                conversation_id=UUID(row[1]) if row[1] else None,
                title=row[2],
                created_at=datetime.fromisoformat(row[3]),
                updated_at=datetime.fromisoformat(row[4])
            )
            self._timelines[timeline.id] = timeline
        
        # 加载 Conversation
        cursor.execute("SELECT * FROM conversations")
        for row in cursor.fetchall():
            conversation = Conversation(
                id=UUID(row[0]),
                title=row[1],
                participants=json.loads(row[2]),
                timeline_id=UUID(row[3]) if row[3] else None,
                memory_refs=[UUID(mid) for mid in json.loads(row[4])],
                metadata=json.loads(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                updated_at=datetime.fromisoformat(row[7])
            )
            self._conversations[conversation.id] = conversation
        
        # 加载 TimelineNode
        cursor.execute("SELECT * FROM timeline_nodes ORDER BY position")
        for row in cursor.fetchall():
            node = TimelineNode(
                id=UUID(row[0]),
                timeline_id=UUID(row[1]),
                event_type=EventType(row[2]),
                content=row[3],
                memory_id=UUID(row[4]) if row[4] else None,
                cluster_id=UUID(row[5]) if row[5] else None,
                timestamp=datetime.fromisoformat(row[6]),
                position=row[7],
                metadata=json.loads(row[8])
            )
            self._nodes[node.id] = node
    
    # ==================== Timeline CRUD ====================
    
    async def create_timeline(self, timeline_create: TimelineCreate) -> Timeline:
        """
        创建 Timeline
        
        Args:
            timeline_create: 创建 Timeline 的请求数据
            
        Returns:
            创建的 Timeline 对象
        """
        timeline = Timeline(
            conversation_id=timeline_create.conversation_id,
            title=timeline_create.title
        )
        
        # 存储到 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT INTO timelines (id, conversation_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(timeline.id),
                str(timeline.conversation_id) if timeline.conversation_id else None,
                timeline.title,
                timeline.created_at.isoformat(),
                timeline.updated_at.isoformat()
            )
        )
        self._sqlite_conn.commit()
        
        # 更新内存缓存
        self._timelines[timeline.id] = timeline
        
        return timeline
    
    async def get_timeline(self, timeline_id: UUID) -> Optional[Timeline]:
        """
        获取单个 Timeline
        
        Args:
            timeline_id: Timeline ID
            
        Returns:
            Timeline 对象，如果不存在返回 None
        """
        return self._timelines.get(timeline_id)
    
    async def delete_timeline(self, timeline_id: UUID) -> bool:
        """
        删除 Timeline
        
        Args:
            timeline_id: Timeline ID
            
        Returns:
            是否成功删除
        """
        if timeline_id not in self._timelines:
            return False
        
        # 删除所有节点
        cursor = self._sqlite_conn.cursor()
        cursor.execute("DELETE FROM timeline_nodes WHERE timeline_id = ?", (str(timeline_id),))
        
        # 删除 Timeline
        cursor.execute("DELETE FROM timelines WHERE id = ?", (str(timeline_id),))
        self._sqlite_conn.commit()
        
        # 删除内存缓存
        for node_id in list(self._nodes.keys()):
            if self._nodes[node_id].timeline_id == timeline_id:
                del self._nodes[node_id]
        
        del self._timelines[timeline_id]
        
        return True
    
    # ==================== Conversation CRUD ====================
    
    async def create_conversation(self, conversation_create: ConversationCreate) -> Conversation:
        """
        创建 Conversation
        
        Args:
            conversation_create: 创建 Conversation 的请求数据
            
        Returns:
            创建的 Conversation 对象
        """
        conversation = Conversation(
            title=conversation_create.title,
            participants=conversation_create.participants,
            metadata=conversation_create.metadata
        )
        
        # 存储到 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (
                id, title, participants, timeline_id, memory_refs, metadata,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(conversation.id),
                conversation.title,
                json.dumps(conversation.participants),
                str(conversation.timeline_id) if conversation.timeline_id else None,
                json.dumps([str(mid) for mid in conversation.memory_refs]),
                json.dumps(conversation.metadata.model_dump()),
                conversation.created_at.isoformat(),
                conversation.updated_at.isoformat()
            )
        )
        self._sqlite_conn.commit()
        
        # 更新内存缓存
        self._conversations[conversation.id] = conversation
        
        return conversation
    
    async def get_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """
        获取单个 Conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation 对象，如果不存在返回 None
        """
        return self._conversations.get(conversation_id)
    
    async def link_conversation_timeline(
        self,
        conversation_id: UUID,
        timeline_id: UUID
    ) -> Optional[Conversation]:
        """
        关联 Conversation 和 Timeline
        
        Args:
            conversation_id: Conversation ID
            timeline_id: Timeline ID
            
        Returns:
            更新后的 Conversation 对象
        """
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None
        
        conversation.timeline_id = timeline_id
        conversation.updated_at = datetime.now()
        
        # 更新 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            "UPDATE conversations SET timeline_id = ?, updated_at = ? WHERE id = ?",
            (
                str(timeline_id),
                conversation.updated_at.isoformat(),
                str(conversation_id)
            )
        )
        self._sqlite_conn.commit()
        
        # 更新 Timeline 的 conversation_id
        timeline = self._timelines.get(timeline_id)
        if timeline:
            timeline.conversation_id = conversation_id
            timeline.updated_at = datetime.now()
            cursor.execute(
                "UPDATE timelines SET conversation_id = ?, updated_at = ? WHERE id = ?",
                (
                    str(conversation_id),
                    timeline.updated_at.isoformat(),
                    str(timeline_id)
                )
            )
            self._sqlite_conn.commit()
        
        return conversation
    
    # ==================== TimelineNode CRUD ====================
    
    async def add_node(
        self,
        timeline_id: UUID,
        node_create: TimelineNodeCreate
    ) -> Optional[TimelineNode]:
        """
        添加 Timeline 节点
        
        Args:
            timeline_id: Timeline ID
            node_create: 创建节点的请求数据
            
        Returns:
            创建的 TimelineNode 对象
        """
        timeline = self._timelines.get(timeline_id)
        if not timeline:
            return None
        
        # 计算位置
        existing_nodes = [n for n in self._nodes.values() if n.timeline_id == timeline_id]
        position = len(existing_nodes)
        
        # 创建节点
        node = TimelineNode(
            timeline_id=timeline_id,
            event_type=node_create.event_type,
            content=node_create.content,
            memory_id=node_create.memory_id,
            cluster_id=node_create.cluster_id,
            metadata=node_create.metadata,
            position=position
        )
        
        # 存储到 SQLite
        cursor = self._sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT INTO timeline_nodes (
                id, timeline_id, event_type, content, memory_id, cluster_id,
                timestamp, position, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(node.id),
                str(node.timeline_id),
                node.event_type.value,
                node.content,
                str(node.memory_id) if node.memory_id else None,
                str(node.cluster_id) if node.cluster_id else None,
                node.timestamp.isoformat(),
                node.position,
                json.dumps(node.metadata)
            )
        )
        
        # 更新 Timeline 的 updated_at
        timeline.updated_at = datetime.now()
        cursor.execute(
            "UPDATE timelines SET updated_at = ? WHERE id = ?",
            (timeline.updated_at.isoformat(), str(timeline_id))
        )
        
        self._sqlite_conn.commit()
        
        # 更新内存缓存
        self._nodes[node.id] = node
        
        return node
    
    async def get_node(self, node_id: UUID) -> Optional[TimelineNode]:
        """
        获取单个节点
        
        Args:
            node_id: 节点 ID
            
        Returns:
            TimelineNode 对象，如果不存在返回 None
        """
        return self._nodes.get(node_id)
    
    async def get_nodes_by_memory(self, memory_id: UUID) -> list[TimelineNode]:
        """
        获取 Memory 关联的所有节点
        
        Args:
            memory_id: Memory ID
            
        Returns:
            TimelineNode 列表
        """
        return [
            node for node in self._nodes.values()
            if node.memory_id == memory_id
        ]
    
    async def get_range(self, query: TimelineRangeQuery) -> list[TimelineNode]:
        """
        获取时间范围内的节点
        
        Args:
            query: 范围查询请求
            
        Returns:
            TimelineNode 列表
        """
        nodes = [
            node for node in self._nodes.values()
            if query.start <= node.timestamp <= query.end
        ]
        
        # 应用事件类型过滤
        if query.event_types:
            nodes = [n for n in nodes if n.event_type in query.event_types]
        
        # 应用 Memory ID 过滤
        if query.memory_id:
            nodes = [n for n in nodes if n.memory_id == query.memory_id]
        
        # 按时间排序
        nodes.sort(key=lambda n: n.timestamp)
        
        # 应用限制
        return nodes[:query.limit]
    
    async def delete_node(self, node_id: UUID) -> bool:
        """
        删除节点
        
        Args:
            node_id: 节点 ID
            
        Returns:
            是否成功删除
        """
        node = self._nodes.get(node_id)
        if not node:
            return False
        
        # 从 SQLite 删除
        cursor = self._sqlite_conn.cursor()
        cursor.execute("DELETE FROM timeline_nodes WHERE id = ?", (str(node_id),))
        self._sqlite_conn.commit()
        
        # 从内存缓存删除
        del self._nodes[node_id]
        
        return True
    
    # ==================== 统计和导出 ====================
    
    async def get_stats(self, timeline_id: UUID) -> TimelineStats:
        """
        获取 Timeline 统计信息
        
        Args:
            timeline_id: Timeline ID
            
        Returns:
            TimelineStats 对象
        """
        nodes = [n for n in self._nodes.values() if n.timeline_id == timeline_id]
        
        if not nodes:
            return TimelineStats(
                total_nodes=0,
                event_distribution={},
                first_event=None,
                last_event=None,
                memory_refs_count=0,
                avg_events_per_day=0.0
            )
        
        # 事件分布
        event_counts: dict[EventType, int] = {}
        for node in nodes:
            event_counts[node.event_type] = event_counts.get(node.event_type, 0) + 1
        
        # Memory 引用数
        memory_refs = sum(1 for n in nodes if n.memory_id is not None)
        
        # 日均事件数
        first = min(n.timestamp for n in nodes)
        last = max(n.timestamp for n in nodes)
        days = max(1, (last - first).days)
        avg_per_day = len(nodes) / days
        
        return TimelineStats(
            total_nodes=len(nodes),
            event_distribution=event_counts,
            first_event=first,
            last_event=last,
            memory_refs_count=memory_refs,
            avg_events_per_day=avg_per_day
        )
    
    async def export_timeline(self, timeline_id: UUID) -> Optional[TimelineExport]:
        """
        导出 Timeline
        
        Args:
            timeline_id: Timeline ID
            
        Returns:
            TimelineExport 对象
        """
        timeline = self._timelines.get(timeline_id)
        if not timeline:
            return None
        
        nodes = [n for n in self._nodes.values() if n.timeline_id == timeline_id]
        nodes.sort(key=lambda n: n.position)
        
        # 获取关联的 Conversation
        conversations = []
        if timeline.conversation_id:
            conversation = self._conversations.get(timeline.conversation_id)
            if conversation:
                conversations.append(conversation)
        
        return TimelineExport(
            timeline=timeline,
            nodes=nodes,
            conversations=conversations
        )
    
    async def close(self) -> None:
        """关闭数据库连接"""
        if self._sqlite_conn:
            self._sqlite_conn.close()
            self._sqlite_conn = None
        
        self._timelines.clear()
        self._conversations.clear()
        self._nodes.clear()