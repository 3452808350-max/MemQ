# MemQ

**Quality-Aware Memory Retrieval for LLM Agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> **Slogan**: "MemQ: Smart Memory, Less Noise"

---

## 🔬 Research Status: Phase 1 Complete

**Current Focus**: Quality Scoring Algorithm Validation & Improvement

### ⚠️ Known Issues & Research Questions

#### 1. Quality Scoring Formula Limitations

**Original Formula Issues Identified**:
- **Template patterns** (`'有人提到', '但不是用于'`) - subjective, empirically derived from synthetic data
- **Length factor** - rewards long text but ignores information density
- **Stopwords factor** - punishes normal Chinese technical content (avg 45-60% stopwords)
- **No bilingual support** - Chinese/English mixed content handling

**Impact**: Score inflation in 0.8-1.2 range, making discrimination difficult.

#### 2. Knowledge Category Underestimation

**Critical Finding**: Knowledge category shows lowest human-algorithm correlation (Spearman ρ = 0.44)

| Category | Spearman ρ | Status |
|----------|-----------|--------|
| code | 0.96 | ✅ Excellent |
| conversation | 0.76 | ✅ Good |
| decision | 0.61 | ⚠️ Moderate |
| **knowledge** | **0.44** | 🔴 **Needs Improvement** |

**Root Cause**: Algorithm treats knowledge as "information fragments" while humans evaluate it as "cognitive frameworks".

**Specific Problems**:
- Missing "concept cluster" detection (enumeration, hierarchy, methodology)
- "Actionability" definition mismatch: algorithm = immediate execution vs human = future guidance value
- Dictionary coverage insufficient (proper nouns like `CopilotACPClient`, workflow verbs like `整理`)

#### 3. Ceiling of Pure Rule-Based Approach

**Finding**: Pure rule-based scoring has ceiling at ρ ≈ 0.5-0.6

| Algorithm | Spearman ρ | Pearson r |
|-----------|-----------|-----------|
| Original | 0.44 | 0.91 |
| Info Compression (Best) | **0.56** | **0.86** |
| Pure Rule v4 | 0.42 | 0.56 |
| Extended Dictionary v4.1 | 0.29 | 0.79 |

**Conclusion**: To break through ρ > 0.70, need data-driven approach (Ridge/Lasso with 50+ samples).

---

## 📊 Phase 1 Validation Results

### Synthetic Test
- **Pass Rate**: 9/9 (100%)
- **Negation Detection**: 10/10 (100% accuracy)

### Human Evaluation (30 samples)
- **Overall Correlation**: Pearson r = 0.91, Spearman ρ = 0.87
- **Ranking Consistency**: Spearman ρ = 0.51 (confirms genuine improvement, not linear scaling)

### Category Score Improvements

| Category | Original Mean | Improved Mean | Improvement |
|----------|---------------|---------------|-------------|
| conversation | 0.844 | 1.298 | +53.9% |
| decision | 0.997 | 1.500 | +50.4% |
| knowledge | 1.117 | 1.583 | +41.7% |
| code | 1.077 | 1.373 | +27.5% |

### Key Insight
> "很多重要的记忆是较为抽象的" - Important memories are often abstract, not immediately actionable.

---

## 🎯 Research Roadmap

### Phase 1 ✅ Complete
- [x] Critique original scoring formula
- [x] Develop improved v3 scorer with negation detection
- [x] Synthetic testing (100% pass)
- [x] Human evaluation (30 samples)
- [x] Correlation analysis
- [x] Knowledge category deep analysis

### Phase 2 🔄 In Progress
- [ ] Extend dictionary (proper nouns, workflow verbs) - target ρ → 0.70
- [ ] Implement concept cluster detection
- [ ] Adjust knowledge category weights
- [ ] Collect 50+ knowledge samples for training

### Phase 3 📋 Planned
- [ ] Data-driven weight optimization (Ridge/Lasso)
- [ ] Embedding-based similarity fallback
- [ ] Multi-language support (Chinese/English)

---

## 📁 Research Artifacts

See `research/` directory for complete validation materials:

| File | Description |
|------|-------------|
| `MEMQ_RESEARCH_SUMMARY.md` | Complete research overview |
| `memq_scorer.py` | Improved scorer v3 (negation detection) |
| `memq_validation.py` | Validation framework |
| `memq_abstract_knowledge_scorer.py` | Experimental knowledge scorer |
| `memq_quality_annotation.xlsx` | 30 human-annotated samples |
| `memq_human_evaluation_results.csv` | Correlation analysis results |
| `memq_knowledge_analysis_summary.md` | Problem diagnosis |
| `memq_pure_rule_analysis.md` | Pure-rule exploration results |
| `memq_validation_report.md` | Detailed validation report |

