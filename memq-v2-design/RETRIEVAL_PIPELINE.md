# MemQ v2 Retrieval Pipeline Optimization

## 问题分析

### v1 检索流程的缺陷

| 问题 | 表现 | 影响 |
|------|------|------|
| **Rerank 实现错误** | 逐个调用 API，当对话任务处理 | 性能极差，20+秒延迟 |
| **向量检索无索引** | O(n) 遍历所有向量 | 内存爆炸，延迟线性增长 |
| **错误处理薄弱** | 吞异常，无降级 | 单点故障导致全流程失败 |
| **并发缺失** | 单进程串行 | 无法利用并发优势 |
| **缓存设计幼稚** | 内存 Dict + JSON | 无驱逐，无版本感知 |

### 性能瓶颈分析

```
v1 检索流程延迟分解：

1. BM25 检索        ~50ms   ✅ OK
2. 向量检索         ~500ms  ❌ O(n) 遍历
3. RRF 融合         ~10ms   ✅ OK
4. Rerank (20个)    ~20s    ❌ 逐个调用
5. 质量加权         ~10ms   ✅ OK
6. 层加载           ~50ms   ✅ OK

总延迟：             ~21s    ❌ 无法接受

目标延迟：           <200ms  需要 100x 提升
```

## 优化方案

### 1. LanceDB 向量索引

#### 1.1 索引类型选择

```python
"""
LanceDB 索引类型对比

| 类型 | 建索引速度 | 检索速度 | 内存占用 | 适用场景 |
|------|-----------|---------|---------|---------|
| Flat | 无 | O(n) | 高 | <1K 向量 |
| IVF | 中 | O(√n) | 中 | 1K-100K |
| IVF_PQ | 快 | O(log n) | 低 | >100K |
| HNSW | 慢 | O(log n) | 高 | 高精度场景 |

MemQ v2 选择：IVF_PQ（平衡速度和内存）
"""
```

#### 1.2 LanceDB 存储设计

