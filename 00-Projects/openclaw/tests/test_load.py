# @file: test_load.py
# @module: openclaw.tests.test_load
# @purpose: "Load and stress tests"
# @ai_maintained: true
# @version: "1.0.0"

import pytest
import asyncio
import time
import random
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dss_modules.memory.embedding import EmbeddingGenerator, EmbeddingPool
from dss_modules.index import VectorIndex, InvertedIndex
from dss_modules.gateway import OutputGateway

# ============ Load Tests ============

# @load_test: test_embedding_load_1000
# @purpose: "Load test: 1000 embeddings"
@pytest.mark.load
@pytest.mark.asyncio
async def test_embedding_load_1000():
    """@purpose: Load test 1000 embeddings"""
    
    pool = EmbeddingPool(size=4)
    texts = [f"Load test text {i} for performance testing." for i in range(1000)]
    
    start = time.time()
    embeddings = await pool.generate_batch(texts)
    end = time.time()
    
    assert len(embeddings) == 1000
    
    total_time = end - start
    throughput = 1000 / total_time
    
    print(f"\n=== Load Test: 1000 Embeddings ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {throughput:.2f} embeddings/s")
    print(f"Average: {(total_time * 1000) / 1000:.2f}ms/embedding")
    
    assert throughput > 50  # Should be > 50 embeddings/s

# @load_test: test_embedding_load_10000
# @purpose: "Load test: 10000 embeddings"
@pytest.mark.load
@pytest.mark.asyncio
async def test_embedding_load_10000():
    """@purpose: Load test 10000 embeddings"""
    
    pool = EmbeddingPool(size=8)
    texts = [f"Load test text {i} for performance testing." for i in range(10000)]
    
    start = time.time()
    embeddings = await pool.generate_batch(texts)
    end = time.time()
    
    assert len(embeddings) == 10000
    
    total_time = end - start
    throughput = 10000 / total_time
    
    print(f"\n=== Load Test: 10000 Embeddings ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {throughput:.2f} embeddings/s")
    print(f"Average: {(total_time * 1000) / 10000:.2f}ms/embedding")
    
    assert throughput > 50

# @load_test: test_vector_index_load_10k
# @purpose: "Load test: 10k vectors"
@pytest.mark.load
def test_vector_index_load_10k():
    """@purpose: Load test 10k vectors"""
    
    index = VectorIndex(dimension=1536)
    
    # Add 10,000 vectors
    start = time.time()
    for i in range(10000):
        embedding = [random.random() for _ in range(1536)]
        index.add(f"id{i}", embedding)
    end = time.time()
    
    add_time = end - start
    
    print(f"\n=== Load Test: 10k Vectors ===")
    print(f"Add time: {add_time:.2f}s")
    print(f"Average add: {(add_time * 1000) / 10000:.2f}ms/vector")
    
    # Search test
    start = time.time()
    for i in range(100):
        query = [random.random() for _ in range(1536)]
        index.search(query, top_k=10)
    end = time.time()
    
    search_time = end - start
    
    print(f"Search 100 times: {search_time:.2f}s")
    print(f"Average search: {(search_time * 1000) / 100:.2f}ms/search")
    
    assert len(index.items) == 10000

# @load_test: test_concurrent_search
# @purpose: "Load test: concurrent searches"
@pytest.mark.load
@pytest.mark.asyncio
async def test_concurrent_search():
    """@purpose: Load test concurrent searches"""
    
    index = VectorIndex(dimension=1536)
    
    # Add 10,000 vectors
    for i in range(10000):
        embedding = [random.random() for _ in range(1536)]
        index.add(f"id{i}", embedding)
    
    # Concurrent searches
    async def search_task(task_id):
        query = [random.random() for _ in range(1536)]
        return index.search(query, top_k=10)
    
    start = time.time()
    
    # Run 100 concurrent searches
    tasks = [search_task(i) for i in range(100)]
    results = await asyncio.gather(*tasks)
    
    end = time.time()
    
    total_time = end - start
    throughput = 100 / total_time
    
    print(f"\n=== Load Test: 100 Concurrent Searches ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {throughput:.2f} searches/s")
    
    assert all(len(r) == 10 for r in results)

# ============ Stress Tests ============

