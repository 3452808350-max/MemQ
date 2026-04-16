"""
Cluster Memory API 测试

测试 Memory Pool, Cluster Manager, Timeline 的基本功能。
"""

import pytest
from uuid import uuid4

from cluster_memory.src.models.memory import Memory, MemoryCreate
from cluster_memory.src.models.cluster import Cluster, ClusterCreate
from cluster_memory.src.models.timeline import TimelineNode


class TestMemoryModels:
    """测试 Memory 数据模型"""
    
    def test_memory_create(self):
        """测试创建 Memory"""
        memory_create = MemoryCreate(
            content="Test memory content",
            tags=["test", "unit"],
            metadata={"source": "test"}
        )
        assert memory_create.content == "Test memory content"
        assert memory_create.tags == ["test", "unit"]
    
    def test_memory_model(self):
        """测试 Memory 模型"""
        memory = Memory(
            content="Test memory",
            tags=["test"]
        )
        assert memory.id is not None
        assert memory.content == "Test memory"
        assert memory.created_at is not None
    
    def test_memory_update_content(self):
        """测试更新 Memory 内容"""
        memory = Memory(content="Original")
        memory.update_content("Updated")
        assert memory.content == "Updated"
        assert memory.updated_at > memory.created_at
    
    def test_memory_add_tag(self):
        """测试添加标签"""
        memory = Memory(content="Test")
        memory.add_tag("new-tag")
        assert "new-tag" in memory.tags
    
    def test_memory_remove_tag(self):
        """测试移除标签"""
        memory = Memory(content="Test", tags=["tag1", "tag2"])
        result = memory.remove_tag("tag1")
        assert result is True
        assert "tag1" not in memory.tags


class TestClusterModels:
    """测试 Cluster 数据模型"""
    
    def test_cluster_create(self):
        """测试创建 Cluster"""
        cluster_create = ClusterCreate(
            name="Test Cluster",
            description="Test description",
            tags=["test"]
        )
        assert cluster_create.name == "Test Cluster"
    
    def test_cluster_model(self):
        """测试 Cluster 模型"""
        cluster = Cluster(
            name="Test",
            memory_ids=[uuid4()]
        )
        assert cluster.id is not None
        assert cluster.name == "Test"
        assert len(cluster.memory_ids) == 1


class TestTimelineModels:
    """测试 Timeline 数据模型"""
    
    def test_timeline_node(self):
        """测试 Timeline Node"""
        node = TimelineNode(
            event_type="create",
            content="Test event"
        )
        assert node.id is not None
        assert node.event_type == "create"
        assert node.timestamp is not None


# TODO: 添加集成测试（需要数据库连接）
# class TestMemoryPoolService:
#     """测试 Memory Pool 服务"""
#     
#     @pytest.fixture
#     async def memory_pool(self):
#         """创建 Memory Pool 实例"""
#         from cluster_memory.src.services.memory_pool import MemoryPool, MemoryPoolConfig
#         pool = MemoryPool(MemoryPoolConfig(db_path="./test_data"))
#         await pool.initialize()
#         yield pool
#         await pool.close()
#     
#     async def test_add_memory(self, memory_pool):
#         """测试添加 Memory"""
#         memory = await memory_pool.add(MemoryCreate(content="Test"))
#         assert memory.id is not None