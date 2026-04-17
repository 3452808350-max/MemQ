# MemQ v2 Validation Plan

## 问题分析

### v1 实验验证的缺陷

| 问题 | 表现 | 影响 |
|------|------|------|
| **数据集合成** | 500条人工构造QA，非真实数据 | 无法反映真实场景 |
| **"完美分离"自证** | 规则和数据同一人写 | 循环论证，无说服力 |
| **样本量不足** | Monte Carlo 100次 | 统计显著性存疑 |
| **无用户反馈** | 无真实采纳/拒绝数据 | 无法验证实用性 |
| **无对比基准** | 无与 LanceDB/Chroma 等对比 | 无相对评估 |

## 验证方案

### 1. 真实数据采集

#### 1.1 数据来源

```
数据采集渠道：

┌─────────────────────────────────────────┐
│         OpenClaw Real User Data         │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Memory      │  │ User        │       │
│  │ Queries     │  │ Feedback    │       │
│  │ (自然查询)  │  │ (采纳/拒绝) │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Agent       │  │ Task        │       │
│  │ Session     │  │ Results     │       │
│  │ Logs        │  │ (成功/失败) │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
```

#### 1.2 数据采集策略

```python
class DataCollector:
    """真实数据采集器"""
    
    def __init__(self):
        # 数据库
        self.lancedb = LanceDBVectorStore()
        
        # 采集配置
        self.collection_config = {
            'min_memories': 1000,      # 最小记忆数
            'min_queries': 500,        # 最小查询数
            'collection_period': 7,    # 采集周期（天）
            'anonymize': True,         # 匿名化处理
        }
    
    async def collect_memories(self) -> List[MemoryRecord]:
        """采集真实记忆"""
        memories = []
        
        # 来源 1: OpenClaw 记忆系统
        openclaw_memories = await self.fetch_openclaw_memories()
        memories.extend(openclaw_memories)
        
        # 来源 2: Agent Session Logs
        session_memories = await self.extract_session_memories()
        memories.extend(session_memories)
        
        # 来源 3: Claude Plugin Task Results
        task_memories = await self.extract_task_memories()
        memories.extend(task_memories)
        
        # 匿名化处理
        if self.collection_config['anonymize']:
            memories = [self.anonymize(m) for m in memories]
        
        # 过滤低质量
        memories = [m for m in memories if len(m.content) > 20]
        
        return memories
    
    async def collect_queries(self) -> List[QueryRecord]:
        """采集真实查询"""
        queries = []
        
        # 来源 1: 用户查询日志
        user_queries = await self.fetch_user_queries(days=7)
        queries.extend(user_queries)
        
        # 来源 2: Agent 查询历史
        agent_queries = await self.fetch_agent_queries()
        queries.extend(agent_queries)
        
        # 去重
        queries = self.deduplicate(queries)
        
        return queries
    
    async def collect_feedback(self) -> List[FeedbackRecord]:
        """采集用户反馈"""
        feedbacks = []
        
        # 来源 1: 显式反馈（评分）
        explicit = await self.fetch_explicit_feedback()
        feedbacks.extend(explicit)
        
        # 来源 2: 隐式反馈（采纳/忽略）
        implicit = await self.extract_implicit_feedback()
        feedbacks.extend(implicit)
        
        # 来源 3: 任务成功/失败
        task_feedback = await self.extract_task_feedback()
        feedbacks.extend(task_feedback)
        
        return feedbacks
    
    def anonymize(self, memory: MemoryRecord) -> MemoryRecord:
        """匿名化处理"""
        # 替换敏感信息
        # - 人名 → [USER]
        # - 邮箱 → [EMAIL]
        # - URL → [URL]
        # - 日期 → [DATE]
        
        content = memory.content
        
        # 人名替换
        content = re.sub(r'[A-Z][a-z]+ [A-Z][a-z]+', '[USER]', content)
        
        # 邮箱替换
        content = re.sub(r'\S+@\S+', '[EMAIL]', content)
        
        # URL 替换
        content = re.sub(r'https?://\S+', '[URL]', content)
        
        # 日期替换
        content = re.sub(r'\d{4}-\d{2}-\d{2}', '[DATE]', content)
        
        return MemoryRecord(
            id=memory.id,
            content=content,
            category=memory.category,
            scope='anonymous',
            timestamp=memory.timestamp,
        )
```

