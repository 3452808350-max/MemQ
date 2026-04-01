# @file: test_embedding.py
# @module: openclaw.core.memory.test_embedding
# @purpose: "Unit tests for embedding module"
# @ai_maintained: true
# @version: "1.0.0"

import pytest
import asyncio
from dss_modules.memory.embedding import (
    EmbeddingGenerator,
    EmbeddingConfig,
    EmbeddingPool
)

# @test: test_embedding_config
# @purpose: "Test embedding configuration"
def test_embedding_config():
    """@purpose: Test config"""
    
    config = EmbeddingConfig(
        model="text-embedding-3-small",
        dimension=1536,
        cache_enabled=True,
        cache_size=10000
    )
    
    assert config.model == "text-embedding-3-small"
    assert config.dimension == 1536
    assert config.cache_enabled == True
    assert config.cache_size == 10000

# @test: test_embedding_generator_init
# @purpose: "Test embedding generator initialization"
def test_embedding_generator_init():
    """@purpose: Test init"""
    
    generator = EmbeddingGenerator()
    
    assert generator.config.model == "text-embedding-3-small"
    assert generator.config.dimension == 1536
    assert generator.cache == {}

# @test: test_embedding_generator_mock
# @purpose: "Test mock embedding generation"
@pytest.mark.asyncio
async def test_embedding_generator_mock():
    """@purpose: Test mock embedding"""
    
    generator = EmbeddingGenerator()
    
    # Test single generation
    embedding = await generator._mock_embedding("test text")
    
    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)
    assert all(-1 <= x <= 1 for x in embedding)

# @test: test_embedding_cache
# @purpose: "Test embedding cache"
@pytest.mark.asyncio
async def test_embedding_cache():
    """@purpose: Test cache"""
    
    generator = EmbeddingGenerator(
        EmbeddingConfig(cache_enabled=True, cache_size=100)
    )
    
    # First generation (cache miss)
    text = "test text for caching"
    embedding1 = await generator._mock_embedding(text)
    
    # Manually add to cache
    cache_key = generator._get_cache_key(text)
    generator.cache[cache_key] = embedding1
    
    # Second generation (cache hit)
    embedding2 = await generator.generate(text)
    
    assert embedding1 == embedding2
    assert len(generator.cache) == 1

# @test: test_embedding_batch
# @purpose: "Test batch embedding generation"
@pytest.mark.asyncio
async def test_embedding_batch():
    """@purpose: Test batch generation"""
    
    generator = EmbeddingGenerator()
    
    texts = ["text 1", "text 2", "text 3"]
    embeddings = await generator.generate_batch(texts)
    
    assert len(embeddings) == 3
    assert all(len(emb) == 1536 for emb in embeddings)

# @test: test_embedding_pool
# @purpose: "Test embedding pool"
@pytest.mark.asyncio
async def test_embedding_pool():
    """@purpose: Test pool"""
    
    pool = EmbeddingPool(size=4)
    
    assert len(pool.generators) == 4
    assert pool.current_index == 0
    
    # Test round-robin
    gen1 = pool.get_generator()
    gen2 = pool.get_generator()
    
    assert gen1 != gen2
    assert pool.current_index == 2

# @test: test_embedding_pool_batch
# @purpose: "Test pool batch generation"
@pytest.mark.asyncio
async def test_embedding_pool_batch():
    """@purpose: Test pool batch"""
    
    pool = EmbeddingPool(size=2)
    
    texts = ["text 1", "text 2", "text 3", "text 4"]
    embeddings = await pool.generate_batch(texts)
    
    assert len(embeddings) == 4
    assert all(len(emb) == 1536 for emb in embeddings)

# @test: test_embedding_stats
# @purpose: "Test embedding statistics"
def test_embedding_stats():
    """@purpose: Test stats"""
    
    generator = EmbeddingGenerator()
    stats = generator.get_stats()
    
    assert stats['model'] == "text-embedding-3-small"
    assert stats['dimension'] == 1536
    assert stats['cache_size'] == 0
    assert stats['cache_enabled'] == True

# @test: test_embedding_cache_clear
# @purpose: "Test cache clear"
def test_embedding_cache_clear():
    """@purpose: Test cache clear"""
    
    generator = EmbeddingGenerator(
        EmbeddingConfig(cache_enabled=True)
    )
    
    # Add to cache
    generator.cache['key1'] = [1.0, 2.0]
    generator.cache['key2'] = [3.0, 4.0]
    
    # Clear cache
    generator.clear_cache()
    
    assert len(generator.cache) == 0

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
