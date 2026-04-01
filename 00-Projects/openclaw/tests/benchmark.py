# @file: benchmark.py
# @module: openclaw.tests.benchmark
# @purpose: "Performance benchmark suite for OpenClaw"
# @ai_maintained: true
# @version: "1.0.0"

import sys
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# @schema: BenchmarkResult
# @ai_readable: true
@dataclass
class BenchmarkResult:
    """@purpose: Benchmark result structure"""
    
    # @field: name
    # @type: str
    name: str
    
    # @field: iterations
    # @type: int
    iterations: int
    
    # @field: total_time
    # @type: float
    total_time: float
    
    # @field: avg_time
    # @type: float
    avg_time: float
    
    # @field: ops_per_second
    # @type: float
    ops_per_second: float
    
    # @field: metadata
    # @type: Dict[str, Any]
    metadata: Dict[str, Any] = None

# @class: CacheBenchmark
# @purpose: "Cache performance benchmark"
# @ai_testable: true
class CacheBenchmark:
    """@summary: Cache benchmark suite"""
    
    # @function: benchmark_sync_cache
    # @purpose: "Benchmark synchronous cache"
    # @input: iterations: int
    # @output: BenchmarkResult
    # @async: true
    # @ai_testable: true
    async def benchmark_sync_cache(self, iterations: int = 1000) -> BenchmarkResult:
        """@purpose: Benchmark sync cache"""
        
        from openclaw.core.cache import CacheManager
        
        cache = CacheManager.get_instance()
        
        start = time.time()
        for i in range(iterations):
            cache.set(f'key_{i}', f'value_{i}')
        set_time = time.time() - start
        
        start = time.time()
        for i in range(iterations):
            cache.get(f'key_{i}')
        get_time = time.time() - start
        
        total_time = set_time + get_time
        avg_time = total_time / (iterations * 2)
        ops_per_second = iterations / total_time
        
        return BenchmarkResult(
            name="Sync Cache",
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            ops_per_second=ops_per_second,
            metadata={
                "set_time": set_time,
                "get_time": get_time,
                "set_avg": set_time / iterations,
                "get_avg": get_time / iterations
            }
        )
    
    # @function: benchmark_async_cache
    # @purpose: "Benchmark asynchronous cache"
    # @input: iterations: int
    # @output: BenchmarkResult
    # @async: true
    # @ai_testable: true
    async def benchmark_async_cache(self, iterations: int = 1000) -> BenchmarkResult:
        """@purpose: Benchmark async cache"""
        
        from openclaw.core.cache.async_cache import AsyncMultiLayerCache
        
        cache = AsyncMultiLayerCache()
        
        start = time.time()
        for i in range(iterations):
            await cache.set(f'key_{i}', f'value_{i}')
        set_time = time.time() - start
        
        start = time.time()
        for i in range(iterations):
            await cache.get(f'key_{i}')
        get_time = time.time() - start
        
        total_time = set_time + get_time
        avg_time = total_time / (iterations * 2)
        ops_per_second = iterations / total_time
        
        return BenchmarkResult(
            name="Async Cache",
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            ops_per_second=ops_per_second,
            metadata={
                "set_time": set_time,
                "get_time": get_time,
                "set_avg": set_time / iterations,
                "get_avg": get_time / iterations
            }
        )
    
    # @function: benchmark_batch_cache
    # @purpose: "Benchmark batch cache operations"
    # @input: iterations: int
    # @output: BenchmarkResult
    # @async: true
    # @ai_testable: true
    async def benchmark_batch_cache(self, iterations: int = 100) -> BenchmarkResult:
        """@purpose: Benchmark batch cache"""
        
        from openclaw.core.cache.async_cache import AsyncMultiLayerCache, AsyncBatchCache
        
        cache = AsyncMultiLayerCache()
        batch = AsyncBatchCache(cache)
        
        start = time.time()
        items = {f'batch_{i}': f'value_{i}' for i in range(iterations)}
        await batch.set_batch(items)
        set_time = time.time() - start
        
        start = time.time()
        keys = [f'batch_{i}' for i in range(iterations)]
        await batch.get_batch(keys)
        get_time = time.time() - start
        
        total_time = set_time + get_time
        avg_time = total_time / (iterations * 2)
        ops_per_second = iterations / total_time
        
        return BenchmarkResult(
            name="Batch Cache",
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            ops_per_second=ops_per_second,
            metadata={
                "set_time": set_time,
                "get_time": get_time,
                "set_avg": set_time / iterations,
                "get_avg": get_time / iterations
            }
        )