#### 1.3 数据质量指标

| 指标 | 目标 | 验证方法 |
|------|------|----------|
| 记忆数 | ≥1000 | 数据库 count |
| 查询数 | ≥500 | 查询日志统计 |
| 反馈数 | ≥200 | 反馈表统计 |
| 类型分布 | 均衡 | 各类型占比 15-25% |
| 噪声比例 | 10-20% | 人工标注验证 |

### 2. A/B 测试框架

#### 2.1 测试设计

```python
class ABTestFramework:
    """A/B 测试框架"""
    
    def __init__(self):
        # 测试配置
        self.test_config = {
            'control': 'baseline',       # 对照组：LanceDB 默认
            'treatment': 'memq_v2',      # 实验组：MemQ v2
            'split_ratio': 0.5,          # 50/50 分流
            'min_sample_size': 1000,     # 最小样本量
            'significance_level': 0.05,  # 显著性水平
            'metrics': ['recall@5', 'recall@10', 'mrr', 'latency'],
        }
        
        # 分流器
        self.splitter = UserSplitter(
            ratio=self.test_config['split_ratio'],
            salt='memq_ab_test_2026'
        )
        
        # 结果收集
        self.results = {
            'control': [],
            'treatment': [],
        }
    
    async def assign_user(self, user_id: str) -> str:
        """用户分组"""
        group = self.splitter.assign(user_id)
        return group
    
    async def run_query(
        self,
        query: str,
        group: str,
        top_k: int = 5
    ) -> QueryResult:
        """执行查询"""
        if group == 'control':
            # 对照组：LanceDB 默认检索
            result = await self.baseline_retrieve(query, top_k)
        else:
            # 实验组：MemQ v2
            result = await self.memq_v2_retrieve(query, top_k)
        
        # 记录结果
        self.results[group].append({
            'query': query,
            'timestamp': time.time(),
            'results': result,
            'metrics': self.calculate_metrics(result),
        })
        
        return result
    
    async def baseline_retrieve(
        self,
        query: str,
        top_k: int
    ) -> List[Dict]:
        """对照组检索（LanceDB 默认）"""
        # 仅向量检索，无质量分加权
        query_vector = await self.get_embedding(query)
        
        results = self.lancedb.table.search(query_vector, 'l1_vector')
        results = results.limit(top_k)
        
        return results.to_pandas()
    
    async def memq_v2_retrieve(
        self,
        query: str,
        top_k: int
    ) -> List[Dict]:
        """实验组检索（MemQ v2）"""
        # 完整 MemQ v2 流程
        return await self.memq_pipeline.retrieve(query, top_k)
    
    def calculate_metrics(self, result: QueryResult) -> Dict:
        """计算指标"""
        # Recall@5: Top5 是否包含相关记忆
        recall_at_5 = 1 if result.has_relevant_in_top_5 else 0
        
        # Recall@10: Top10 是否包含相关记忆
        recall_at_10 = 1 if result.has_relevant_in_top_10 else 0
        
        # MRR: 相关记忆排名倒数
        mrr = 1 / result.first_relevant_rank if result.first_relevant_rank > 0 else 0
        
        # Latency: 检索延迟
        latency = result.latency_ms
        
        return {
            'recall@5': recall_at_5,
            'recall@10': recall_at_10,
            'mrr': mrr,
            'latency': latency,
        }
    
    async def analyze_results(self) -> ABTestResult:
        """分析 A/B 测试结果"""
        control_metrics = self.aggregate_metrics(self.results['control'])
        treatment_metrics = self.aggregate_metrics(self.results['treatment'])
        
        # 统计检验
        significance = self.statistical_test(
            control_metrics,
            treatment_metrics
        )
        
        # 计算改进
        improvement = self.calculate_improvement(
            control_metrics,
            treatment_metrics
        )
        
        return ABTestResult(
            control=control_metrics,
            treatment=treatment_metrics,
            significance=significance,
            improvement=improvement,
        )
    
    def statistical_test(
        self,
        control: Dict,
        treatment: Dict
    ) -> Dict[str, float]:
        """统计显著性检验"""
        from scipy import stats
        
        results = {}
        
        for metric in self.test_config['metrics']:
            # t 检验
            control_values = [r['metrics'][metric] for r in self.results['control']]
            treatment_values = [r['metrics'][metric] for r in self.results['treatment']]
            
            t_stat, p_value = stats.ttest_ind(control_values, treatment_values)
            
            results[metric] = {
                't_stat': t_stat,
                'p_value': p_value,
                'significant': p_value < self.test_config['significance_level'],
            }
        
        return results
    
    def calculate_improvement(
        self,
        control: Dict,
        treatment: Dict
    ) -> Dict[str, float]:
        """计算改进百分比"""
        improvement = {}
        
        for metric in self.test_config['metrics']:
            control_value = control[metric]
            treatment_value = treatment[metric]
            
            if control_value != 0:
                imp = (treatment_value - control_value) / control_value * 100
            else:
                imp = 0
            
            improvement[metric] = imp
        
        return improvement
```

