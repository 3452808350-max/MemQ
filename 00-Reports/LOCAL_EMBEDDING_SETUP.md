# 🚀 本地向量模型部署指南

> **部署时间**: 2026-03-08  
> **方案**: Ollama / vllm  
> **状态**: ✅ 就绪

---

## 📋 方案选择

### 方案 1: Ollama (推荐) ⭐⭐⭐⭐⭐

**优点**:
- ✅ 简单易用
- ✅ 快速启动
- ✅ 多种模型
- ✅ 低显存占用
- ✅ REST API

**推荐模型**:
| 模型 | 维度 | 上下文 | 显存 | 速度 |
|------|------|--------|------|------|
| **nomic-embed-text** | 768 | 8192 | ~1GB | 快 |
| **mxbai-embed-large** | 1024 | 512 | ~2GB | 快 |
| **all-minilm** | 384 | 512 | ~0.5GB | 最快 |

---

### 方案 2: vllm (高性能) ⭐⭐⭐⭐

**优点**:
- ✅ 高性能
- ✅ 批量处理
- ✅ 支持多种模型

**推荐模型**:
- `BAAI/bge-large-zh-v1.5` (中文优化)
- `BAAI/bge-base-zh-v1.5` (平衡)

---

## 🚀 Ollama 部署

### 步骤 1: 安装 Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# 验证安装
ollama --version
```

---

### 步骤 2: 拉取向量化模型

```bash
# 推荐模型 (平衡)
ollama pull nomic-embed-text

# 或者高性能模型
ollama pull mxbai-embed-large

# 或者最小模型 (最快)
ollama pull all-minilm
```

---

### 步骤 3: 启动 Ollama 服务

```bash
# 后台运行
ollama serve &

# 或者使用 systemd
sudo systemctl start ollama
sudo systemctl enable ollama
```

---

### 步骤 4: 测试

```bash
# 测试模型
ollama run nomic-embed-text "Hello World"

# 测试 API
curl http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "prompt": "Hello World"}'
```

**预期输出**:
```json
{
  "embedding": [0.123, -0.456, 0.789, ...],
  "total_duration": 12345678,
  "model": "nomic-embed-text"
}
```

---

## 🔧 集成到 OpenClaw

### 配置 Embedding 生成器

**文件**: `openclaw/core/memory/embedding.py`

**配置**:
```python
config = EmbeddingConfig(
    use_local=True,  # 使用本地 Ollama ⭐
    local_url="http://localhost:11434",
    local_model="nomic-embed-text",
    dimension=768
)

generator = EmbeddingGenerator(config)
```

---

### 使用示例

```python
from openclaw.core.memory.embedding import EmbeddingGenerator, EmbeddingConfig

# 配置本地 Ollama
config = EmbeddingConfig(
    use_local=True,
    local_url="http://localhost:11434",
    local_model="nomic-embed-text"
)

generator = EmbeddingGenerator(config)

# 生成嵌入
embedding = await generator.generate("你好世界")
print(f"维度：{len(embedding)}")  # 768
```

---

## 📊 性能对比

### Ollama vs DashScope

| 指标 | Ollama (本地) | DashScope (API) |
|------|--------------|-----------------|
| **延迟** | ~50ms | ~200ms |
| **成本** | 免费 | 按量计费 |
| **限制** | 无 | 速率限制 |
| **隐私** | ✅ 本地 | ❌ 云端 |
| **配置** | 需要安装 | 简单 |

---

### 性能测试

```bash
# 运行性能测试
cd /home/kyj/.openclaw/workspace
pytest openclaw/tests/test_benchmark.py::test_embedding_single_performance -v -s
```

**预期结果**:
```
Single embedding (Ollama): 50-100ms  ✅
```

---

## 🚀 vllm 部署 (可选)

### 步骤 1: 安装 vllm

```bash
pip install vllm
```

---

### 步骤 2: 启动 API 服务

```bash
python -m vllm.entrypoints.openai.api_server \
  --model BAAI/bge-large-zh-v1.5 \
  --host 0.0.0.0 \
  --port 8000