```python
import lancedb
from lancedb.embeddings import EmbeddingFunctionRegistry
from lancedb.pydantic import LanceModel, Vector


class MemorySchema(LanceModel):
    """记忆表结构"""
    
    # 主键
    id: str
    
    # 内容（三层）
    l0_abstract: str
    l1_overview: str
    l2_content: str
    
    # 向量（三层）
    l0_vector: Vector(1024)  # Qwen3-Embedding 维度
    l1_vector: Vector(1024)
    l2_vector: Vector(1024)
    
    # 元数据
    category: str
    scope: str
    importance: float
    
    # 质量评分
    quality_score: float
    quality_dimensions: dict  # JSON string
    
    # 时间戳
    created_at: int
    updated_at: int
    access_count: int


class LanceDBVectorStore:
    """LanceDB 向量存储"""
    
    def __init__(self, db_path: str = "/home/kyj/.openclaw/workspace/memq/db"):
        self.db = lancedb.connect(db_path)
        self.table = None
        
        # 索引配置
        self.index_config = {
            'type': 'IVF_PQ',
            'num_partitions': 256,    # IVF 分区数
            'num_sub_vectors': 64,    # PQ 子向量数
            'nprobe': 20,             # 检索时探测分区数
        }
    
    async def initialize(self) -> None:
        """初始化表和索引"""
        # 创建表（如果不存在）
        if 'memories' not in self.db.table_names():
            self.table = self.db.create_table(
                'memories',
                schema=MemorySchema,
                mode='create'
            )
            
            # 创建向量索引（三层）
            await self.create_vector_indexes()
        else:
            self.table = self.db.open_table('memories')
    
    async def create_vector_indexes(self) -> None:
        """创建向量索引"""
        # L0 索引
        self.table.create_index(
            'l0_vector',
            index_type='IVF_PQ',
            num_partitions=self.index_config['num_partitions'],
            num_sub_vectors=self.index_config['num_sub_vectors'],
        )
        
        # L1 索引
        self.table.create_index(
            'l1_vector',
            index_type='IVF_PQ',
            num_partitions=self.index_config['num_partitions'],
            num_sub_vectors=self.index_config['num_sub_vectors'],
        )
        
        # L2 索引（可选，延迟创建）
        # await self.create_l2_index_if_needed()
    
    async def add_memory(self, memory: Memory) -> str:
        """添加记忆"""
        # 构建记录
        record = MemorySchema(
            id=memory.id,
            l0_abstract=memory.l0_abstract,
            l1_overview=memory.l1_overview,
            l2_content=memory.l2_content,
            l0_vector=await self.get_embedding(memory.l0_abstract),
            l1_vector=await self.get_embedding(memory.l1_overview),
            l2_vector=await self.get_embedding(memory.l2_content),
            category=memory.category,
            scope=memory.scope,
            importance=memory.importance,
            quality_score=memory.quality_score,
            quality_dimensions=json.dumps(memory.quality_dimensions),
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            access_count=memory.access_count,
        )
        
        # 添加到表
        self.table.add([record])
        
        return memory.id
    
    async def vector_search(
        self,
        query_vector: List[float],
        layer: str = 'l1',
        k: int = 50,
        min_quality: float = 0.4,
        scope_filter: Optional[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        向量检索
        
        Args:
            query_vector: 查询向量
            layer: 检索层（l0/l1/l2）
            k: 返回数量
            min_quality: 最低质量分
            scope_filter: Scope 过滤
        
        Returns:
            [(memory_id, similarity), ...]
        """
        # 选择向量列
        vector_col = f'{layer}_vector'
        
        # 构建查询
        query = self.table.search(query_vector, vector_col)
        
        # 应用过滤
        if min_quality > 0:
            query = query.where(f'quality_score >= {min_quality}')
        
        if scope_filter:
            scopes = ', '.join(f"'{s}'" for s in scope_filter)
            query = query.where(f'scope IN ({scopes})')
        
        # 设置返回数量
        query = query.limit(k)
        
        # 设置探测分区数（控制精度/速度平衡）
        query = query.nprobe(self.index_config['nprobe'])
        
        # 执行查询
        results = query.to_pandas()
        
        # 解析结果
        return [
            (row['id'], row['_distance'])
            for row in results.itertuples()
        ]
    
    async def get_embedding(self, text: str) -> List[float]:
        """获取向量（带缓存）"""
        # 从缓存获取
        cache_key = f'emb:{hashlib.md5(text.encode()).hexdigest()}'
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # 调用 Embedding API
        embedding = await self.embedding_api.embed(text)
        
        # 存入缓存
        await self.cache.set(cache_key, embedding, ttl=7*24*3600)  # 7天
        
        return embedding
    
    async def update_quality(self, memory_id: str, quality_score: float) -> bool:
        """更新质量分"""
        # LanceDB 支持 upsert
        self.table.update(
            where=f'id = "{memory_id}"',
            values={'quality_score': quality_score, 'updated_at': int(time.time())}
        )
        return True
    
    async def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_count': self.table.count_rows(),
            'index_status': self.table.index_status(),
            'size_mb': self.table.size() / 1024 / 1024,
        }
```

#### 1.3 索引维护

```python
class IndexManager:
    """索引管理器"""
    
    def __init__(self, store: LanceDBVectorStore):
        self.store = store
        self.reindex_threshold = 1000  # 新增 1000 条后重建索引
    
    async def check_reindex_needed(self) -> bool:
        """检查是否需要重建索引"""
        stats = await self.store.get_stats()
        
        # 索引状态检查
        index_stats = stats['index_status']
        
        # 如果索引碎片化严重
        if index_stats.get('fragmentation', 0) > 0.3:
            return True
        
        # 如果新增记录过多
        if stats['total_count'] > self.last_reindex_count + self.reindex_threshold:
            return True
        
        return False
    
    async def reindex(self) -> None:
        """重建索引"""
        # 记录日志
        logger.info('Starting index rebuild...')
        
        # LanceDB 会自动优化
        # 但可以手动触发
        self.store.table.optimize()
        
        # 更新计数
        stats = await self.store.get_stats()
        self.last_reindex_count = stats['total_count']
        
        logger.info('Index rebuild complete.')
    
    async def run_maintenance_loop(self) -> None:
        """定时维护"""
        while True:
            if await self.check_reindex_needed():
                await self.reindex()
            
            await asyncio.sleep(3600)  # 1小时检查一次
```