#### 2.2 测试执行流程

```
A/B 测试执行流程：

┌─────────────────────────────────────────┐
│         User Query Request              │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│         User Assignment                  │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Hash(user)  │  │ Split 50/50 │       │
│  └─────────────┘  └─────────────┘       │
│                                         │
│  ┌─────────────┐  ┌─────────────┐       │
│  │ Control     │  │ Treatment   │       │
│  │ Group       │  │ Group       │       │
│  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
┌─────────────┐  ┌─────────────┐
│ Baseline    │  │ MemQ v2     │
│ Retrieve    │  │ Retrieve    │
│ (LanceDB)   │  │ Pipeline    │
└─────────────┘  └─────────────┘
        │               │
        │               │
        └───────┬───────┘
                │
                ▼
┌─────────────────────────────────────────┐
│         Record Results                   │
│  - Query ID                              │
│  - Group                                 │
│  - Metrics (Recall/MRR/Latency)          │
│  - User Feedback (Adopted/Ignored)       │
└─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│         Statistical Analysis             │
│  - t 检验                                │
│  - p 值                                  │
│  - 改进百分比                            │
└─────────────────────────────────────────┘
```

### 3. 指标定义

#### 3.1 主要指标

| 指标 | 定义 | 计算方法 | 目标 |
|------|------|----------|------|
| **Recall@5** | Top5 包含相关记忆的比例 | hits@5 / total_queries | ≥0.80 |
| **Recall@10** | Top10 包含相关记忆的比例 | hits@10 / total_queries | ≥0.85 |
| **MRR** | 平均倒数排名 | Σ(1/rank) / total_queries | ≥0.50 |
| **Latency** | 检索延迟 | mean(latency_ms) | <200ms |
| **Adoption Rate** | 用户采纳率 | adopted / total_shown | ≥0.70 |

#### 3.2 质量评分指标

| 指标 | 定义 | 计算方法 | 目标 |
|------|------|----------|------|
| **误伤率** | 正常记忆被判低质量的比例 | false_negative / total_positive | <5% |
| **噪声识别率** | 噪声被判低质量的比例 | true_negative / total_noise | ≥95% |
| **维度准确率** | 各维度评分与实际相关性一致 | consistency / total | ≥0.80 |

#### 3.3 系统指标

