# MemQ v2 Quality Scoring Improvement

## 问题分析

### v1 质量评分的缺陷

| 问题 | 表现 | 影响 |
|------|------|------|
| **破坏词粗糙** | "好的"、"让我" 误伤正常对话 | 正常记忆被降权 |
| **权重固定** | 无自适应机制，无反馈调整 | 无法适应不同场景 |
| **类型识别靠关键词** | 漏掉代码片段、结构化内容 | 代码记忆被低估 |
| **无上下文感知** | 不考虑前文、后文关系 | 单句判断误伤 |
| **无反馈闭环** | 无用户采纳/点击记录 | 质量评分无法改进 |

### 典型误伤案例

```
案例 1: 正常对话被误判
原文: "好的，我来帮你实现这个功能。第一步是..."
v1 判断: "好的" → 破坏词 → 降权 0.5
正确判断: 技术指导 → 高质量 → 0.9

案例 2: 代码片段被漏判
原文: "function fetch(url, options) { return fetch(url, options); }"
v1 判断: 无代码关键词 → 0.7
正确判断: 纯代码 → 1.0

案例 3: 上下文感知缺失
原文: "抱歉，这个方案在 MongoDB 中不可行，应该用 Redis。"
v1 判断: "抱歉" → 破坏词 → 降权 0.5
正确判断: 技术建议 → 高质量 → 0.85
```

## 改进方案

### 1. 上下文感知检测

#### 1.1 破坏词位置分析

```python
class ContextAwareDetector:
    """基于位置的破坏词检测"""
    
    def __init__(self):
        # 区分"开头破坏词"和"全局破坏词"
        self.start_destructive = {
            # 开头出现 → 低质量
            '好的', '好滴', '好的呢', '当然', '没问题',
            '让我', '我来', '作为 AI', '作为助手',
            '请问', '有什么可以帮你',
            '抱歉', '对不起', 'Sorry', 'Apologies',
        }
        
        self.global_destructive = {
            # 任何位置出现 → 低质量
            '无法', '不能', '不会', '不知道', '不清楚',
            '作为语言模型', 'as a language model',
            '有人提到', '类似的但不是用于',
        }
    
    def detect(self, text: str) -> Tuple[float, List[str]]:
        """
        返回：(破坏因子, 破坏词列表)
        
        规则：
        1. 开头破坏词只在开头匹配
        2. 全局破坏词在任何位置匹配
        3. 后文有实质内容 → 减轻惩罚
        """
        factors = []
        detected = []
        
        stripped = text.strip()
        
        # 开头破坏词检测
        for word in self.start_destructive:
            if stripped.startswith(word):
                detected.append(word)
                # 后文是否有实质内容？
                remaining = stripped[len(word):].strip()
                if len(remaining) > 50:  # 有实质内容
                    factors.append(0.7)  # 轻度惩罚
                elif len(remaining) > 20:  # 有一些内容
                    factors.append(0.5)  # 中度惩罚
                else:  # 纯模板
                    factors.append(0.2)  # 重度惩罚
        
        # 全局破坏词检测
        for word in self.global_destructive:
            if word in stripped:
                detected.append(word)
                factors.append(0.3)  # 固定惩罚
        
        # 无破坏词 → 正常
        if not factors:
            return 1.0, []
        
        # 多个破坏词叠加
        final_factor = min(factors)  # 取最严重的
        return final_factor, detected
```

#### 1.2 上下文窗口分析

