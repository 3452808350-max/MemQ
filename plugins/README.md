# MemQ Plugins - 记忆检索插件

## 📁 文件结构

```
plugins/
├── memq.py              # 基础版：纯内存分层检索（快速测试用）
├── memq_pro.py          # 专业版：向量+BM25+Rerank 混合检索（生产用）
└── test_ollama_embedding.py  # Ollama 向量化测试脚本
```

## 🚀 快速开始

### 基础版（快速测试）

```python
from memq import MemQ

memq = MemQ()
memq.add_memory("test", "这是测试内容", category="general")
results = memq.search("测试", layer="l1")
```

**特点**：
- ✅ 无需外部依赖
- ✅ 秒级启动
- ✅ L0/L1/L2 分层
- ❌ 关键词检索（无向量）

---

### 专业版（生产环境）

```python
from memq_pro import MemQPro

memq = MemQPro()
memq.add_memory("kimi_api", content, category="skills")
results = memq.search("如何部署 API？", top_k=5, layer=MemoryLayer.L1_OVERVIEW)
```

**特点**：
- ✅ Ollama Qwen3-Embedding 向量检索（1024 维）
- ✅ BM25 关键词检索
- ✅ Ollama Qwen3-Reranker 重排序
- ✅ L0/L1/L2 分层（Token 节省 70-88%）
- ✅ 100% GPU 加速
- ⚠️ 需要 Ollama 服务运行

**检索流程**：
1. 混合检索（向量 +BM25）→ Top-20
2. Reranker 重排序 → Top-10
3. 返回指定层次内容

---

## 📊 性能对比

| 特性 | memq.py | memq_pro.py |
|------|---------|-------------|
| 检索方式 | 关键词 | 向量+BM25+Rerank |
| 召回率 | ~60% | ~75%+ |
| Token 节省 | 70-88% | 70-88% |
| GPU 加速 | ❌ | ✅ |
| 启动速度 | 秒级 | 10-20 秒（首次） |
| 外部依赖 | 无 | Ollama |

---

## 🔧 依赖

### 基础版
```bash
pip install rank-bm25
```

### 专业版
```bash
pip install rank-bm25 numpy
# Ollama 服务（GPU 加速）
# - modelscope.cn/Qwen/Qwen3-Embedding-0.6B-GGUF
# - modelscope.cn/dengcao/Qwen3-Reranker-0.6B-GGUF
```

---

## 🎯 使用建议

**选择指南**：
- 快速原型/测试 → `memq.py`
- 生产环境/高准确率 → `memq_pro.py`
- 无网络环境 → `memq.py`
- 有 GPU 资源 → `memq_pro.py`

---

## 📝 版本历史

- **2026-03-16**: 清理多余版本，统一为 `memq.py` + `memq_pro.py`
- **2026-03-15**: 初始实现（多个实验版本）

---

## 🔍 故障排查

### Ollama 模型未跑在 GPU 上

```bash
# 检查模型状态
ollama ps

# 应该显示 "100% GPU"，如果显示 "100% CPU"：
# 1. 配置 ROCm 环境变量
# 2. 重启 Ollama 服务
sudo systemctl restart ollama
```

### 向量化超时

检查 Ollama 服务是否正常：
```bash
curl http://localhost:11434/api/tags
```

---

**维护者**: Kaguya  
**最后更新**: 2026-03-16