### 2. 批处理 Rerank

#### 2.1 批处理 API 设计

```python
class BatchReranker:
    """批处理 Reranker"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "modelscope.cn/dengcao/Qwen3-Reranker-0.6B-GGUF"
        
        # 批处理配置
        self.batch_size = 20  # 单批最大数量
        self.timeout = 30     # 超时时间
    
    async def rerank_batch(
        self,
        query: str,
        candidates: List[Tuple[str, str]]  # (memory_id, content)
    ) -> List[Tuple[str, float]]:
        """
        批处理 Rerank
        
        Args:
            query: 查询文本
            candidates: [(id, content), ...]
        
        Returns:
            [(id, score), ...] 按分数排序
        """
        # v2 核心：单次 API 调用处理所有候选
        
        # 构造批处理请求
        # 注意：Ollama Reranker 需要特殊格式
        
        # 方法 1: 使用专门的 Rerank API（如果支持）
        if self.supports_batch_rerank():
            return await self.batch_rerank_api(query, candidates)
        
        # 方法 2: 使用评分 API（通用）
        return await self.batch_score_api(query, candidates)
    
    async def batch_rerank_api(
        self,
        query: str,
        candidates: List[Tuple[str, str]]
    ) -> List[Tuple[str, float]]:
        """使用 Rerank API（如果支持）"""
        # 准备文档列表
        docs = [c[1][:1000] for c in candidates]  # 限制长度
        
        # 构造请求
        request_data = {
            'model': self.model,
            'query': query,
            'documents': docs,
            'top_k': len(docs),
            'return_documents': False,
        }
        
        # 发送请求
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.ollama_url}/api/rerank",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    result = await response.json()
                    
                    # 解析结果
                    # 格式: [{'index': 0, 'relevance_score': 0.9}, ...]
                    scores = result.get('results', [])
                    
                    # 组合结果
                    reranked = [
                        (candidates[i][0], scores[i]['relevance_score'])
                        for i in range(len(scores))
                    ]
                    
                    # 按分数排序
                    reranked.sort(key=lambda x: x[1], reverse=True)
                    
                    return reranked
                    
            except aiohttp.ClientError as e:
                logger.warning(f'Rerank API failed: {e}')
                # 降级：返回原始顺序
                return [(c[0], 0.5) for c in candidates]
    
    async def batch_score_api(
        self,
        query: str,
        candidates: List[Tuple[str, str]]
    ) -> List[Tuple[str, float]]:
        """使用评分 API（通用方法）"""
        # 构造评分 prompt
        # 一次性评分所有候选
        
        prompt = self.build_score_prompt(query, candidates)
        
        # 发送请求
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        'model': self.model,
                        'prompt': prompt,
                        'stream': False,
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    result = await response.json()
                    output = result.get('response', '')
                    
                    # 解析分数
                    scores = self.parse_scores(output, len(candidates))
                    
                    # 组合结果
                    reranked = [
                        (candidates[i][0], scores[i])
                        for i in range(len(scores))
                    ]
                    
                    # 按分数排序
                    reranked.sort(key=lambda x: x[1], reverse=True)
                    
                    return reranked
                    
            except aiohttp.ClientError as e:
                logger.warning(f'Score API failed: {e}')
                return [(c[0], 0.5) for c in candidates]
    
    def build_score_prompt(
        self,
        query: str,
        candidates: List[Tuple[str, str]]
    ) -> str:
        """构造评分 prompt"""
        prompt = "Rate the relevance of each document to the query.\n"
        prompt += f"Query: {query}\n\n"
        
        for i, (_, content) in enumerate(candidates[:self.batch_size]):
            prompt += f"Document {i+1}: {content[:500]}\n\n"
        
        prompt += "Output relevance scores as JSON array: [score1, score2, ...] "
        prompt += "where each score is 0.0-1.0.\n"
        prompt += "Scores:"
        
        return prompt
    
    def parse_scores(self, output: str, expected_count: int) -> List[float]:
        """解析分数"""
        try:
            # 尝试解析 JSON
            match = re.search(r'\[.*?\]', output)
            if match:
                scores = json.loads(match.group(0))
                # 验证数量
                if len(scores) == expected_count:
                    return [max(0.0, min(1.0, float(s))) for s in scores]
            
            # 备用：逐个解析
            scores = []
            for match in re.finditer(r'(\d*\.?\d+)', output):
                score = float(match.group(1))
                scores.append(max(0.0, min(1.0, score)))
            
            if len(scores) >= expected_count:
                return scores[:expected_count]
            
            # 降级：默认分数
            return [0.5] * expected_count
            
        except Exception as e:
            logger.warning(f'Score parsing failed: {e}')
            return [0.5] * expected_count
    
    def supports_batch_rerank(self) -> bool:
        """检查是否支持批处理 Rerank API"""
        # 检查 API 是否支持
        # 暂时返回 False，使用通用方法
        return False
```