```python
class ContextWindowAnalyzer:
    """上下文窗口分析"""
    
    def analyze(self, memory: Memory, context: List[Memory]) -> float:
        """
        分析记忆在上下文中的角色
        
        Returns:
            上下文因子 (0.5 - 1.2)
        """
        # 获取前后记忆
        prev_mem = context[-1] if context else None
        next_mem = None  # 需要时序信息
        
        # 规则 1: 回答追问 → 高质量
        if prev_mem and self.is_question(prev_mem):
            return 1.2
        
        # 规则 2: 承接前文 → 正常
        if prev_mem and self.is_continuation(memory, prev_mem):
            return 1.0
        
        # 规则 3: 纯模板回复 → 低质量
        if self.is_template_reply(memory, prev_mem):
            return 0.6
        
        return 1.0  # 默认正常
    
    def is_question(self, mem: Memory) -> bool:
        """是否是提问"""
        text = mem.content.strip()
        return text.endswith('?') or text.endswith('？') or \
               any(kw in text for kw in ['如何', '怎么', '为什么', '是否'])
    
    def is_continuation(self, mem: Memory, prev: Memory) -> bool:
        """是否是承接"""
        # 代码连续
        if prev.type == 'code' and mem.type == 'code':
            return True
        
        # 同一话题
        if self.share_topic(mem, prev):
            return True
        
        return False
    
    def is_template_reply(self, mem: Memory, prev: Memory) -> bool:
        """是否是模板回复"""
        text = mem.content.strip()
        
        # 纯模板开场
        templates = [
            '好的，', '好滴，', '当然，', '没问题，',
            '让我', '我来', '作为 AI',
        ]
        
        for tpl in templates:
            if text.startswith(tpl) and len(text) < 30:
                return True
        
        return False
```

### 2. 自适应权重调整

#### 2.1 权重动态调整机制

```python
class AdaptiveWeightAdjuster:
    """自适应权重调整"""
    
    def __init__(self):
        # 初始权重（基于经验）
        self.base_weights = {
            'type': 0.10,
            'length': 0.20,
            'entity': 0.10,
            'destructive': 0.30,
            'template': 0.25,
            'metadata': 0.05,
        }
        
        # 动态权重（基于反馈）
        self.dynamic_weights = dict(self.base_weights)
        
        # 反馈历史
        self.feedback_history = []
        
        # 调整参数
        self.adjustment_rate = 0.1  # 每次调整幅度
        self.min_weight = 0.05
        self.max_weight = 0.50
    
    def adjust(self, feedback: Feedback) -> None:
        """
        根据反馈调整权重
        
        Feedback:
            memory_id: 记忆ID
            user_action: 'adopted' | 'ignored' | 'rejected'
            dimensions: 各维度得分
            predicted_quality: 预测质量分
        """
        self.feedback_history.append(feedback)
        
        # 分析预测误差
        if feedback.user_action == 'adopted':
            # 用户采纳 → 预测正确或低估
            if feedback.predicted_quality < 0.7:
                # 低估 → 提升相关维度权重
                self.boost_underestimated_dimensions(feedback)
        elif feedback.user_action == 'rejected':
            # 用户拒绝 → 预测错误或高估
            if feedback.predicted_quality > 0.5:
                # 高估 → 降低相关维度权重
                self.reduce_overestimated_dimensions(feedback)
        
        # 周期性全局调整
        if len(self.feedback_history) >= 100:
            self.global_adjustment()
    
    def boost_underestimated_dimensions(self, feedback: Feedback) -> None:
        """提升低估维度权重"""
        # 找出得分低的维度（这些维度导致低估）
        low_dims = [
            k for k, v in feedback.dimensions.items()
            if v < 0.7 and self.dynamic_weights[k] > self.min_weight
        ]
        
        for dim in low_dims:
            # 降低该维度权重（因为它误判了）
            self.dynamic_weights[dim] -= self.adjustment_rate
            self.dynamic_weights[dim] = max(
                self.dynamic_weights[dim], self.min_weight
            )
        
        # 补偿：提升其他维度
        remaining_weight = 1.0 - sum(self.dynamic_weights.values())
        other_dims = [k for k in self.dynamic_weights if k not in low_dims]
        
        for dim in other_dims:
            self.dynamic_weights[dim] += remaining_weight / len(other_dims)
    
    def reduce_overestimated_dimensions(self, feedback: Feedback) -> None:
        """降低高估维度权重"""
        # 找出得分高的维度（这些维度导致高估）
        high_dims = [
            k for k, v in feedback.dimensions.items()
            if v > 0.7 and self.dynamic_weights[k] < self.max_weight
        ]
        
        for dim in high_dims:
            # 降低该维度权重
            self.dynamic_weights[dim] -= self.adjustment_rate
            self.dynamic_weights[dim] = max(
                self.dynamic_weights[dim], self.min_weight
            )
        
        # 补偿
        remaining_weight = 1.0 - sum(self.dynamic_weights.values())
        other_dims = [k for k in self.dynamic_weights if k not in high_dims]
        
        for dim in other_dims:
            self.dynamic_weights[dim] += remaining_weight / len(other_dims)
    
    def global_adjustment(self) -> None:
        """全局调整（基于历史数据）"""
        # 统计各维度的预测准确率
        dim_accuracy = self.calculate_dimension_accuracy()
        
        # 按准确率调整权重
        # 准确率高的维度 → 权重提升
        # 准确率低的维度 → 权重降低
        
        total_accuracy = sum(dim_accuracy.values())
        
        for dim, acc in dim_accuracy.items():
            # 按准确率占比分配权重
            target_weight = acc / total_accuracy * 0.6  # 60% 按准确率分配
            current_weight = self.dynamic_weights[dim]
            
            # 渐进调整
            new_weight = current_weight * 0.8 + target_weight * 0.2
            new_weight = max(self.min_weight, min(self.max_weight, new_weight))
            self.dynamic_weights[dim] = new_weight
        
        # 确保总和为 1
        self.normalize_weights()
        
        # 清理历史
        self.feedback_history = self.feedback_history[-50:]  # 保留最近 50 条
    
    def normalize_weights(self) -> None:
        """归一化权重"""
        total = sum(self.dynamic_weights.values())
        for dim in self.dynamic_weights:
            self.dynamic_weights[dim] /= total
    
    def get_weights(self) -> Dict[str, float]:
        """获取当前权重"""
        return dict(self.dynamic_weights)
```

