# @file: test_index.py
# @module: openclaw.core.index.test_index
# @purpose: "Unit tests for index modules"
# @ai_maintained: true
# @version: "1.0.0"

import pytest
import numpy as np
from datetime import datetime, timedelta
from dss_modules.index import (
    VectorIndex,
    InvertedIndex,
    TemporalIndex,
    IndexFusion,
    VectorItem,
    InvertedItem,
    TemporalItem,
    SearchResult
)

# ============ Vector Index Tests ============

# @test: test_vector_index_init
# @purpose: "Test vector index initialization"
def test_vector_index_init():
    """@purpose: Test init"""
    
    index = VectorIndex(dimension=1536)
    
    assert index.dimension == 1536
    assert index.items == {}
    assert index.vectors.size == 0

# @test: test_vector_index_add
# @purpose: "Test vector index add"
def test_vector_index_add():
    """@purpose: Test add"""
    
    index = VectorIndex(dimension=3)
    
    index.add("id1", [1.0, 2.0, 3.0], {"key": "value"})
    
    assert "id1" in index.items
    assert len(index.vectors) == 1
    assert np.array_equal(index.vectors[0], [1.0, 2.0, 3.0])

# @test: test_vector_index_search
# @purpose: "Test vector index search"
def test_vector_index_search():
    """@purpose: Test search"""
    
    index = VectorIndex(dimension=3)
    
    # Add vectors
    index.add("id1", [1.0, 0.0, 0.0])
    index.add("id2", [0.0, 1.0, 0.0])
    index.add("id3", [0.0, 0.0, 1.0])
    
    # Search
    results = index.search([1.0, 0.0, 0.0], top_k=2)
    
    assert len(results) == 2
    assert results[0][0] == "id1"  # Most similar
    assert results[0][1] > results[1][1]  # Score descending

# @test: test_vector_index_remove
# @purpose: "Test vector index remove"
def test_vector_index_remove():
    """@purpose: Test remove"""
    
    index = VectorIndex(dimension=3)
    index.add("id1", [1.0, 2.0, 3.0])
    
    # Remove
    result = index.remove("id1")
    
    assert result == True
    assert "id1" not in index.items
    assert len(index.vectors) == 0

# @test: test_vector_index_stats
# @purpose: "Test vector index statistics"
def test_vector_index_stats():
    """@purpose: Test stats"""
    
    index = VectorIndex(dimension=1536)
    index.add("id1", [1.0] * 1536)
    index.add("id2", [2.0] * 1536)
    
    stats = index.get_stats()
    
    assert stats['total_vectors'] == 2
    assert stats['dimension'] == 1536
    assert stats['memory_usage_mb'] > 0

# ============ Inverted Index Tests ============

# @test: test_inverted_index_add
# @purpose: "Test inverted index add"
def test_inverted_index_add():
    """@purpose: Test add"""
    
    index = InvertedIndex()
    index.add("doc1", "This is a test document about testing")
    
    assert "doc1" in index.items
    assert "test" in index.index  # Token should be in index

# @test: test_inverted_index_search
# @purpose: "Test inverted index search"
def test_inverted_index_search():
    """@purpose: Test search"""
    
    index = InvertedIndex()
    index.add("doc1", "Python programming language")
    index.add("doc2", "Java programming language")
    index.add("doc3", "Python snake")
    
    # Search for "python"
    results = index.search("python", top_k=2)
    
    assert len(results) >= 1
    assert results[0][0] in ["doc1", "doc3"]

# @test: test_inverted_index_remove
# @purpose: "Test inverted index remove"
def test_inverted_index_remove():
    """@purpose: Test remove"""
    
    index = InvertedIndex()
    index.add("doc1", "test document")
    
    # Remove
    result = index.remove("doc1")
    
    assert result == True
    assert "doc1" not in index.items

# ============ Temporal Index Tests ============

# @test: test_temporal_index_add
# @purpose: "Test temporal index add"
def test_temporal_index_add():
    """@purpose: Test add"""
    
    index = TemporalIndex()
    now = datetime.now()
    
    index.add("id1", now, {"key": "value"})
    
    assert "id1" in index.items
    assert index.items["id1"].timestamp == now