# @stress_test: test_embedding_stress
# @purpose: "Stress test: continuous embedding generation"
@pytest.mark.stress
@pytest.mark.asyncio
async def test_embedding_stress():
    """@purpose: Stress test embedding"""
    
    pool = EmbeddingPool(size=4)
    
    total_embeddings = 0
    start = time.time()
    
    # Generate embeddings for 30 seconds
    while (time.time() - start) < 30:
        texts = [f"Stress test {i}." for i in range(100)]
        await pool.generate_batch(texts)
        total_embeddings += 100
    
    end = time.time()
    total_time = end - start
    throughput = total_embeddings / total_time
    
    print(f"\n=== Stress Test: Embedding Generation ===")
    print(f"Duration: {total_time:.2f}s")
    print(f"Total embeddings: {total_embeddings}")
    print(f"Throughput: {throughput:.2f} embeddings/s")
    
    assert throughput > 30  # Should be > 30 embeddings/s

# @stress_test: test_index_stress
# @purpose: "Stress test: continuous index operations"
@pytest.mark.stress
def test_index_stress():
    """@purpose: Stress test index"""
    
    index = VectorIndex(dimension=1536)
    
    total_adds = 0
    total_searches = 0
    
    start = time.time()
    
    # Add and search for 30 seconds
    while (time.time() - start) < 30:
        # Add 100 vectors
        for i in range(100):
            embedding = [random.random() for _ in range(1536)]
            index.add(f"stress_{total_adds}_{i}", embedding)
        total_adds += 100
        
        # Search 10 times
        for i in range(10):
            query = [random.random() for _ in range(1536)]
            index.search(query, top_k=10)
        total_searches += 10
    
    end = time.time()
    total_time = end - start
    
    print(f"\n=== Stress Test: Index Operations ===")
    print(f"Duration: {total_time:.2f}s")
    print(f"Total adds: {total_adds}")
    print(f"Total searches: {total_searches}")
    print(f"Add rate: {total_adds / total_time:.2f} vectors/s")
    print(f"Search rate: {total_searches / total_time:.2f} searches/s")
    
    assert total_adds > 1000
    assert total_searches > 100

# @stress_test: test_gateway_stress
# @purpose: "Stress test: gateway processing"
@pytest.mark.stress
@pytest.mark.asyncio
async def test_gateway_stress():
    """@purpose: Stress test gateway"""
    
    gateway = OutputGateway()
    
    # Long text
    text = " ".join([f"word{i}" for i in range(10000)])
    
    total_processed = 0
    start = time.time()
    
    # Process for 30 seconds
    while (time.time() - start) < 30:
        await gateway.process(text)
        total_processed += 1
    
    end = time.time()
    total_time = end - start
    throughput = total_processed / total_time
    
    print(f"\n=== Stress Test: Gateway Processing ===")
    print(f"Duration: {total_time:.2f}s")
    print(f"Total processed: {total_processed}")
    print(f"Throughput: {throughput:.2f} texts/s")
    
    assert throughput > 50  # Should be > 50 texts/s

# ============ Endurance Tests ============

# @endurance_test: test_embedding_endurance
# @purpose: "Endurance test: 5 minutes continuous"
@pytest.mark.endurance
@pytest.mark.asyncio
async def test_embedding_endurance():
    """@purpose: Endurance test 5 minutes"""
    
    pool = EmbeddingPool(size=4)
    
    total_embeddings = 0
    start = time.time()
    
    # Run for 5 minutes
    while (time.time() - start) < 300:  # 300 seconds = 5 minutes
        texts = [f"Endurance test {i}." for i in range(100)]
        await pool.generate_batch(texts)
        total_embeddings += 100
    
    end = time.time()
    total_time = end - start
    throughput = total_embeddings / total_time
    
    print(f"\n=== Endurance Test: 5 Minutes ===")
    print(f"Duration: {total_time:.2f}s")
    print(f"Total embeddings: {total_embeddings}")
    print(f"Throughput: {throughput:.2f} embeddings/s")
    print(f"Errors: 0")
    
    assert throughput > 20  # Should be > 20 embeddings/s

# ============ Memory Leak Tests ============

# @memory_test: test_memory_leak_embedding
# @purpose: "Memory leak test: embedding"
@pytest.mark.memory
@pytest.mark.asyncio
async def test_memory_leak_embedding():
    """@purpose: Memory leak test"""
    
    import tracemalloc
    tracemalloc.start()
    
    generator = EmbeddingGenerator()
    
    # Generate 1000 embeddings
    for i in range(1000):
        text = f"Memory test {i}."
        await generator.generate(text)
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print(f"\n=== Memory Leak Test: Embedding ===")
    print(f"Current memory: {current / 1024 / 1024:.2f} MB")
    print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
    
    # Should not exceed 500 MB
    assert peak < 500 * 1024 * 1024

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