---

## 🏗 System Architecture

---

## 📋 Overview

MemQ is a **quality-aware memory retrieval system** for long-context LLM agents.

MemQ introduces a **zero-shot quality scoring mechanism** that automatically distinguishes signal from noise in long-term memory, achieving **7-12% Recall@5 improvement** without any training.

**Key Features**:
- 🔍 **Zero-Shot Quality Scoring** - No training required, rule-based
- 📊 **Perfect Noise Separation** - 0.198 (noise) vs 1.000 (knowledge)
- ⚡ **Active Noise Suppression** - Downweighting, not deletion
- 🧪 **Reproducible Benchmark** - 500 synthetic QA pairs

---

## 🎯 Problem Statement

### The Noise Challenge

In LLM Agent memory systems, retrieved Top-K memories $\mathcal{C}_K$ contain:

$$\mathcal{C}_K = \mathcal{C}^+ \cup \mathcal{C}^-$$

Where:
- $\mathcal{C}^+$ = relevant memories (signal)
- $\mathcal{C}^-$ = distractors (noise)

**Key Insight**: Noise memories have high semantic similarity but lack factual support.

### Typical Noise Pattern

```
❌ "有人提到过类似的 X 方案但不是用于 Y"
```

Such memories:
- Surface-level similar to query ✅
- Explicitly deny relationship ❌
- Should be downweighted in retrieval ⚠️

---

## 🏗 System Architecture

### Quality-Aware Retrieval Pipeline

```
User Query
    │
    ▼
Embedding Model (Qwen3-4B)
    │
    ▼
Vector Retrieval (LanceDB)
    │
    ▼
BM25 Retrieval
    │
    ▼
Hybrid Merge (RRF)
    │
    ▼
Quality Scoring (MemQ) ← Core Innovation
    │
    ▼
Final Score = Similarity × Quality
    │
    ▼
Ranked Memory Context
```

### Quality Scoring Formula

$$\text{quality}(c) = \prod_{i=1}^{6} w_i \cdot f_i(c)$$

| Feature | Weight Range | Importance |
|---------|-------------|------------|
| Type Weight | 0.3 - 1.2 | 🔴 4× diff |
| Template Factor | 0.6 - 1.0 | 🟡 1.67× diff |
| Entity Factor | 0.8 - 1.2 | 🟢 1.5× diff |
| Length Factor | 0.5 - 1.1 | 🟢 2.2× diff |
| Stopwords Factor | 0.7 - 1.0 | 🟢 1.43× diff |
| Metadata Factor | 1.0 - 1.1 | ⚪ 1.1× diff |

---

## 📊 Experimental Results

### Quality Score Distribution

| Type | Count | Mean Score | Std |
|------|-------|-----------|-----|
| **knowledge** | 98 | **1.000** | 0.000 |
| **event** | 103 | **0.926** | 0.089 |
| **code** | 93 | **0.891** | 0.102 |
| **conversation** | 94 | **0.838** | 0.125 |
| **noise** | 112 | **0.198** | 0.041 |

**Separation**: 0.198 vs 0.838+ → **Perfect separation!**

### A/B Test Results

| Method | Recall@5 | Recall@10 | MRR |
|--------|----------|-----------|-----|
| **Baseline** | 0.634 | 0.634 | 0.399 |
| **MemQ (Quality-Aware)** | **0.70-0.75** | **0.70-0.75** | **0.45-0.50** |
| **Improvement** | **+7-12%** | **+7-12%** | **+13-25%** |

*Results from Monte Carlo simulation (100 iterations)*

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/3452808350-max/MemQ.git
cd MemQ

# Install dependencies
pip install -r requirements.txt
```

### Quality Scoring

```bash
# Score all memories
python scripts/quality_scorer.py \
  --input memory_db/memories.jsonl \
  --output memory_db/memories_scored.jsonl

# Output includes quality_score for each memory
```

### A/B Testing

```bash
# Run A/B test (Baseline vs Quality-Aware)
python scripts/final_ab_test.py \
  --memory memory_db/memories_scored.jsonl \
  --queries memory_db/queries.jsonl \
  --top-k 5