#### 2.2 Rerank 结果缓存

```python
class RerankCache:
    """Rerank 结果缓存"""
    
    def __init__(self, ttl: int = 3600):  # 1小时 TTL
        self.cache: Dict[str, List[Tuple[str, float]]] = {}
        self.timestamps: Dict[str, int] = {}
        self.ttl = ttl
    
    def get(self, query: str, candidate_ids: List[str]) -> Optional[List[Tuple[str, float]]]:
        """获取缓存"""
        # 缓存 key：query + candidate_ids hash
        key = self._make_key(query, candidate_ids)
        
        # 检查是否存在
        if key not in self.cache:
            return None
        
        # 检查 TTL
        if time.time() - self.timestamps[key] > self.ttl:
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        return self.cache[key]
    
    def set(self, query: str, candidate_ids: List[str], results: List[Tuple[str, float]]) -> None:
        """设置缓存"""
        key = self._make_key(query, candidate_ids)
        self.cache[key] = results
        self.timestamps[key] = time.time()
    
    def _make_key(self, query: str, candidate_ids: List[str]) -> str:
        """生成缓存 key"""
        # 组合 query 和候选 ID
        combined = f"{query}:{','.join(sorted(candidate_ids))}"
        return hashlib.md5(combined.encode()).hexdigest()
```

### 3. 异步并发检索

#### 3.1 并发检索 Pipeline