#### 2.2 场景自适应

```python
class ScenarioAwareWeights:
    """场景自适应权重"""
    
    def __init__(self):
        # 不同场景的权重配置
        self.scenario_weights = {
            'coding': {
                'type': 0.20,      # 代码类型更重要
                'length': 0.15,
                'entity': 0.15,    # API/库名更重要
                'destructive': 0.20,
                'template': 0.20,
                'metadata': 0.10,
            },
            'conversation': {
                'type': 0.05,      # 类型不重要
                'length': 0.10,
                'entity': 0.05,
                'destructive': 0.35,  # 破坏词更重要
                'template': 0.40,     # 模板更重要
                'metadata': 0.05,
            },
            'knowledge': {
                'type': 0.15,
                'length': 0.25,    # 详细内容更重要
                'entity': 0.20,    # 实体密度更重要
                'destructive': 0.15,
                'template': 0.15,
                'metadata': 0.10,
            },
            'default': {
                'type': 0.10,
                'length': 0.20,
                'entity': 0.10,
                'destructive': 0.30,
                'template': 0.25,
                'metadata': 0.05,
            },
        }
    
    def detect_scenario(self, query: str) -> str:
        """检测查询场景"""
        # 代码场景
        code_keywords = ['function', 'class', 'import', 'API', 'error', 'bug', 
                        '函数', '类', '错误', 'API']
        if any(kw in query for kw in code_keywords):
            return 'coding'
        
        # 知识场景
        knowledge_keywords = ['如何', '怎么', '为什么', '原理', '教程', 
                             'guide', 'tutorial', 'how to']
        if any(kw in query for kw in knowledge_keywords):
            return 'knowledge'
        
        # 对话场景
        conversation_keywords = ['你好', '谢谢', '帮我', '能否', 
                                'hello', 'help', 'can you']
        if any(kw in query for kw in conversation_keywords):
            return 'conversation'
        
        return 'default'
    
    def get_weights(self, scenario: str) -> Dict[str, float]:
        """获取场景权重"""
        return self.scenario_weights.get(scenario, self.scenario_weights['default'])
```

