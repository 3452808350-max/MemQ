#!/usr/bin/env python3
"""
记忆检索路由系统

功能:
1. 智能路由到最优检索策略
2. 支持多种检索方式 (缓存/向量/BM25/混合)
3. 自动选择 GPU/CPU
4. 性能监控和优化
"""

import time
from typing import List, Dict, Optional, Tuple
from enum import Enum


class RetrievalStrategy(Enum):
    """检索策略"""
    CACHE_ONLY = "cache_only"           # 仅缓存 (最快)
    VECTOR_SEARCH = "vector_search"      # 向量检索 (GPU 加速)
    BM25_SEARCH = "bm25_search"          # BM25 全文检索
    HYBRID_SEARCH = "hybrid_search"      # 混合搜索 (向量+BM25+ 重排)
    GPU_ACCELERATED = "gpu_accelerated"  # GPU 加速检索


class MemoryRouter:
    """记忆检索路由器"""
    
    def __init__(self):
        self.cache = None
        self.vector_index = None
        self.bm25_index = None
        self.hybrid_engine = None
        self.gpu_engine = None
        
        self._init_components()
    
    def _init_components(self):
        """初始化各组件"""
        print('🔧 初始化记忆检索路由...')
        
        # 1. 初始化缓存
        try:
            from memory_enhanced import MemoryLRUCache
            self.cache = MemoryLRUCache(maxsize=1000)
            print('  ✅ 缓存组件就绪')
        except Exception as e:
            print(f'  ⚠️  缓存组件：{e}')
        
        # 2. 初始化 BM25
        try:
            from hybrid_search_enhancement import BM25Searcher
            self.bm25_index = BM25Searcher()
            print('  ✅ BM25 组件就绪')
        except Exception as e:
            print(f'  ⚠️  BM25 组件：{e}')
        
        # 3. 初始化混合搜索
        try:
            from hybrid_search_enhancement import HybridSearchEngine
            self.hybrid_engine = HybridSearchEngine()
            print('  ✅ 混合搜索组件就绪')
        except Exception as e:
            print(f'  ⚠️  混合搜索组件：{e}')
        
        # 4. 初始化 GPU 加速
        try:
            import torch
            if torch.cuda.is_available():
                from gpu_optimized_memory import GPUOptimizedSearchEngine
                self.gpu_engine = GPUOptimizedSearchEngine()
                print(f'  ✅ GPU 加速就绪 ({torch.cuda.get_device_name(0)})')
            else:
                print('  ⚠️  GPU 不可用，使用 CPU')
        except Exception as e:
            print(f'  ⚠️  GPU 组件：{e}')
        
        print('✅ 记忆检索路由初始化完成\n')
    
    def route_query(self, 
                   query: str,
                   top_k: int = 5,
                   auto_select: bool = True,
                   strategy: RetrievalStrategy = None) -> List[Dict]:
        """
        路由查询到最优检索策略
        
        Args:
            query: 查询文本
            top_k: 返回数量
            auto_select: 是否自动选择策略
            strategy: 手动指定策略
        
        Returns:
            检索结果列表
        """
        start_time = time.time()
        
        # 自动选择策略
        if auto_select:
            strategy = self._select_strategy(query)
        
        # 执行检索
        results = self._execute_search(query, top_k, strategy)
        
        # 记录性能
        elapsed = time.time() - start_time
        
        print(f'🔍 检索完成:')
        print(f'   策略：{strategy.value}')
        print(f'   耗时：{elapsed*1000:.2f}ms')
        print(f'   结果：{len(results)} 条\n')
        
        return results
    
    def _select_strategy(self, query: str) -> RetrievalStrategy:
        """
        自动选择最优检索策略
        
        规则:
        1. 短查询 (<10 字) → 缓存优先
        2. 精确匹配 → 缓存
        3. 语义查询 → GPU 加速 (如果可用)
        4. 关键词查询 → BM25
        5. 复杂查询 → 混合搜索
        """
        query_len = len(query)
        
        # 规则 1: 短查询 → 缓存
        if query_len < 10 and self.cache:
            return RetrievalStrategy.CACHE_ONLY
        
        # 规则 2: GPU 可用 → GPU 加速
        if self.gpu_engine:
            return RetrievalStrategy.GPU_ACCELERATED
        
        # 规则 3: 混合搜索 (最全面)
        if self.hybrid_engine:
            return RetrievalStrategy.HYBRID_SEARCH
        
        # 规则 4: BM25
        if self.bm25_index:
            return RetrievalStrategy.BM25_SEARCH
        
        # 默认：缓存
        return RetrievalStrategy.CACHE_ONLY
    
    def _execute_search(self, 
                       query: str,
                       top_k: int,
                       strategy: RetrievalStrategy) -> List[Dict]:
        """执行检索"""
        
        if strategy == RetrievalStrategy.CACHE_ONLY:
            return self._search_cache(query, top_k)
        
        elif strategy == RetrievalStrategy.VECTOR_SEARCH:
            return self._search_vector(query, top_k)
        
        elif strategy == RetrievalStrategy.BM25_SEARCH:
            return self._search_bm25(query, top_k)
        
        elif strategy == RetrievalStrategy.HYBRID_SEARCH:
            return self._search_hybrid(query, top_k)
        
        elif strategy == RetrievalStrategy.GPU_ACCELERATED:
            return self._search_gpu(query, top_k)
        
        return []
    
    def _search_cache(self, query: str, top_k: int) -> List[Dict]:
        """缓存检索"""
        if not self.cache:
            return []
        
        # 尝试缓存命中
        result = self.cache.get(f"search:{hash(query)}")
        return [result] if result else []
    
    def _search_vector(self, query: str, top_k: int) -> List[Dict]:
        """向量检索"""
        # TODO: 实现向量索引检索
        return []
    
    def _search_bm25(self, query: str, top_k: int) -> List[Dict]:
        """BM25 检索"""
        if not self.bm25_index:
            return []
        
        results = self.bm25_index.search(query, top_k=top_k)
        return [{'doc_id': doc_id, 'score': score, 'source': 'bm25'} 
                for doc_id, score in results]
    
    def _search_hybrid(self, query: str, top_k: int) -> List[Dict]:
        """混合搜索"""
        if not self.hybrid_engine:
            return []
        
        results = self.hybrid_engine.search(query, top_k=top_k, use_reranker=True)
        return [{'doc_id': doc_id, 'score': score, 'source': 'hybrid'} 
                for doc_id, score, _ in results]
    
    def _search_gpu(self, query: str, top_k: int) -> List[Dict]:
        """GPU 加速检索"""
        if not self.gpu_engine:
            return self._search_hybrid(query, top_k)
        
        results = self.gpu_engine.search(query, top_k=top_k, use_reranker=True)
        return [{'doc_id': doc_id, 'score': score, 'source': 'gpu'} 
                for doc_id, score, _ in results]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = {
            'components': {
                'cache': self.cache is not None,
                'bm25': self.bm25_index is not None,
                'hybrid': self.hybrid_engine is not None,
                'gpu': self.gpu_engine is not None
            },
            'strategies': [s.value for s in RetrievalStrategy]
        }
        return stats


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print('=' * 80)
    print('🔍 记忆检索路由系统测试')
    print('=' * 80)
    print()
    
    # 创建路由器
    router = MemoryRouter()
    
    # 测试查询
    test_queries = [
        "DSS 优化",
        "混合记忆架构",
        "GPU 加速",
        "Minimax 测试",
    ]
    
    print('=' * 80)
    print('🧪 测试查询')
    print('=' * 80)
    print()
    
    for query in test_queries:
        print(f'查询：{query}')
        print('-' * 80)
        
        # 自动路由
        results = router.route_query(query, top_k=5, auto_select=True)
        
        if results:
            print('结果:')
            for i, result in enumerate(results[:3], 1):
                print(f'  {i}. {result.get("doc_id", "N/A")} '
                      f'(score: {result.get("score", 0):.3f}, '
                      f'source: {result.get("source", "N/A")})')
        else:
            print('  ⚠️  无结果')
        
        print()
    
    # 显示统计
    print('=' * 80)
    print('📊 系统统计')
    print('=' * 80)
    print()
    
    stats = router.get_stats()
    print('组件状态:')
    for component, available in stats['components'].items():
        status = '✅' if available else '⚠️'
        print(f'  {status} {component}')
    
    print('\n可用策略:')
    for strategy in stats['strategies']:
        print(f'  - {strategy}')
    
    print()
    print('=' * 80)
    print('✅ 记忆检索路由系统测试完成！')
    print('=' * 80)
