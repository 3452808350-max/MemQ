# 📚 金融预测论文精读计划（14天）

---

## 📅 第1周：基础方法（1-10篇）

### Day 1 (2月17日) ⭐ 入门必读

| 论文 | 方向 | 难度 |
|------|------|------|
| **StockMixer** | MLP架构 | ⭐⭐ |
| **MASTER** | Transformer | ⭐⭐⭐ |

**StockMixer: A Simple yet Strong MLP-based Architecture for Stock Price Forecasting**
- 机构：SJTU-Quant (上海交大)
- 核心：简单MLP架构吊打复杂Transformer
- 要点：
  - 三个 Mixer：时间、股票、特征混合
  - 无注意力机制，计算效率高
  - 在A股票预测上SOTA
  
**MASTER: Market-Guided Stock Transformer**
- 核心：市场状态引导的Transformer
- 要点：
  - 市场Embedding
  - 多尺度时间建模
  - 预测+排序双任务

---

### Day 2 (2月18日) ⭐ 强化学习

| 论文 | 方向 | 难度 |
|------|------|------|
| **DeepScalper** | 日内交易 | ⭐⭐⭐ |
| **FinRL** | 框架 | ⭐⭐ |

**DeepScalper: Risk-Aware Reinforcement Learning for Intraday Trading**
- 核心：日内择时交易
- 要点：
  - Risk-aware RL
  - Actor-Critic架构
  - 处理短暂交易机会

**FinRL: Deep Reinforcement Learning Framework for Quantitative Trading**
- 机构：AI4Finance
- 核心：完整的DRL交易框架
- 要点：
  - 环境模拟
  - 多种算法集成
  - 易于上手

---

### Day 3 (2月19日) ⭐ 图神经网络

| 论文 | 方向 | 难度 |
|------|------|------|
| **HIST** | 图学习 | ⭐⭐⭐ |
| **RTGCN** | 时序图 | ⭐⭐⭐ |

**HIST: Graph-based Framework for Stock Trend Forecasting**
- 核心：概念导向的图神经网络
- 要点：
  - 挖掘概念股关联
  - 异构图建模
  - 信息解耦

**RTGCN: Relational Temporal Graph Convolution Network**
- 核心：关系时序图卷积
- 要点：
  - 股票关系建模
  - 时序+空间信息
  - 排序任务

---

### Day 4 (2月20日) ⭐ 大语言模型

| 论文 | 方向 | 难度 |
|------|------|------|
| **FinGPT** | LLM金融应用 | ⭐⭐⭐ |
| **AlphaFin** | 检索增强 | ⭐⭐⭐⭐ |

**FinGPT: Democratizing Financial LLMs**
- 机构：AI4Finance
- 核心：开源金融大语言模型
- 要点：
  - LoRA微调
  - 自动数据管道
  - 指令微调

**AlphaFin: Benchmarking Financial Analysis**
- 核心：检索增强股票分析
- 要点：
  - RAG框架
  - 金融分析基准
  - Chain-of-Thought

---

### Day 5 (2月21日) ⭐ 投资组合

| 论文 | 方向 | 难度 |
|------|------|------|
| **DeepTrader** | 组合管理 | ⭐⭐⭐ |
| **mSSRM** | 组合优化 | ⭐⭐⭐⭐ |

**DeepTrader: Risk-Return Balanced Portfolio Management**
- 核心：市场状态嵌入
- 要点：
  - Deep RL
  - 风险收益平衡
  - 多资产组合

**mSSRM: Global Optimal Portfolio for m-Sparse Sharpe Ratio**
- 核心：夏普率最大化
- 要点：
  - NeurIPS 2024
  - 稀疏组合
  - 理论保证

---

## 📅 第2周：进阶专题（11-20篇）

### Day 6 (2月22日) ⭐ 波动率预测

| 论文 | 方向 | 难度 |
|------|------|------|
| **DoubleAdapt** | 元学习 | ⭐⭐⭐⭐ |
| **FactorVAE** | VAE因子 | ⭐⭐⭐ |

**DoubleAdapt: Incremental Learning for Stock Trend Forecasting**
- 核心：元学习+增量学习
- 要点：
  - KDD 2023
  - 域适应
  - 解决分布漂移

**FactorVAE: Probabilistic Dynamic Factor Model**
- 核心：VAE因子模型
- 要点：
  - 交叉截面收益预测
  - 概率生成
  - 隐因子学习

---

### Day 7 (2月23日) ⭐ 多模态

| 论文 | 方向 | 难度 |
|------|------|------|
| **StockEmotions** | 情绪分析 | ⭐⭐ |
| **Astock** | 新闻驱动 | ⭐⭐⭐ |