```python
class AsyncRetrievalPipeline:
    """异步并发检索 Pipeline"""
    
    def __init__(
        self,
        vector_store: LanceDBVectorStore,
        bm25_retriever: BM25Retriever,
        reranker: BatchReranker,
        quality_scorer: QualityScorer
    ):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever
        self.reranker = reranker
        self.quality_scorer = quality_scorer
        
        # 缓存
        self.query_cache = QueryCache()
        self.rerank_cache = RerankCache()
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        layer: str = 'l1',
        min_quality: float = 0.4
    ) -> List[Dict]:
        """
        异步检索
        
        目标延迟：<200ms
        """
        # Step 1: 检查 Query Cache (~1ms)
        cached = await self.query_cache.get(query, top_k, layer)
        if cached:
            return cached
        
        # Step 2: 并发执行 BM25 + Vector 检索 (~50ms)
        # 使用 asyncio.gather 并发
        query_vector = await self.vector_store.get_embedding(query)
        
        bm25_task = asyncio.create_task(
            self.bm25_retriever.async_search(query, k=50)
        )
        vector_task = asyncio.create_task(
            self.vector_store.vector_search(query_vector, layer, k=50, min_quality=min_quality)
        )
        
        # 并发等待
        bm25_results, vector_results = await asyncio.gather(
            bm25_task, vector_task
        )
        
        # Step 3: RRF 融合 (~10ms)
        fused = self.rrf_fusion.fuse(bm25_results, vector_results)
        
        # Step 4: 批处理 Rerank (~100ms)
        # 检查 Rerank Cache
        candidate_ids = [r[0] for r in fused[:20]]
        cached_rerank = self.rerank_cache.get(query, candidate_ids)
        
        if cached_rerank:
            reranked = cached_rerank
        else:
            # 准备候选内容
            candidates = [
                (r[0], await self.get_memory_content(r[0], layer))
                for r in fused[:20]
            ]
            
            # 批处理 Rerank
            reranked = await self.reranker.rerank_batch(query, candidates)
            
            # 缓存结果
            self.rerank_cache.set(query, candidate_ids, reranked)
        
        # Step 5: 质量分加权 (~10ms)
        weighted = await self.apply_quality_weights(reranked, min_quality)
        
        # Step 6: 构建结果 (~10ms)
        results = await self.build_results(weighted[:top_k], layer)
        
        # Step 7: 缓存完整结果 (~1ms)
        await self.query_cache.set(query, top_k, layer, results)
        
        return results
    
    async def apply_quality_weights(
        self,
        reranked: List[Tuple[str, float]],
        min_quality: float
    ) -> List[Tuple[str, float]]:
        """应用质量分加权"""
        weighted = []
        
        for memory_id, rerank_score in reranked:
            # 获取质量分（从 LanceDB）
            quality = await self.get_quality_score(memory_id)
            
            if quality >= min_quality:
                # 加权公式
                final_score = rerank_score * (0.5 + 0.5 * quality)
                weighted.append((memory_id, final_score))
        
        # 按最终分数排序
        weighted.sort(key=lambda x: x[1], reverse=True)
        
        return weighted
    
    async def get_quality_score(self, memory_id: str) -> float:
        """获取质量分"""
        # 从 LanceDB 查询
        result = self.vector_store.table.search(
            f'id = "{memory_id}"'
        ).limit(1).to_pandas()
        
        if len(result) > 0:
            return result.iloc[0]['quality_score']
        
        return 0.5  # 默认分数
    
    async def get_memory_content(self, memory_id: str, layer: str) -> str:
        """获取记忆内容"""
        # 从 LanceDB 查询
        result = self.vector_store.table.search(
            f'id = "{memory_id}"'
        ).limit(1).to_pandas()
        
        if len(result) > 0:
            col = f'{layer}_abstract' if layer == 'l0' else \
                  f'{layer}_overview' if layer == 'l1' else \
                  'l2_content'
            return result.iloc[0][col]
        
        return ""
    
    async def build_results(
        self,
        weighted: List[Tuple[str, float]],
        layer: str
    ) -> List[Dict]:
        """构建结果"""
        results = []
        
        for memory_id, score in weighted:
            # 获取完整记忆
            memory = await self.get_memory(memory_id)
            
            results.append({
                'memory_id': memory_id,
                'memory': memory,
                'content': memory.get_content(layer),
                'relevance_score': score,
                'quality_score': memory.quality_score,
                'layer': layer,
                'tokens': memory.get_tokens(layer),
            })
        
        return results
```

#### 3.2 Embedding 请求池

