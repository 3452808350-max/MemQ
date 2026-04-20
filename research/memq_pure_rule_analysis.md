# MemQ 纯规则评分器探索总结

## 实验结果

| 版本 | Spearman ρ | Pearson r | 特点 |
|-----|-----------|-----------|------|
| 原算法 | 0.4431 | 0.91 | 实体密度为主 |
| 信息压缩 v3 | **0.5629** | 0.86 | 概念数/长度 |
| 纯规则 v4 | 0.4192 | 0.56 | 压缩+抽象+因果 |
| 纯规则 v4.1 | 0.2892 | 0.79 | +工作流价值 |
| 纯规则 v4.2 | 0.4192 | 0.88 | 权重优化 |

**最佳纯规则：信息压缩算法（ρ=0.56）**

## 关键发现

### 1. 纯规则的上限

用 8 个样本测试，纯规则最好只能达到 ρ≈0.56。

原因：
- **词典覆盖有限**：无法穷举所有技术概念、专有名词
- **权重难以调优**：人工调参容易过拟合小样本
- **语义理解缺失**：无法理解"最小方案"、"核心逻辑"的价值

### 2. 信息压缩理论最有效

```python
# 核心公式
compression_rate = unique_concepts / (text_length / 20) * 5
```

**为什么有效？**
- 高质量知识 = 短文本包含丰富概念
- 与人类直觉一致："言简意赅"
- 无需复杂词典，只需实体识别

### 3. 纯规则的边界

| 方法 | 预期 ρ | 复杂度 | 可解释性 |
|-----|--------|--------|---------|
| 纯规则（当前） | 0.50-0.60 | 低 | 高 |
| 规则+词典扩展 | 0.60-0.70 | 中 | 高 |
| 规则+机器学习权重 | 0.70-0.80 | 中 | 中 |
| Embedding 相似度 | 0.80+ | 高 | 低 |

## 建议方案

### 方案 A：纯规则优化（推荐短期）

基于**信息压缩算法**，优化以下 3 点：

```python
def score_knowledge_v5(text):
    # 1. 概念识别（扩展词典）
    concepts = extract_concepts(text, dictionary=EXPANDED_DICT)
    proprietary = extract_proprietary_names(text)  # CopilotACPClient
    
    # 2. 信息压缩率（核心）
    compression = len(concepts) / (len(text) / 20) * 5
    
    # 3. 结构奖励（枚举、层级、因果链）
    structure_bonus = detect_patterns(text)  # 顿号列表、L1/L2/L3、→
    
    # 4. 价值修饰词（最小、核心、示例）
    value_boost = detect_value_modifiers(text)
    
    return min(compression + structure_bonus * 0.3 + value_boost * 0.2, 5)
```

**预期效果**：ρ ≈ 0.65

### 方案 B：规则+轻量 ML（推荐中期）

用 100+ 标注样本，学习最优权重：

```python
from sklearn.linear_model import Ridge

# 特征工程
features = [
    concept_density,      # 概念密度
    compression_rate,     # 压缩率
    structure_score,      # 结构分
    actionability,        # 可执行性
    causal_depth,         # 因果深度
]

# 学习权重（可解释）
model = Ridge(alpha=1.0)
model.fit(features, human_scores)
# 输出：各维度权重
```

**预期效果**：ρ ≈ 0.75

### 方案 C：Embedding 相似度（下下策）

```python
# 预定义"高价值知识"的 embedding
high_value_knowledge = [
    "系统性技术框架和方法论",
    "可复用的设计模式和架构",
    "因果链清晰的问题分析",
]
reference_embeddings = [embed(t) for t in high_value_knowledge]

def score_with_embedding(text):
    text_emb = embed(text)
    similarity = max(cos_sim(text_emb, ref) for ref in reference_embeddings)
    return similarity * 5
```

**问题**：
- 成本高（每次评分都要调 Embedding API）
- 不可解释（黑盒）
- 需要大量参考样本

## 下一步建议

### 立即行动（今天）
1. 实施**信息压缩算法**作为 knowledge 类别的基础评分
2. 扩展词典（专有名词、价值修饰词）
3. 收集更多标注样本（目标 50+ knowledge 样本）

### 短期（本周）
1. 用收集的样本训练轻量模型（Ridge/Lasso）
2. 优化权重，目标 ρ > 0.70

### 中期（本月）
1. 如果纯规则无法突破 0.70，考虑轻量 Embedding 方案
2. 或者引入 LLM 辅助评分（成本可控的前提下）

## 核心洞察

> "压缩 + 可迁移 + 因果深度" 的方向是对的，但纯规则的天花板明显。
> 
> 真正的解决方案：**规则做 80%，数据驱动优化最后 20%**。

---

*实验日期：2026-04-20*
*样本数：8 knowledge 样本*
*测试者：River Jiert*