### 3. 反馈闭环

#### 3.1 反馈收集机制

```typescript
interface FeedbackCollector {
  // 收集渠道
  channels: {
    // 用户点击采纳
    'memory:adopted': (event: MemoryAdoptedEvent) => void;
    
    // 用户明确忽略
    'memory:ignored': (event: MemoryIgnoredEvent) => void;
    
    // 用户标记删除
    'memory:rejected': (event: MemoryRejectedEvent) => void;
    
    // 用户评分（可选）
    'memory:rated': (event: MemoryRatedEvent) => void;
  };
  
  // 反馈存储
  store: FeedbackStore;
  
  // 批量上报
  reporter: FeedbackReporter;
}

interface Feedback {
  memory_id: string;
  timestamp: number;
  
  // 用户行为
  user_action: 'adopted' | 'ignored' | 'rejected' | 'rated';
  
  // 预测质量
  predicted_quality: number;
  dimensions: Record<string, number>;
  
  // 实际反馈（可选）
  actual_quality?: number;  // 用户评分 0-10
  
  // 上下文
  query: string;
  rank: number;  // 检索排名
  total_results: number;
}
```

#### 3.2 反馈聚合与分析

```python
class FeedbackAggregator:
    """反馈聚合器"""
    
    def __init__(self, store: FeedbackStore):
        self.store = store
        self.aggregation_interval = 3600  # 1小时聚合一次
    
    def aggregate(self) -> AggregationResult:
        """聚合反馈数据"""
        # 获取最近的反馈
        feedbacks = self.store.get_recent(hours=1)
        
        # 统计采纳率
        adoption_rate = self.calculate_adoption_rate(feedbacks)
        
        # 统计排名分布
        rank_distribution = self.calculate_rank_distribution(feedbacks)
        
        # 统计维度准确率
        dimension_accuracy = self.calculate_dimension_accuracy(feedbacks)
        
        # 统计场景分布
        scenario_distribution = self.calculate_scenario_distribution(feedbacks)
        
        return AggregationResult(
            adoption_rate=adoption_rate,
            rank_distribution=rank_distribution,
            dimension_accuracy=dimension_accuracy,
            scenario_distribution=scenario_distribution,
            timestamp=time.time(),
        )
    
    def calculate_adoption_rate(self, feedbacks: List[Feedback]) -> float:
        """计算采纳率"""
        adopted = sum(1 for f in feedbacks if f.user_action == 'adopted')
        total = len(feedbacks)
        return adopted / total if total > 0 else 0.5
    
    def calculate_rank_distribution(self, feedbacks: List[Feedback]) -> Dict[int, float]:
        """计算排名分布"""
        # Top 1, Top 3, Top 5, Top 10 的采纳率
        rank_bins = {1: [], 3: [], 5: [], 10: []}
        
        for f in feedbacks:
            for k in rank_bins:
                if f.rank <= k:
                    rank_bins[k].append(f)
        
        return {
            k: sum(1 for f in v if f.user_action == 'adopted') / len(v)
            for k, v in rank_bins.items() if len(v) > 0
        }
    
    def calculate_dimension_accuracy(self, feedbacks: List[Feedback]) -> Dict[str, float]:
        """计算维度准确率"""
        # 对于被采纳的记忆，检查哪些维度得分高
        # 对于被拒绝的记忆，检查哪些维度得分低
        
        dim_scores = {dim: {'correct': 0, 'total': 0} for dim in DIMENSIONS}
        
        for f in feedbacks:
            if f.user_action == 'adopted':
                # 预测正确 → 高维度得分应该确实高
                for dim, score in f.dimensions.items():
                    if score > 0.7:
                        dim_scores[dim]['correct'] += 1
                    dim_scores[dim]['total'] += 1
            elif f.user_action == 'rejected':
                # 预测错误 → 高维度得分不应该高
                for dim, score in f.dimensions.items():
                    if score <= 0.7:
                        dim_scores[dim]['correct'] += 1
                    dim_scores[dim]['total'] += 1
        
        return {
            dim: scores['correct'] / scores['total']
            for dim, scores in dim_scores.items()
            if scores['total'] > 0
        }
```