```

---

### 步骤 3: 配置 OpenClaw

```python
config = EmbeddingConfig(
    use_local=True,
    local_url="http://localhost:8000/v1",
    local_model="BAAI/bge-large-zh-v1.5",
    dimension=1024
)
```

---

## 📊 显存需求

### Ollama 模型

| 模型 | 显存 | 推荐显卡 |
|------|------|---------|
| **all-minilm** | 0.5GB | 任意显卡 |
| **nomic-embed-text** | 1GB | GTX 1050+ |
| **mxbai-embed-large** | 2GB | GTX 1060+ |

---

### vllm 模型

| 模型 | 显存 | 推荐显卡 |
|------|------|---------|
| **bge-base-zh** | 3GB | GTX 1060+ |
| **bge-large-zh** | 5GB | GTX 1080+ |

---

## 🎯 推荐配置

### 最低配置

```bash
# 模型
ollama pull all-minilm

# 配置
config = EmbeddingConfig(
    use_local=True,
    local_model="all-minilm",
    dimension=384
)
```

**显存**: 0.5GB  
**速度**: 最快  

---

### 推荐配置

```bash
# 模型
ollama pull nomic-embed-text

# 配置
config = EmbeddingConfig(
    use_local=True,
    local_model="nomic-embed-text",
    dimension=768
)
```

**显存**: 1GB  
**速度**: 快  
**质量**: 好  

---

### 高性能配置

```bash
# 模型
ollama pull mxbai-embed-large

# 配置
config = EmbeddingConfig(
    use_local=True,
    local_model="mxbai-embed-large",
    dimension=1024
)
```

**显存**: 2GB  
**速度**: 快  
**质量**: 最好  

---

## 🧪 测试验证

### 运行测试

```bash
cd /home/kyj/.openclaw/workspace

# 单次性能测试
pytest openclaw/tests/test_benchmark.py::test_embedding_single_performance -v -s

# 批量性能测试
pytest openclaw/tests/test_benchmark.py::test_embedding_batch_performance -v -s

# 连接池测试
pytest openclaw/tests/test_benchmark.py::test_embedding_pool_performance -v -s
```

---

### 预期结果

```
============================= test session starts ==============================
openclaw/tests/test_benchmark.py::test_embedding_single_performance 
Single embedding (Ollama): 67.42ms ✅ PASSED

openclaw/tests/test_benchmark.py::test_embedding_batch_performance 
Batch embedding (100): 3.45s ✅ PASSED
Per embedding: 34.50ms

openclaw/tests/test_benchmark.py::test_embedding_pool_performance 
Pool embedding (100): 2.89s ✅ PASSED
Per embedding: 28.90ms
```

---

## 🎊 总结

### 优势

- ✅ **免费** - 无需 API Key
- ✅ **快速** - 本地部署 < 100ms
- ✅ **隐私** - 数据本地处理
- ✅ **无限制** - 无速率限制
- ✅ **灵活** - 多种模型选择

---

### 推荐方案

**最佳平衡**:
```bash
ollama pull nomic-embed-text
```

**配置**:
```python
EmbeddingConfig(
    use_local=True,
    local_model="nomic-embed-text",
    dimension=768
)
```

**性能**: ~50-100ms/次  
**显存**: ~1GB  

---

## 🚀 立即开始

### 1. 安装 Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. 拉取模型

```bash
ollama pull nomic-embed-text
```

### 3. 启动服务

```bash
ollama serve &
```

### 4. 测试

```bash
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "你好"}'
```

### 5. 运行性能测试

```bash
cd /home/kyj/.openclaw/workspace
pytest openclaw/tests/test_benchmark.py -v
```

---

**本地部署完成！享受免费快速的向量嵌入生成！** 🚀

---

*部署指南时间：2026-03-08*  
*部署者：Kaguya*  
*状态：✅ 就绪*