# @test: test_temporal_index_search
# @purpose: "Test temporal index search"
def test_temporal_index_search():
    """@purpose: Test search"""
    
    index = TemporalIndex()
    
    # Add items with different timestamps
    now = datetime.now()
    index.add("id1", now - timedelta(days=2))
    index.add("id2", now - timedelta(days=1))
    index.add("id3", now)
    
    # Search recent
    results = index.get_recent(limit=2)
    
    assert len(results) == 2
    assert results[0][0] == "id3"  # Most recent
    assert results[1][0] == "id2"

# @test: test_temporal_index_time_range
# @purpose: "Test temporal index time range search"
def test_temporal_index_time_range():
    """@purpose: Test time range"""
    
    index = TemporalIndex()
    now = datetime.now()
    
    index.add("id1", now - timedelta(days=2))
    index.add("id2", now - timedelta(days=1))
    index.add("id3", now)
    
    # Search time range
    start = now - timedelta(days=1, hours=12)
    results = index.search(start=start, limit=10)
    
    assert len(results) == 2  # id2 and id3
    assert results[0][0] == "id3"

# ============ Index Fusion Tests ============

# @test: test_index_fusion_rrf
# @purpose: "Test RRF fusion"
def test_index_fusion_rrf():
    """@purpose: Test RRF"""
    
    fusion = IndexFusion()
    
    # Two result lists
    list1 = [("id1", 0.9), ("id2", 0.8), ("id3", 0.7)]
    list2 = [("id2", 0.9), ("id1", 0.8), ("id4", 0.7)]
    
    # RRF fusion
    results = fusion.rrf_fuse([list1, list2], k=60)
    
    assert len(results) == 4
    assert results[0].id in ["id1", "id2"]  # Top should be id1 or id2

# @test: test_index_fusion_weighted
# @purpose: "Test weighted fusion"
def test_index_fusion_weighted():
    """@purpose: Test weighted fusion"""
    
    fusion = IndexFusion()
    
    list1 = [("id1", 1.0), ("id2", 0.5)]
    list2 = [("id2", 1.0), ("id1", 0.5)]
    
    # Weighted fusion (list2 has higher weight)
    results = fusion.weighted_fuse([list1, list2], weights=[0.3, 0.7])
    
    assert results[0].id == "id2"  # id2 should win with higher weight

# @test: test_index_fusion_deduplicate
# @purpose: "Test deduplication"
def test_index_fusion_deduplicate():
    """@purpose: Test deduplication"""
    
    fusion = IndexFusion()
    
    results = [
        SearchResult(id="id1", score=0.9, source="vector"),
        SearchResult(id="id1", score=0.8, source="keyword"),  # Duplicate
        SearchResult(id="id2", score=0.7, source="vector")
    ]
    
    # Deduplicate
    unique = fusion.deduplicate(results)
    
    assert len(unique) == 2
    assert unique[0].id == "id1"
    assert unique[1].id == "id2"

# ============ Integration Tests ============

# @test: test_complete_search_pipeline
# @purpose: "Test complete search pipeline"
def test_complete_search_pipeline():
    """@purpose: Test pipeline"""
    
    # Vector index
    vector_index = VectorIndex(dimension=3)
    vector_index.add("id1", [1.0, 0.0, 0.0])
    vector_index.add("id2", [0.0, 1.0, 0.0])
    
    # Inverted index
    inverted_index = InvertedIndex()
    inverted_index.add("id1", "python programming")
    inverted_index.add("id2", "java programming")
    
    # Fusion
    fusion = IndexFusion()
    
    # Search both
    vector_results = vector_index.search([1.0, 0.0, 0.0], top_k=2)
    inverted_results = inverted_index.search("python", top_k=2)
    
    # Fuse
    fused = fusion.fuse_all([vector_results, inverted_results], method="rrf")
    
    assert len(fused) >= 1
    assert fused[0].id == "id1"  # Should rank highest

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
