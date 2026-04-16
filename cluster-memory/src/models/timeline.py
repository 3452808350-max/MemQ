"""
Timeline 数据模型

定义 Conversation Timeline 的数据结构，支持时间导航和 Memory 关联。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Timeline 事件类型"""
    CREATE = "create"
    """创建 Memory"""
    UPDATE = "update"
    """更新 Memory"""
    DELETE = "delete"
    """删除 Memory"""
    REFERENCE = "reference"
    """引用 Memory"""
    QUERY = "query"
    """查询操作"""
    CLUSTER_CREATE = "cluster_create"
    """创建 Cluster"""
    CLUSTER_UPDATE = "cluster_update"
    """更新 Cluster"""
    CLUSTER_DELETE = "cluster_delete"
    """删除 Cluster"""
    NOTE = "note"
    """备注"""


class TimelineNodeBase(BaseModel):
    """Timeline 节点基础模型"""
    event_type: EventType
    """事件类型"""
    content: Optional[str] = Field(default=None, max_length=10000)
    """事件内容/备注"""
    memory_id: Optional[UUID] = None
    """关联的 Memory ID"""
    cluster_id: Optional[UUID] = None
    """关联的 Cluster ID"""
    metadata: dict[str, Any] = Field(default_factory=dict)
    """额外元数据"""


class TimelineNodeCreate(TimelineNodeBase):
    """创建 Timeline 节点请求"""
    pass


class TimelineNode(TimelineNodeBase):
    """Timeline 节点完整模型"""
    id: UUID = Field(default_factory=uuid4)
    """节点唯一标识符"""
    timeline_id: UUID
    """所属 Timeline ID"""
    timestamp: datetime = Field(default_factory=datetime.now)
    """时间戳"""
    position: int = 0
    """节点位置 (用于排序)"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440010",
                    "timeline_id": "550e8400-e29b-41d4-a716-446655440011",
                    "event_type": "create",
                    "content": "创建了新记忆",
                    "memory_id": "550e8400-e29b-41d4-a716-446655440000",
                    "cluster_id": None,
                    "timestamp": "2026-04-16T10:00:00",
                    "position": 1,
                    "metadata": {
                        "source": "user",
                        "session_id": "session-123"
                    }
                }
            ]
        }
    }


class ConversationMetadata(BaseModel):
    """Conversation 元数据"""
    title: Optional[str] = Field(default=None, max_length=200)
    """对话标题"""
    participants: list[str] = Field(default_factory=list)
    """参与者列表"""
    session_id: Optional[str] = None
    """会话 ID"""
    extra: dict[str, Any] = Field(default_factory=dict)
    """额外元数据"""


class ConversationBase(BaseModel):
    """Conversation 基础模型"""
    title: Optional[str] = Field(default=None, max_length=200)
    """对话标题"""
    participants: list[str] = Field(default_factory=list)
    """参与者"""
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata)
    """元数据"""


class ConversationCreate(ConversationBase):
    """创建 Conversation 请求"""
    pass


class Conversation(ConversationBase):
    """Conversation 完整模型"""
    id: UUID = Field(default_factory=uuid4)
    """唯一标识符"""
    timeline_id: Optional[UUID] = None
    """关联的 Timeline ID"""
    memory_refs: list[UUID] = Field(default_factory=list)
    """引用的 Memory ID 列表"""
    created_at: datetime = Field(default_factory=datetime.now)
    """创建时间"""
    updated_at: datetime = Field(default_factory=datetime.now)
    """更新时间"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440020",
                    "title": "Python 学习讨论",
                    "participants": ["user", "assistant"],
                    "timeline_id": "550e8400-e29b-41d4-a716-446655440021",
                    "memory_refs": [
                        "550e8400-e29b-41d4-a716-446655440000",
                        "550e8400-e29b-41d4-a716-446655440001"
                    ],
                    "created_at": "2026-04-16T10:00:00",
                    "updated_at": "2026-04-16T10:00:00",
                    "metadata": {
                        "title": "Python 学习讨论",
                        "participants": ["user", "assistant"],
                        "session_id": "session-123",
                        "extra": {}
                    }
                }
            ]
        }
    }

    def add_memory_ref(self, memory_id: UUID) -> None:
        """添加 Memory 引用"""
        if memory_id not in self.memory_refs:
            self.memory_refs.append(memory_id)
            self.updated_at = datetime.now()

    def remove_memory_ref(self, memory_id: UUID) -> bool:
        """移除 Memory 引用，返回是否成功"""
        if memory_id in self.memory_refs:
            self.memory_refs.remove(memory_id)
            self.updated_at = datetime.now()
            return True
        return False


class TimelineBase(BaseModel):
    """Timeline 基础模型"""
    conversation_id: Optional[UUID] = None
    """关联的 Conversation ID"""
    title: Optional[str] = Field(default=None, max_length=200)
    """Timeline 标题"""


class TimelineCreate(TimelineBase):
    """创建 Timeline 请求"""
    pass


class Timeline(TimelineBase):
    """Timeline 完整模型"""
    id: UUID = Field(default_factory=uuid4)
    """唯一标识符"""
    conversation_id: Optional[UUID] = None
    """关联的 Conversation ID"""
    created_at: datetime = Field(default_factory=datetime.now)
    """创建时间"""
    updated_at: datetime = Field(default_factory=datetime.now)
    """更新时间"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440030",
                    "conversation_id": "550e8400-e29b-41d4-a716-446655440020",
                    "title": "Python 学习时间线",
                    "created_at": "2026-04-16T10:00:00",
                    "updated_at": "2026-04-16T10:00:00"
                }
            ]
        }
    }


class TimelineRangeQuery(BaseModel):
    """Timeline 范围查询请求"""
    start: datetime
    """开始时间"""
    end: datetime
    """结束时间"""
    event_types: Optional[list[EventType]] = None
    """事件类型过滤 (可选)"""
    memory_id: Optional[UUID] = None
    """Memory ID 过滤 (可选)"""
    limit: int = Field(default=100, ge=1, le=1000)
    """返回数量限制"""


class TimelineStats(BaseModel):
    """Timeline 统计信息"""
    total_nodes: int
    """总节点数"""
    event_distribution: dict[EventType, int]
    """事件类型分布"""
    first_event: Optional[datetime]
    """最早事件时间"""
    last_event: Optional[datetime]
    """最新事件时间"""
    memory_refs_count: int
    """Memory 引用数量"""
    avg_events_per_day: float
    """日均事件数"""


class TimelineExport(BaseModel):
    """Timeline 导出模型"""
    timeline: Timeline
    """Timeline 信息"""
    nodes: list[TimelineNode]
    """节点列表"""
    conversations: list[Conversation]
    """关联的 Conversation"""
    exported_at: datetime = Field(default_factory=datetime.now)
    """导出时间"""
    format_version: str = "1.0"
    """格式版本"""