#### 3.3 反馈驱动的权重更新

```python
class FeedbackDrivenUpdater:
    """反馈驱动的权重更新器"""
    
    def __init__(
        self,
        adjuster: AdaptiveWeightAdjuster,
        aggregator: FeedbackAggregator
    ):
        self.adjuster = adjuster
        self.aggregator = aggregator
        
        # 定时任务
        self.update_interval = 3600  # 1小时更新一次
    
    async def run_update_loop(self) -> None:
        """定时更新循环"""
        while True:
            # 聚合反馈
            aggregation = self.aggregator.aggregate()
            
            # 检查是否有足够数据
            if aggregation.total_feedbacks >= 50:
                # 执行权重调整
                self.adjust_weights(aggregation)
            
            # 等待下一次
            await asyncio.sleep(self.update_interval)
    
    def adjust_weights(self, aggregation: AggregationResult) -> None:
        """根据聚合结果调整权重"""
        current_weights = self.adjuster.get_weights()
        
        # 基于维度准确率调整
        for dim, accuracy in aggregation.dimension_accuracy.items():
            if accuracy > 0.7:
                # 准确率高 → 提升权重
                current_weights[dim] = min(
                    current_weights[dim] + 0.05,
                    0.50  # 最大权重
                )
            elif accuracy < 0.5:
                # 准确率低 → 降低权重
                current_weights[dim] = max(
                    current_weights[dim] - 0.05,
                    0.05  # 最小权重
                )
        
        # 归一化
        total = sum(current_weights.values())
        for dim in current_weights:
            current_weights[dim] /= total
        
        # 更新权重
        self.adjuster.dynamic_weights = current_weights
        
        # 记录调整日志
        self.log_adjustment(aggregation, current_weights)
```

### 4. 类型识别改进

#### 4.1 多特征类型识别