| 指标 | 定义 | 计算方法 | 目标 |
|------|------|----------|------|
| **吞吐量** | QPS | queries / second | ≥10 |
| **缓存命中率** | 查询缓存命中率 | cache_hits / total_queries | ≥60% |
| **可用性** | 服务可用率 | uptime / total_time | ≥99% |

### 4. 人工标注验证

#### 4.1 标注任务设计

```python
class AnnotationTask:
    """人工标注任务"""
    
    def __init__(self):
        # 标注配置
        self.annotation_config = {
            'task_type': 'quality_labeling',
            'samples': 1000,           # 标注样本数
            'annotators': 3,           # 标注员数（交叉验证）
            'labels': ['high', 'medium', 'low', 'noise'],
            'min_agreement': 0.7,      # 最低一致性要求
        }
    
    async def create_annotation_batch(self) -> List[AnnotationSample]:
        """创建标注批次"""
        # 随机抽样
        memories = await self.sample_memories(self.annotation_config['samples'])
        
        # 构建标注样本
        samples = []
        for mem in memories:
            sample = AnnotationSample(
                id=mem.id,
                content=mem.content[:200],  # 截取前200字
                context=mem.category,
                predicted_quality=mem.quality_score,
            )
            samples.append(sample)
        
        return samples
    
    async def collect_annotations(
        self,
        batch: List[AnnotationSample]
    ) -> List[AnnotationResult]:
        """收集标注结果"""
        results = []
        
        # 发送给标注员
        for annotator_id in range(self.annotation_config['annotators']):
            annotations = await self.send_to_annotator(
                batch,
                annotator_id
            )
            results.extend(annotations)
        
        # 聚合标注
        aggregated = self.aggregate_annotations(results)
        
        return aggregated
    
    def aggregate_annotations(
        self,
        results: List[AnnotationResult]
    ) -> List[AnnotationResult]:
        """聚合多个标注员结果"""
        # 按 memory_id 分组
        grouped = {}
        for r in results:
            if r.memory_id not in grouped:
                grouped[r.memory_id] = []
            grouped[r.memory_id].append(r.label)
        
        # 计算一致性
        aggregated = []
        for memory_id, labels in grouped.items():
            # 多数投票
            label_counts = Counter(labels)
            majority_label = label_counts.most_common(1)[0][0]
            
            # 一致性分数
            agreement = label_counts[majority_label] / len(labels)
            
            if agreement >= self.annotation_config['min_agreement']:
                aggregated.append(AnnotationResult(
                    memory_id=memory_id,
                    label=majority_label,
                    agreement=agreement,
                ))
        
        return aggregated
    
    async def validate_quality_scores(
        self,
        annotations: List[AnnotationResult]
    ) -> ValidationResult:
        """验证质量评分"""
        # 对比预测质量分与人工标注
        matches = 0
        total = len(annotations)
        
        for ann in annotations:
            # 获取预测质量分
            memory = await self.get_memory(ann.memory_id)
            predicted = memory.quality_score
            
            # 标注转分数
            actual = self.label_to_score(ann.label)
            
            # 判断是否匹配
            if self.is_match(predicted, actual):
                matches += 1
        
        # 计算准确率
        accuracy = matches / total
        
        return ValidationResult(
            accuracy=accuracy,
            total=total,
            matches=matches,
        )
    
    def label_to_score(self, label: str) -> float:
        """标注转分数"""
        mapping = {
            'high': 0.9,
            'medium': 0.6,
            'low': 0.3,
            'noise': 0.1,
        }
        return mapping.get(label, 0.5)
    
    def is_match(self, predicted: float, actual: float) -> bool:
        """判断是否匹配"""
        # 允许误差 ±0.2
        return abs(predicted - actual) <= 0.2
```

### 5. 对比基准测试

#### 5.1 对比系统选择

