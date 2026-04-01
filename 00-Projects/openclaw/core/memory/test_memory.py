# @test_module: test_memory_manager
# @ai_generated: true
# @coverage_target: 0.95
# @module: openclaw.core.memory.manager

import pytest
import asyncio
from openclaw.core.memory import (
    MemoryManager,
    MemoryConfig,
    MemoryStoreError,
    MemoryNotInitializedError
)

# @test_for: MemoryManager.store
# @test_type: "unit"
# @ai_generated: true
# @priority: "high"
def test_store_memory():
    """@purpose: Test basic memory storage"""
    
    # Arrange
    config = MemoryConfig(database_path=":memory:")
    manager = MemoryManager(config)
    
    # Act
    memory_id = manager.store("test_key", {"data": 123})
    
    # Assert
    assert memory_id is not None
    assert isinstance(memory_id, str)
    assert len(memory_id) > 0

# @test_for: MemoryManager.retrieve
# @test_type: "unit"
# @ai_generated: true
# @priority: "high"
def test_retrieve_memory():
    """@purpose: Test memory retrieval"""
    
    # Arrange
    config = MemoryConfig(database_path=":memory:")
    manager = MemoryManager(config)
    manager.store("key", "value")
    
    # Act
    result = manager.retrieve("key")
    
    # Assert
    assert result == "value"

# @test_for: MemoryManager.retrieve
# @test_type: "unit"
# @ai_generated: true
# @priority: "high"
def test_retrieve_nonexistent_key():
    """@purpose: Test retrieving non-existent key"""
    
    # Arrange
    config = MemoryConfig(database_path=":memory:")
    manager = MemoryManager(config)
    
    # Act
    result = manager.retrieve("nonexistent")
    
    # Assert
    assert result is None

# @test_for: MemoryManager.search
# @test_type: "unit"
# @ai_generated: true
# @priority: "medium"
def test_search_memories():
    """@purpose: Test memory search"""
    
    # Arrange
    config = MemoryConfig(database_path=":memory:")
    manager = MemoryManager(config)
    manager.store("user_name", "Alice")
    manager.store("user_age", "30")
    manager.store("other", "data")
    
    # Act
    results = manager.search("user", limit=10)
    
    # Assert
    assert len(results) >= 2
    assert all("user" in r.key.lower() for r in results)

# @test_for: MemoryManager.delete
# @test_type: "unit"
# @ai_generated: true
# @priority: "medium"
def test_delete_memory():
    """@purpose: Test memory deletion"""
    
    # Arrange
    config = MemoryConfig(database_path=":memory:")
    manager = MemoryManager(config)
    manager.store("key", "value")
    
    # Act
    result = manager.delete("key")
    
    # Assert
    assert result is True
    assert manager.retrieve("key") is None

# @test_for: MemoryManager.clear
# @test_type: "unit"
# @ai_generated: true
# @priority: "medium"
def test_clear_all_memories():
    """@purpose: Test clearing all memories"""
    
    # Arrange
    config = MemoryConfig(database_path=":memory:")
    manager = MemoryManager(config)
    manager.store("key1", "value1")
    manager.store("key2", "value2")
    
    # Act
    count = manager.clear()
    
    # Assert
    assert count == 2
    assert len(manager._store) == 0

# @test_for: MemoryManager.get_stats
# @test_type: "unit"
# @ai_generated: true
# @priority: "low"
def test_get_stats():
    """@purpose: Test getting statistics"""
    
    # Arrange
    config = MemoryConfig(database_path=":memory:")
    manager = MemoryManager(config)
    manager.store("key1", "value1")
    manager.store("key2", "value2")
    
    # Act
    stats = manager.get_stats()
    
    # Assert
    assert stats.total_entries == 2
    assert stats.total_tokens > 0

# @test_for: MemoryManager
# @test_type: "integration"
# @ai_generated: true
# @priority: "high"
def test_full_workflow():
    """@purpose: Test full workflow"""
    
    # Arrange
    config = MemoryConfig(database_path=":memory:")
    manager = MemoryManager(config)
    
    # Act & Assert - Store
    memory_id = manager.store("user", {"name": "Alice", "age": 30})
    assert memory_id is not None
    
    # Act & Assert - Retrieve
    user = manager.retrieve("user")
    assert user["name"] == "Alice"
    assert user["age"] == 30
    
    # Act & Assert - Search
    results = manager.search("Alice")
    assert len(results) >= 1
    
    # Act & Assert - Delete
    deleted = manager.delete("user")
    assert deleted is True
    assert manager.retrieve("user") is None
