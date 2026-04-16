"""
Cluster 数据模型

定义 Cluster (记忆群组) 的数据结构，支持层级嵌套和统计信息。
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ClusterStats(BaseModel):
    """Cluster 统计信息"""
    memory_count: int = 0
    """记忆数量"""
    avg_similarity: float = 0.0
    """平均相似度"""
    total_tags: int = 0
    """标签总数"""
    last_activity: Optional[datetime] = None
    """最后活动时间"""


class ClusterBase(BaseModel):
    """Cluster 基础模型"""
    name: str = Field(..., min_length=1, max_length=100)
    """Cluster 名称"""
    description: Optional[str] = Field(default=None, max_length=1000)
    """Cluster 描述"""
    tags: list[str] = Field(default_factory=list)
    """标签列表"""
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    """显示颜色 (十六进制，如 #3498db)"""


class ClusterCreate(ClusterBase):
    """创建 Cluster 请求模型"""
    parent_cluster_id: Optional[UUID] = None
    """父 Cluster ID (用于嵌套)"""
    memory_ids: list[UUID] = Field(default_factory=list)
    """初始 Memory ID 列表"""


class Cluster(ClusterBase):
    """Cluster 完整模型"""
    id: UUID = Field(default_factory=uuid4)
    """唯一标识符"""
    memory_ids: list[UUID] = Field(default_factory=list)
    """包含的 Memory ID 列表"""
    parent_cluster_id: Optional[UUID] = None
    """父 Cluster ID"""
    children: list[UUID] = Field(default_factory=list)
    """子 Cluster ID 列表"""
    created_at: datetime = Field(default_factory=datetime.now)
    """创建时间"""
    updated_at: datetime = Field(default_factory=datetime.now)
    """更新时间"""
    stats: ClusterStats = Field(default_factory=ClusterStats)
    """统计信息"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "name": "工作项目",
                    "description": "工作相关的记忆集合",
                    "tags": ["work", "project"],
                    "color": "#3498db",
                    "memory_ids": [
                        "550e8400-e29b-41d4-a716-446655440002",
                        "550e8400-e29b-41d4-a716-446655440003"
                    ],
                    "parent_cluster_id": None,
                    "children": [],
                    "created_at": "2026-04-16T10:00:00",
                    "updated_at": "2026-04-16T10:00:00",
                    "stats": {
                        "memory_count": 2,
                        "avg_similarity": 0.85,
                        "total_tags": 5,
                        "last_activity": "2026-04-16T10:00:00"
                    }
                }
            ]
        }
    }

    def add_memory(self, memory_id: UUID) -> None:
        """添加 Memory 到 Cluster"""
        if memory_id not in self.memory_ids:
            self.memory_ids.append(memory_id)
            self.stats.memory_count = len(self.memory_ids)
            self.updated_at = datetime.now()
            self.stats.last_activity = datetime.now()

    def remove_memory(self, memory_id: UUID) -> bool:
        """从 Cluster 移除 Memory，返回是否成功"""
        if memory_id in self.memory_ids:
            self.memory_ids.remove(memory_id)
            self.stats.memory_count = len(self.memory_ids)
            self.updated_at = datetime.now()
            return True
        return False

    def add_child(self, child_id: UUID) -> None:
        """添加子 Cluster"""
        if child_id not in self.children:
            self.children.append(child_id)
            self.updated_at = datetime.now()

    def remove_child(self, child_id: UUID) -> bool:
        """移除子 Cluster，返回是否成功"""
        if child_id in self.children:
            self.children.remove(child_id)
            self.updated_at = datetime.now()
            return True
        return False

    def is_root(self) -> bool:
        """是否为根 Cluster"""
        return self.parent_cluster_id is None

    def is_leaf(self) -> bool:
        """是否为叶子 Cluster (无子节点)"""
        return len(self.children) == 0

    def update_stats(self, avg_similarity: float, total_tags: int) -> None:
        """更新统计信息"""
        self.stats.avg_similarity = avg_similarity
        self.stats.total_tags = total_tags
        self.stats.memory_count = len(self.memory_ids)


class ClusterUpdate(BaseModel):
    """更新 Cluster 请求模型"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    tags: Optional[list[str]] = None
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    parent_cluster_id: Optional[UUID] = None


class ClusterTree(BaseModel):
    """Cluster 树结构 (用于展示层级)"""
    cluster: Cluster
    """当前 Cluster"""
    children: list["ClusterTree"] = Field(default_factory=list)
    """子节点"""

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "cluster": {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "name": "根节点",
                        "description": "根 Cluster",
                        "tags": [],
                        "color": "#3498db",
                        "memory_ids": [],
                        "parent_cluster_id": None,
                        "children": ["550e8400-e29b-41d4-a716-446655440002"],
                        "created_at": "2026-04-16T10:00:00",
                        "updated_at": "2026-04-16T10:00:00",
                        "stats": {
                            "memory_count": 0,
                            "avg_similarity": 0.0,
                            "total_tags": 0,
                            "last_activity": None
                        }
                    },
                    "children": [
                        {
                            "cluster": {
                                "id": "550e8400-e29b-41d4-a716-446655440002",
                                "name": "子节点",
                                "description": "子 Cluster",
                                "tags": [],
                                "color": "#2ecc71",
                                "memory_ids": ["550e8400-e29b-41d4-a716-446655440003"],
                                "parent_cluster_id": "550e8400-e29b-41d4-a716-446655440001",
                                "children": [],
                                "created_at": "2026-04-16T10:00:00",
                                "updated_at": "2026-04-16T10:00:00",
                                "stats": {
                                    "memory_count": 1,
                                    "avg_similarity": 0.0,
                                    "total_tags": 0,
                                    "last_activity": None
                                }
                            },
                            "children": []
                        }
                    ]
                }
            ]
        }
    }


# 允许递归模型
ClusterTree.model_rebuild()


class ClusterMergeRequest(BaseModel):
    """合并 Cluster 请求"""
    source_cluster_ids: list[UUID]
    """要合并的源 Cluster ID 列表"""
    target_cluster_id: UUID
    """目标 Cluster ID"""
    keep_source_tags: bool = True
    """是否保留源 Cluster 的标签"""
    new_name: Optional[str] = None
    """新名称 (可选)"""


class ClusterSplitRequest(BaseModel):
    """拆分 Cluster 请求"""
    cluster_id: UUID
    """要拆分的 Cluster ID"""
    split_by: str = Field(..., pattern="^(tag|similarity|manual)$")
    """拆分方式：tag(按标签), similarity(按相似度), manual(手动)"""
    tag_names: Optional[list[str]] = None
    """按标签拆分时的标签列表"""
    similarity_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    """按相似度拆分时的阈值"""