| 系统 | 特点 | 对比意义 |
|------|------|----------|
| **LanceDB Default** | 仅向量检索 | 基础基准 |
| **Chroma** | 开源向量数据库 | 竞品对比 |
| **Weaviate** | 企业级向量搜索 | 高端对比 |
| **v1 MemQ** | 原版本 | 自身对比 |

#### 5.2 对比测试流程

```python
class BenchmarkTest:
    """对比基准测试"""
    
    async def run_benchmark(self) -> BenchmarkResult:
        """运行基准测试"""
        results = {}
        
        # 1. LanceDB Default
        results['lancedb'] = await self.test_lancedb_default()
        
        # 2. Chroma
        results['chroma'] = await self.test_chroma()
        
        # 3. MemQ v1
        results['memq_v1'] = await self.test_memq_v1()
        
        # 4. MemQ v2
        results['memq_v2'] = await self.test_memq_v2()
        
        # 对比分析
        comparison = self.compare_results(results)
        
        return BenchmarkResult(
            results=results,
            comparison=comparison,
        )
    
    async def test_lancedb_default(self) -> Dict:
        """测试 LanceDB 默认"""
        # 仅向量检索
        # 无质量分，无 rerank
        
        metrics = []
        for query in self.test_queries:
            start = time.time()
            
            # 检索
            results = await self.lancedb_search(query, k=5)
            
            latency = time.time() - start
            
            # 计算指标
            recall = self.calculate_recall(results, query)
            mrr = self.calculate_mrr(results, query)
            
            metrics.append({
                'recall@5': recall,
                'mrr': mrr,
                'latency': latency * 1000,
            })
        
        return self.aggregate_metrics(metrics)
    
    async def test_memq_v2(self) -> Dict:
        """测试 MemQ v2"""
        metrics = []
        
        for query in self.test_queries:
            start = time.time()
            
            # MemQ v2 完整流程
            results = await self.memq_v2_retrieve(query, k=5)
            
            latency = time.time() - start
            
            # 计算指标
            recall = self.calculate_recall(results, query)
            mrr = self.calculate_mrr(results, query)
            
            metrics.append({
                'recall@5': recall,
                'mrr': mrr,
                'latency': latency * 1000,
            })
        
        return self.aggregate_metrics(metrics)
```

## 验证计划

| 阶段 | 任务 | 时间 | 产出 |
|------|------|------|------|
| **Phase 1** | 数据采集 | 1周 | 1000+ 真实记忆，500+ 查询 |
| **Phase 2** | 人工标注 | 2周 | 1000 标注样本，一致性验证 |
| **Phase 3** | A/B 测试 | 2周 | 对照组 vs 实验组结果 |
| **Phase 4** | 基准对比 | 1周 | 4 系统对比报告 |
| **Phase 5** | 结果分析 | 1周 | 统计报告，改进建议 |

## 验证标准

### 定量标准

| 指标 | v1 | v2 目标 | 验证通过条件 |
|------|-----|---------|--------------|
| Recall@5 | 0.63 | ≥0.80 | p < 0.05，改进 ≥20% |
| Latency | 21s | <200ms | 改进 ≥100x |
| 误伤率 | 20% | <5% | 人工标注验证 |
| 噪声识别 | 80% | ≥95% | 人工标注验证 |

### 定性标准

| 标准 | 验证方法 |
|------|----------|
| 真实数据 | 数据来源可追溯，非合成 |
| 统计显著 | p < 0.05，样本量 ≥1000 |
| 用户满意 | Adoption Rate ≥70% |
| 系统稳定 | 可用性 ≥99% |

## 总结

MemQ v2 验证方案的核心：

1. **真实数据** - OpenClaw 用户数据，非合成
2. **A/B 测试** - 对照组 vs 实验组，统计检验
3. **人工标注** - 1000 样本，交叉验证
4. **对比基准** - LanceDB/Chroma/v1，相对评估
5. **定量标准** - 明确指标，可量化验证

下一步：详见 ROADMAP.md。