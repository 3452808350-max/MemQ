# @test_module: test_context_manager
# @ai_generated: true
# @coverage_target: 0.95

import pytest
from openclaw.core.context import (
    HierarchicalContextManager,
    ContextLevel,
    ContextEntry
)

# @test_for: HierarchicalContextManager.set_context
# @test_type: "unit"
# @ai_generated: true
def test_set_context():
    """@purpose: Test setting context"""
    
    # Arrange
    manager = HierarchicalContextManager()
    entry = ContextEntry(
        key="test_key",
        value="test_value",
        level=ContextLevel.SYSTEM
    )
    
    # Act
    import asyncio
    asyncio.run(manager.set_context(entry))
    
    # Assert
    entries = asyncio.run(manager.get_context(ContextLevel.SYSTEM))
    assert len(entries) >= 1

# @test_for: HierarchicalContextManager.get_context
# @test_type: "unit"
# @ai_generated: true
def test_get_context():
    """@purpose: Test getting context"""
    
    # Arrange
    manager = HierarchicalContextManager()
    entry = ContextEntry(
        key="test_key",
        value="test_value",
        level=ContextLevel.MODULE
    )
    
    import asyncio
    asyncio.run(manager.set_context(entry))
    
    # Act
    entries = asyncio.run(manager.get_context(ContextLevel.MODULE, "test_key"))
    
    # Assert
    assert len(entries) == 1
    assert entries[0].value == "test_value"

# @test_for: HierarchicalContextManager.query_context
# @test_type: "unit"
# @ai_generated: true
def test_query_context():
    """@purpose: Test querying context"""
    
    # Arrange
    manager = HierarchicalContextManager()
    
    import asyncio
    asyncio.run(manager.set_context(ContextEntry(
        key="user_preference",
        value="User likes concise responses",
        level=ContextLevel.SYSTEM
    )))
    
    # Act
    results = asyncio.run(manager.query_context(
        query="user preference",
        levels=[ContextLevel.SYSTEM],
        limit=10
    ))
    
    # Assert
    assert len(results) >= 1