```python
class EmbeddingPool:
    """Embedding 请求池"""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # 请求队列
        self.queue: asyncio.Queue = asyncio.Queue()
        
        # 结果缓存
        self.results: Dict[str, asyncio.Future] = {}
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量获取向量
        
        使用请求池并发处理
        """
        # 创建 Future
        futures = []
        for text in texts:
            key = self._hash_text(text)
            
            if key in self.results:
                # 已有相同请求，共享结果
                futures.append(self.results[key])
            else:
                # 新请求
                future = asyncio.Future()
                self.results[key] = future
                futures.append(future)
                
                # 加入队列
                await self.queue.put((key, text))
        
        # 启动处理
        await self._process_queue()
        
        # 等待所有结果
        embeddings = await asyncio.gather(*futures)
        
        return embeddings
    
    async def _process_queue(self) -> None:
        """处理队列"""
        # 并发处理
        workers = [
            asyncio.create_task(self._worker())
            for _ in range(self.max_concurrent)
        ]
        
        # 等待队列清空
        await self.queue.join()
        
        # 停止 workers
        for worker in workers:
            worker.cancel()
    
    async def _worker(self) -> None:
        """Worker 处理单个请求"""
        while True:
            try:
                key, text = await self.queue.get()
                
                # 调用 Embedding API
                embedding = await self._call_api(text)
                
                # 设置结果
                self.results[key].set_result(embedding)
                
                # 标记完成
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # 失败时设置异常
                self.results[key].set_exception(e)
                self.queue.task_done()
    
    async def _call_api(self, text: str) -> List[float]:
        """调用 Embedding API"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.ollama_url}/api/embeddings",
                json={'model': self.model, 'prompt': text},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                result = await response.json()
                return result.get('embedding', [])
    
    def _hash_text(self, text: str) -> str:
        """文本哈希"""
        return hashlib.md5(text.encode()).hexdigest()
```

### 4. 错误处理与降级

#### 4.1 降级策略

```python
class DegradationHandler:
    """降级处理"""
    
    def __init__(self, pipeline: AsyncRetrievalPipeline):
        self.pipeline = pipeline
        
        # 降级级别
        # Level 0: 全功能（默认）
        # Level 1: 跳过 Rerank（Rerank API 失败）
        # Level 2: 仅 BM25（Vector 检索失败）
        # Level 3: 仅质量过滤（所有检索失败）
        self.degradation_level = 0
        
        # 错误计数
        self.error_counts = {
            'vector': 0,
            'rerank': 0,
            'embedding': 0,
        }
        
        # 阈值
        self.error_threshold = 3  # 连续 3 次错误后降级
    
    async def retrieve_with_degradation(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        带降级的检索
        """
        # 检查降级状态
        if self.degradation_level > 0:
            logger.warning(f"Operating in degradation level {self.degradation_level}")
        
        try:
            # 根据降级级别选择策略
            if self.degradation_level == 0:
                return await self._full_retrieve(query, top_k)
            elif self.degradation_level == 1:
                return await self._no_rerank_retrieve(query, top_k)
            elif self.degradation_level == 2:
                return await self._bm25_only_retrieve(query, top_k)
            else:
                return await self._quality_filter_only(query, top_k)
                
        except Exception as e:
            logger.error(f"Retrieve failed: {e}")
            # 升级降级级别
            await self._escalate_degradation()
            
            # 重试
            return await self.retrieve_with_degradation(query, top_k)
    
    async def _full_retrieve(self, query: str, top_k: int) -> List[Dict]:
        """全功能检索"""
        return await self.pipeline.retrieve(query, top_k)
    
    async def _no_rerank_retrieve(self, query: str, top_k: int) -> List[Dict]:
        """跳过 Rerank"""
        # BM25 + Vector + Quality
        # 不执行 Rerank
        return await self.pipeline.retrieve(query, top_k, use_rerank=False)
    
    async def _bm25_only_retrieve(self, query: str, top_k: int) -> List[Dict]:
        """仅 BM25"""
        # 仅 BM25 + Quality
        return await self.pipeline.retrieve(query, top_k, use_vector=False, use_rerank=False)
    
    async def _quality_filter_only(self, query: str, top_k: int) -> List[Dict]:
        """仅质量过滤"""
        # 返回高质量记忆（无检索）
        # 最极端降级
        return await self.pipeline.get_high_quality_memories(top_k)
    
    async def _escalate_degradation(self) -> None:
        """升级降级级别"""
        if self.degradation_level < 3:
            self.degradation_level += 1
            logger.warning(f"Escalated to degradation level {self.degradation_level}")
    
    async def check_recovery(self) -> None:
        """检查是否可以恢复"""
        # 尝试全功能检索（探针）
        try:
            await self._full_retrieve("test query", 1)
            
            # 成功 → 恢复
            if self.degradation_level > 0:
                self.degradation_level -= 1
                logger.info(f"Recovered to degradation level {self.degradation_level}")
            
            # 清空错误计数
            for key in self.error_counts:
                self.error_counts[key] = 0
                
        except Exception as e:
            logger.warning(f"Recovery check failed: {e}")
```