**StockEmotions: Investor Emotions for Financial Analysis**
- 核心：投资者情绪建模
- 要点：
  - 多变量时序
  - 情感分析
  - AAAI 2023

**Astock: Stock-specific News Analyzing**
- 核心：个股新闻分析
- 要点：
  - ACL/EMNLP
  - 事件检测
  - 自动交易

---

### Day 8 (2月24日) ⭐ 最新2025

| 论文 | 方向 | 难度 |
|------|------|------|
| **SAMBA** | 状态空间 | ⭐⭐⭐⭐ |
| **MERA** | MoE+检索 | ⭐⭐⭐⭐ |

**SAMBA: Mamba Meets Financial Markets**
- 核心：状态空间模型
- 要点：
  - ICASSP 2025
  - Mamba + 图网络
  - 长序列处理

**MERA: Mixture of Experts with Retrieval-Augmented**
- 核心：专家混合+检索
- 要点：
  - WWW 2025
  - 多样化股票模式
  - 检索增强

---

### Day 9 (2月25日) ⭐ 交易执行

| 论文 | 方向 | 难度 |
|------|------|------|
| **Oracle Policy Distillation** | 订单执行 | ⭐⭐⭐⭐ |
| **LARA** | 局部注意力 | ⭐⭐⭐ |

**Universal Trading for Order Execution**
- 核心：订单执行
- 要点：
  - AAAI 2021
  - 策略蒸馏
  - Oracle策略

**LARA: Locality-Aware Attention**
- 核心：局部注意力+自适应标签
- 要点：
  - KDD 2022
  - 机会捕捉
  - 精细标签

---

### Day 10 (2月26日) ⭐ 高频交易

| 论文 | 方向 | 难度 |
|------|------|------|
| **MacroHFT** | 高频RL | ⭐⭐⭐⭐ |
| **DRPO** | 连续策略 | ⭐⭐⭐⭐ |

**MacroHFT: Memory Augmented RL for High Frequency Trading**
- 核心：高频交易
- 要点：
  - KDD 2024
  - 记忆增强
  - 上下文感知

**DRPO: Efficient Continuous Space Policy Optimization**
- 核心：连续空间优化
- 要点：
  - KDD 2023
  - 高频策略
  - 连续动作

---

### Day 11 (2月27日) ⭐ 知识图谱

| 论文 | 方向 | 难度 |
|------|------|------|
| **DANSMP** | 知识图谱 | ⭐⭐⭐ |
| **FinGAT** | 图注意力 | ⭐⭐⭐ |

**DANSMP: Dual Attention Networks with Market KG**
- 核心：市场知识图谱
- 要点：
  - TKDE 2023
  - 异构关系
  - 双注意力

**FinGAT: Financial Graph Attention Networks**
- 核心：图注意力网络
- 要点：
  - TKDE 2021
  - Top-K选股
  - 关系建模

---

### Day 12 (2月28日) ⭐ 生成模型

| 论文 | 方向 | 难度 |
|------|------|------|
| **Diffusion VAE** | 扩散模型 | ⭐⭐⭐⭐ |
| **DVA** | 多步预测 | ⭐⭐⭐⭐ |

**Diffusion Variational Autoencoder for Stock Prediction**
- 核心：扩散模型处理随机性
- 要点：
  - CIKM 2023
  - 多步预测
  - 随机性建模

---

### Day 13 (3月1日) ⭐ 风险建模

| 论文 | 方向 | 难度 |
|------|------|------|
| **Safe-FinRL** | 安全RL | ⭐⭐⭐ |
| **FinRL-Meta** | 基准 | ⭐⭐⭐ |

**Safe-FinRL: Low Bias and Variance for High-Freq Trading**
- 核心：高频交易安全RL
- 要点：
  - 低偏差/方差
  - 理论保证
  - 实用技巧

**FinRL-Meta: Market Environments and Benchmarks**
- 核心：金融强化学习基准
- 要点：
  - NeurIPS 2022
  - 市场环境
  - 数据驱动

---

### Day 14 (3月2日) ⭐ 回顾总结

**本周复盘**
- 14篇论文核心要点回顾
- 模型架构对比
- 实用代码资源整理
- 我们的DSS系统应用建议

---

## 📊 论文难度说明

| 等级 | 含义 |
|------|------|
| ⭐⭐ | 入门级，适合打基础 |
| ⭐⭐⭐ | 进阶级，需要背景知识 |
| ⭐⭐⭐⭐ | 高级，需要深度学习基础 |

---

## 🎯 学习建议

1. **先看代码再读论文** - 大部分有开源代码
2. **重点关注架构图** - 理解模型设计思路
3. **注意实验设置** - 数据集、评估指标
4. **思考应用场景** - 哪些可以用于我们的DSS

---

*计划制定: 2026-02-17*
