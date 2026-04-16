"""
Memory 数据模型

定义 Memory 的核心数据结构，支持向量嵌入和元数据管理。
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryMetadata(BaseModel):
    """Memory 元数据"""
    source: Optional[str] = None
    """来源标识"""
    author: Optional[str] = None
    """作者"""
    priority: Optional[int] = Field(default=None, ge=1, le=10)
    """优先级 (1-10)"""
    extra: dict[str, Any] = Field(default_factory=dict)
    """额外元数据"""


class MemoryBase(BaseModel):
    """Memory 基础模型"""
    content: str = Field(..., min_length=1, max_length=100000)
    """记忆内容文本"""
    tags: list[str] = Field(default_factory=list)
    """标签列表"""
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)
    """元数据"""


class MemoryCreate(MemoryBase):
    """创建 Memory 请求模型"""
    cluster_ids: list[UUID] = Field(default_factory=list)
    """所属 Cluster ID 列表"""


class Memory(MemoryBase):
    """Memory 完整模型"""
    id: UUID = Field(default_factory=uuid4)
    """唯一标识符"""
    cluster_ids: list[UUID] = Field(default_factory=list)
    """所属 Cluster ID 列表"""
    created_at: datetime = Field(default_factory=datetime.now)
    """创建时间"""
    updated_at: datetime = Field(default_factory=datetime.now)
    """更新时间"""
    embedding: Optional[list[float]] = Field(default=None, repr=False)
    """向量嵌入 (内部使用，不序列化到 API)"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "content": "Python asyncio 学习笔记：协程和任务的基本用法",
                    "tags": ["coding", "python", "async"],
                    "cluster_ids": [],
                    "metadata": {
                        "source": "study",
                        "author": "user",
                        "priority": 5
                    },
                    "created_at": "2026-04-16T10:00:00",
                    "updated_at": "2026-04-16T10:00:00"
                }
            ]
        }
    }

    def update_content(self, content: str) -> None:
        """更新内容并自动更新时间戳"""
        self.content = content
        self.updated_at = datetime.now()

    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()

    def remove_tag(self, tag: str) -> bool:
        """移除标签，返回是否成功"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
            return True
        return False

    def add_to_cluster(self, cluster_id: UUID) -> None:
        """添加到 Cluster"""
        if cluster_id not in self.cluster_ids:
            self.cluster_ids.append(cluster_id)
            self.updated_at = datetime.now()

    def remove_from_cluster(self, cluster_id: UUID) -> bool:
        """从 Cluster 移除，返回是否成功"""
        if cluster_id in self.cluster_ids:
            self.cluster_ids.remove(cluster_id)
            self.updated_at = datetime.now()
            return True
        return False


class MemoryUpdate(BaseModel):
    """更新 Memory 请求模型"""
    content: Optional[str] = Field(default=None, min_length=1, max_length=100000)
    tags: Optional[list[str]] = None
    metadata: Optional[MemoryMetadata] = None
    cluster_ids: Optional[list[UUID]] = None


class MemorySearchResult(BaseModel):
    """Memory 搜索结果"""
    memory: Memory
    """匹配的 Memory"""
    score: float = Field(..., ge=0.0, le=1.0)
    """相似度分数 (0-1)"""
    highlights: Optional[dict[str, list[str]]] = None
    """高亮片段"""


class MemoryPoolStats(BaseModel):
    """Memory Pool 统计信息"""
    total_memories: int
    """总记忆数"""
    total_tags: int
    """总标签数"""
    total_clusters: int
    """总 Cluster 数"""
    avg_content_length: float
    """平均内容长度"""
    oldest_memory: Optional[datetime]
    """最早记忆时间"""
    newest_memory: Optional[datetime]
    """最新记忆时间"""
    tag_distribution: dict[str, int]
    """标签分布"""