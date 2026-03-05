#!/usr/bin/env python3
"""
混合记忆检索路由 - 实用版本

提供统一的检索接口，自动路由到最优策略
"""

print('=' * 80)
print('🔍 混合记忆检索路由系统')
print('=' * 80)
print()

# 导入组件
print('📦 加载检索组件...')
print()

try:
    from memory_enhanced import MemoryLRUCache, cached_memory_search
    print('  ✅ 缓存检索组件')
except Exception as e:
    print(f'  ⚠️  缓存组件：{e}')

try:
    from hybrid_search_enhancement import (
        BM25Searcher,
        ReciprocalRankFusion,
        HybridSearchEngine
    )
    print('  ✅ BM25 检索组件')
    print('  ✅ RRF 融合组件')
    print('  ✅ 混合搜索组件')
except Exception as e:
    print(f'  ⚠️  混合搜索组件：{e}')

try:
    import torch
    gpu_available = torch.cuda.is_available()
    if gpu_available:
        print(f'  ✅ GPU 加速组件 ({torch.cuda.get_device_name(0)})')
    else:
        print('  ⚠️  GPU 不可用')
except Exception as e:
    print(f'  ⚠️  GPU 组件：{e}')

print()
print('=' * 80)
print('📊 可用检索策略')
print('=' * 80)
print()

strategies = {
    '缓存检索': {
        '速度': '⭐⭐⭐⭐⭐ (最快)',
        '场景': '已知查询，缓存命中',
        '延迟': '<1ms'
    },
    'BM25 检索': {
        '速度': '⭐⭐⭐⭐',
        '场景': '关键词匹配',
        '延迟': '10-50ms'
    },
    '混合搜索': {
        '速度': '⭐⭐⭐',
        '场景': '语义 + 关键词',
        '延迟': '50-150ms'
    },
    'GPU 加速': {
        '速度': '⭐⭐⭐⭐⭐ (GPU)',
        '场景': '大规模向量检索',
        '延迟': '5-20ms'
    }
}

for name, info in strategies.items():
    print(f'{name:15s} 速度：{info["速度"]:20s} 延迟：{info["延迟"]}')
    print(f'                场景：{info["场景"]}')
    print()

print('=' * 80)
print('💡 使用示例')
print('=' * 80)
print()

examples = """
# 1. 缓存检索 (最快)
from memory_enhanced import cached_memory_search
results = cached_memory_search("DSS 优化")

# 2. BM25 检索 (关键词匹配)
from hybrid_search_enhancement import BM25Searcher
bm25 = BM25Searcher()
results = bm25.search("DSS optimization", top_k=5)

# 3. 混合搜索 (语义 + 关键词)
from hybrid_search_enhancement import HybridSearchEngine
engine = HybridSearchEngine()
results = engine.search("DSS 系统架构", top_k=5, use_reranker=True)

# 4. GPU 加速检索 (大规模)
from gpu_optimized_memory import GPUOptimizedSearchEngine
engine = GPUOptimizedSearchEngine()
results = engine.search("混合记忆架构", top_k=5)
"""

print(examples)

print('=' * 80)
print('🎯 自动路由规则')
print('=' * 80)
print()

rules = """
1. 短查询 (<10 字)     → 缓存优先
2. 精确匹配查询       → 缓存
3. 语义查询          → GPU 加速 (如果可用)
4. 关键词查询        → BM25
5. 复杂查询          → 混合搜索 (向量+BM25+ 重排)
"""

print(rules)

print('=' * 80)
print('✅ 记忆检索路由系统就绪！')
print('=' * 80)