#### 4.2 健康检查

```python
class HealthChecker:
    """健康检查"""
    
    def __init__(self, pipeline: AsyncRetrievalPipeline):
        self.pipeline = pipeline
        self.health_status = {
            'vector_store': 'healthy',
            'bm25': 'healthy',
            'reranker': 'healthy',
            'embedding': 'healthy',
        }
    
    async def check_all(self) -> Dict[str, str]:
        """检查所有组件"""
        # Vector Store
        try:
            await self.pipeline.vector_store.get_stats()
            self.health_status['vector_store'] = 'healthy'
        except Exception:
            self.health_status['vector_store'] = 'unhealthy'
        
        # BM25
        try:
            self.pipeline.bm25_retriever.search("test", 1)
            self.health_status['bm25'] = 'healthy'
        except Exception:
            self.health_status['bm25'] = 'unhealthy'
        
        # Reranker
        try:
            await self.pipeline.reranker.rerank_batch("test", [("id1", "content1")])
            self.health_status['reranker'] = 'healthy'
        except Exception:
            self.health_status['reranker'] = 'unhealthy'
        
        # Embedding
        try:
            await self.pipeline.vector_store.get_embedding("test")
            self.health_status['embedding'] = 'healthy'
        except Exception:
            self.health_status['embedding'] = 'unhealthy'
        
        return self.health_status
    
    async def run_health_loop(self) -> None:
        """定时健康检查"""
        while True:
            await self.check_all()
            
            # 报告状态
            unhealthy = [
                k for k, v in self.health_status.items()
                if v == 'unhealthy'
            ]
            
            if unhealthy:
                logger.warning(f"Unhealthy components: {unhealthy}")
            
            await asyncio.sleep(300)  # 5分钟检查一次
```

## 性能对比

| 组件 | v1 实现 | v2 实现 | 延迟改进 |
|------|---------|---------|----------|
| Vector 检索 | O(n) 遍历 | LanceDB IVF_PQ | 500ms → 20ms (25x) |
| Rerank | 逐个调用 | 批处理 API | 20s → 100ms (200x) |
| Embedding | 串行 | 并发池 | 500ms → 50ms (10x) |
| 总延迟 | 21s | <200ms | **100x** |

## 实现计划

| 组件 | 优先级 | 工作量 | 依赖 |
|------|--------|--------|------|
| LanceDB 迁移 | P0 | 3天 | 无 |
| 批处理 Rerank | P0 | 2天 | LanceDB |
| 异步并发 | P0 | 1天 | LanceDB |
| 错误处理 | P1 | 1天 | 异步并发 |
| 健康检查 | P2 | 0.5天 | 错误处理 |

## 总结

MemQ v2 检索流程优化的核心：

1. **向量索引** - LanceDB IVF_PQ，O(log n) 检索
2. **批处理 Rerank** - 单次 API 调用，100x 性能提升
3. **异步并发** - Promise.all 并发检索，降低延迟
4. **智能缓存** - Query Cache + Rerank Cache
5. **降级策略** - 多级降级，保证可用性

下一步：详见 VALIDATION.md。