```python
class EnhancedTypeDetector:
    """增强类型识别"""
    
    def __init__(self):
        # 关键词特征
        self.code_keywords = {
            'def ', 'class ', 'import ', 'from ', 'function ', 
            'const ', 'let ', 'var ', 'return ', 'if ', 'else ',
            'async ', 'await ', 'try ', 'catch ', 'throw ',
            '```', '``', '{}', '[]', '()', '->', '::',
        }
        
        # 结构特征
        self.code_patterns = [
            r'def \w+\(',              # Python 函数
            r'function \w+\(',         # JS 函数
            r'class \w+[:\{]',         # 类定义
            r'import .* from',         # 导入
            r'const|let|var \w+ =',    # 变量
            r'<\w+>.*</\w+>',          # HTML/XML 标签
            r'\{[\s\S]*\}',            # 大括号块
            r'\[[\s\S]*\]',            # 数组
            r'\w+\(\w+\)',             # 函数调用
        ]
        
        # 知识特征
        self.knowledge_keywords = {
            '原理', '机制', '步骤', '流程', '方法', '方案',
            '教程', '指南', '文档', '说明',
            'tutorial', 'guide', 'how to', 'step by step',
        }
        
        # 实体特征
        self.entity_patterns = [
            r'https?://\S+',           # URL
            r'\S+@\S+',                # Email
            r'\d{4}-\d{2}-\d{2}',      # 日期
            r'v\d+\.\d+',              # 版本号
            r'[A-Z][a-z]+ [A-Z][a-z]+',# 人名
        ]
    
    def detect_type(self, text: str) -> Tuple[str, float]:
        """
        检测类型
        
        Returns:
            (type, confidence)
        """
        scores = {
            'code': self.score_code(text),
            'knowledge': self.score_knowledge(text),
            'entity': self.score_entity(text),
            'conversation': self.score_conversation(text),
        }
        
        # 找最高得分
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        
        # 置信度判断
        if max_score > 0.8:
            return max_type, max_score
        elif max_score > 0.5:
            # 混合类型
            second_type = sorted(scores, key=scores.get, reverse=True)[1]
            return f"{max_type}/{second_type}", max_score
        else:
            return 'unknown', 0.5
    
    def score_code(self, text: str) -> float:
        """代码得分"""
        score = 0.0
        
        # 关键词检查
        for kw in self.code_keywords:
            if kw in text:
                score += 0.2
        
        # 模式匹配
        for pattern in self.code_patterns:
            if re.search(pattern, text):
                score += 0.15
        
        # 语法特征
        # 高比例特殊字符
        special_ratio = sum(1 for c in text if c in '{}[]()<>') / len(text)
        if special_ratio > 0.1:
            score += 0.2
        
        # 行结构（多行代码）
        lines = text.split('\n')
        if len(lines) > 3:
            # 检查缩进一致性
            indented = [l for l in lines if l.startswith('  ') or l.startswith('\t')]
            if len(indented) > len(lines) * 0.5:
                score += 0.2
        
        return min(score, 1.0)
    
    def score_knowledge(self, text: str) -> float:
        """知识得分"""
        score = 0.0
        
        # 关键词
        for kw in self.knowledge_keywords:
            if kw in text:
                score += 0.2
        
        # 结构特征
        # 分段（标题/小节）
        if re.search(r'#\s+\w+', text):  # Markdown 标题
            score += 0.2
        
        # 列表
        if re.search(r'^\s*[-*]\s+', text, re.MULTILINE):
            score += 0.1
        
        # 步骤编号
        if re.search(r'(步骤|Step)\s*\d+', text):
            score += 0.2
        
        return min(score, 1.0)
    
    def score_entity(self, text: str) -> float:
        """实体得分"""
        score = 0.0
        
        # 实体模式
        for pattern in self.entity_patterns:
            matches = re.findall(pattern, text)
            if matches:
                score += 0.1 * len(matches)
        
        return min(score, 1.0)
    
    def score_conversation(self, text: str) -> float:
        """对话得分"""
        # 默认类型
        # 如果没有明显特征，认为是对话
        return 0.5
```

## 实现计划

| 组件 | 优先级 | 工作量 | 依赖 |
|------|--------|--------|------|
| 上下文感知检测 | P0 | 2天 | 无 |
| 自适应权重调整 | P0 | 3天 | 反馈收集 |
| 反馈闭环 | P1 | 2天 | 存储层 |
| 类型识别改进 | P0 | 1天 | 无 |
| 场景自适应 | P2 | 1天 | 反馈闭环 |

## 验证指标

| 指标 | v1 表现 | v2 目标 | 验证方法 |
|------|---------|---------|----------|
| 误伤率 | 20% | <5% | 人工标注 1000 条 |
| 采纳率 | 60% | >85% | A/B 测试 |
| 准确率 | 70% | >90% | 真实用户反馈 |
| 噪声识别 | 80% | >95% | 人工标注噪声集 |

## 总结

MemQ v2 质量评分改进的核心：

1. **上下文感知** - 破坏词位置分析，避免误伤
2. **自适应权重** - 基于反馈动态调整
3. **反馈闭环** - 用户采纳/忽略驱动改进
4. **类型增强** - 多特征识别，不依赖单一关键词

下一步：详见 RETRIEVAL_PIPELINE.md。