# @class: DatabaseBenchmark
# @purpose: "Database performance benchmark"
# @ai_testable: true
class DatabaseBenchmark:
    """@summary: Database benchmark suite"""
    
    # @function: benchmark_connection_pool
    # @purpose: "Benchmark connection pool"
    # @input: iterations: int
    # @output: BenchmarkResult
    # @async: true
    # @ai_testable: true
    async def benchmark_connection_pool(self, iterations: int = 100) -> BenchmarkResult:
        """@purpose: Benchmark connection pool"""
        
        from openclaw.core.db_pool import DatabasePool, PoolConfig
        
        config = PoolConfig(database_path=':memory:', max_connections=10)
        pool = DatabasePool(config)
        await pool.initialize()
        
        # Create table
        await pool.execute('CREATE TABLE test (id INTEGER, value TEXT)')
        
        start = time.time()
        for i in range(iterations):
            await pool.execute('INSERT INTO test VALUES (?, ?)', (i, f'value_{i}'))
        insert_time = time.time() - start
        
        start = time.time()
        for i in range(iterations):
            await pool.execute('SELECT * FROM test WHERE id = ?', (i,))
        select_time = time.time() - start
        
        total_time = insert_time + select_time
        avg_time = total_time / (iterations * 2)
        ops_per_second = iterations / total_time
        
        await pool.close_all()
        
        return BenchmarkResult(
            name="Database Pool",
            iterations=iterations,
            total_time=total_time,
            avg_time=avg_time,
            ops_per_second=ops_per_second,
            metadata={
                "insert_time": insert_time,
                "select_time": select_time,
                "insert_avg": insert_time / iterations,
                "select_avg": select_time / iterations
            }
        )
    
    # @function: benchmark_concurrent_access
    # @purpose: "Benchmark concurrent database access"
    # @input: iterations: int
    # @output: BenchmarkResult
    # @async: true
    # @ai_testable: true
    async def benchmark_concurrent_access(self, iterations: int = 100) -> BenchmarkResult:
        """@purpose: Benchmark concurrent access"""
        
        from openclaw.core.db_pool import DatabasePool, PoolConfig
        
        config = PoolConfig(database_path=':memory:', max_connections=10)
        pool = DatabasePool(config)
        await pool.initialize()
        
        await pool.execute('CREATE TABLE test (id INTEGER, value TEXT)')
        
        async def insert_data(i):
            await pool.execute('INSERT INTO test VALUES (?, ?)', (i, f'value_{i}'))
        
        start = time.time()
        await asyncio.gather(*[insert_data(i) for i in range(iterations)])
        concurrent_time = time.time() - start
        
        avg_time = concurrent_time / iterations
        ops_per_second = iterations / concurrent_time
        
        await pool.close_all()
        
        return BenchmarkResult(
            name="Concurrent Database",
            iterations=iterations,
            total_time=concurrent_time,
            avg_time=avg_time,
            ops_per_second=ops_per_second,
            metadata={
                "concurrent": True,
                "max_connections": config.max_connections
            }
        )

# @class: BenchmarkSuite
# @purpose: "Complete benchmark suite"
# @ai_testable: true
class BenchmarkSuite:
    """@summary: Complete benchmark suite"""
    
    # @attribute: cache_benchmark
    # @type: CacheBenchmark
    cache_benchmark: CacheBenchmark
    
    # @attribute: db_benchmark
    # @type: DatabaseBenchmark
    db_benchmark: DatabaseBenchmark
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize benchmark suite"""
        self.cache_benchmark = CacheBenchmark()
        self.db_benchmark = DatabaseBenchmark()
    
    # @function: run_all
    # @purpose: "Run all benchmarks"
    # @output: Dict[str, BenchmarkResult]
    # @async: true
    # @ai_testable: true
    async def run_all(self) -> Dict[str, BenchmarkResult]:
        """
        @summary: Run all benchmarks
        
        @steps:
          1. Run cache benchmarks
          2. Run database benchmarks
          3. Collect results
        """
        
        results = {}
        
        # @step: 1
        print("Running cache benchmarks...")
        results["sync_cache"] = await self.cache_benchmark.benchmark_sync_cache(1000)
        results["async_cache"] = await self.cache_benchmark.benchmark_async_cache(1000)
        results["batch_cache"] = await self.cache_benchmark.benchmark_batch_cache(100)
        
        # @step: 2
        print("Running database benchmarks...")
        results["db_pool"] = await self.db_benchmark.benchmark_connection_pool(100)
        results["db_concurrent"] = await self.db_benchmark.benchmark_concurrent_access(100)
        
        # @step: 3
        return results
    
    # @function: print_results
    # @purpose: "Print benchmark results"
    # @input: results: Dict[str, BenchmarkResult]
    # @ai_testable: true
    def print_results(self, results: Dict[str, BenchmarkResult]) -> None:
        """@purpose: Print results"""
        
        print("\n" + "=" * 60)
        print("📊 Benchmark Results")
        print("=" * 60)
        
        for name, result in results.items():
            print(f"\n{name}:")
            print(f"  Iterations: {result.iterations}")
            print(f"  Total Time: {result.total_time*1000:.2f}ms")
            print(f"  Avg Time: {result.avg_time*1000:.3f}ms")
            print(f"  Ops/Second: {result.ops_per_second:.2f}")
            
            if result.metadata:
                print("  Details:")
                for key, value in result.metadata.items():
                    if isinstance(value, float):
                        print(f"    {key}: {value:.3f}")
                    else:
                        print(f"    {key}: {value}")
        
        print("\n" + "=" * 60)

# @function: main
# @purpose: "Main entry point"
# @ai_testable: true
async def main():
    """@purpose: Run benchmarks"""
    
    print("=" * 60)
    print("🧪 OpenClaw Performance Benchmark")
    print("=" * 60)
    print()
    
    suite = BenchmarkSuite()
    results = await suite.run_all()
    suite.print_results(results)
    
    print()
    print("✅ Benchmark complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