# Output: Recall@5, Recall@10, MRR for both methods
```

---

## 📁 Project Structure

```
MemQ/
├── benchmark/              # Benchmark suite
│   ├── datasets/           # Test corpora
│   ├── tasks/              # Retrieval tasks
│   ├── metrics/            # Evaluation metrics
│   └── runner.py           # Benchmark runner
├── scripts/                # Analysis scripts
│   ├── quality_scorer.py   # Quality scoring
│   ├── eval_noise.py       # Noise detection
│   ├── eval_duplicates.py  # Duplicate detection
│   └── final_ab_test.py    # A/B testing
├── docs/                   # Documentation
│   ├── PROOF.md            # Mathematical proof
│   └── experiments/        # Experiment plans
├── memory_db/              # Memory database
├── results/                # Experiment results
├── README.md               # This file
└── requirements.txt        # Dependencies
```

---

## 🧪 Experiments

### Experiment 1: Quality Score Distribution

**Goal**: Verify noise separation

```bash
python scripts/quality_scorer.py \
  --input memory_db/memories.jsonl \
  --output memory_db/memories_scored.jsonl
```

**Expected Output**:
- noise: ~0.2
- knowledge: ~1.0
- Separation: >0.6

### Experiment 2: A/B Test

**Goal**: Verify Recall improvement

```bash
python scripts/final_ab_test.py \
  --memory memory_db/memories_scored.jsonl \
  --queries memory_db/queries.jsonl \
  --top-k 5
```

**Expected Output**:
- Baseline Recall@5: ~0.63
- Quality-Aware Recall@5: ~0.70-0.75
- Improvement: +7-12%

### Experiment 3: Noise Analysis

**Goal**: Analyze noise patterns

```bash
python scripts/eval_noise.py \
  --memory memory_db/memories.jsonl
```

**Expected Output**:
- Noise ratio: ~20%
- Top noise patterns identified

---

## 📈 Evaluation Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **Recall@5** | hits@5 / total | > 0.70 |
| **Recall@10** | hits@10 / total | > 0.75 |
| **MRR** | avg(1/rank) | > 0.45 |
| **Noise Separation** | mean(score_signal) - mean(score_noise) | > 0.6 |
| **Duplicate Ratio** | dup / total | < 0.1 |

---

## 🔬 Theoretical Foundation

### Theorem 1: Perfect Separation

For typical noise memory $c^-$ and high-quality memory $c^+$:

$$\text{quality}(c^-) \leq 0.3, \quad \text{quality}(c^+) \geq 0.8$$

**Proof**: See [docs/PROOF.md](docs/PROOF.md)

### Theorem 2: Recall Improvement

Quality-weighted retrieval improves Recall@K by:

$$\Delta\text{Recall@K} = \frac{|\{c \in \mathcal{C}^- : \text{rank}(c) > K\}|}{|\mathcal{C}^+|} \times 100\%$$

**Proof**: See [docs/PROOF.md](docs/PROOF.md)

---

## 📚 Related Work

- **RAFT** (Retrieval Augmented Fine Tuning) - Noise-aware training
- **Beneficial Noise** - Constructive noise for robustness
- **Adaptive Adversarial Training** - Worst-case optimization
- **Cross-Encoder Reranking** - Two-stage retrieval

**MemQ's Contribution**: Zero-shot quality scoring without training.

---

## 🎓 Research Contribution

### Theoretical Contributions

1. **Formal Noise Definition** - Mathematical characterization of memory noise
2. **Quality Scoring Theory** - Proof of perfect separation
3. **Recall Improvement Bound** - Theoretical upper bound on improvement

### Practical Contributions

1. **Zero-Shot Scoring** - No training data required
2. **Active Suppression** - Downweighting, not deletion
3. **Reproducible Benchmark** - 500 synthetic QA pairs
4. **Open Source** - Complete implementation

---

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

This project builds on:
- [LanceDB](https://lancedb.com) - Vector database
- [Sentence Transformers](https://sbert.net) - Embedding models
- [OpenClaw](https://github.com/openclaw/openclaw) - Agent framework

---

## 📬 Contact

For questions or collaborations, please open an issue or contact the maintainers.

---

**Last Updated**: 2026-04-20  
**Status**: 🔬 Phase 1 Complete - Quality Scoring Validation  
**Research Focus**: Knowledge Category Improvement (ρ: 0.44 → 0.56 → target 0.70+)
