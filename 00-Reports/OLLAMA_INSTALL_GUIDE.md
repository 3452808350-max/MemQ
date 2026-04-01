# 🚀 Ollama 安装指南

> **部署时间**: 2026-03-08  
> **目标**: 本地部署向量模型  
> **状态**: 🟡 等待执行

---

## 📋 安装步骤

### 步骤 1: 下载并安装 Ollama

**方法 1: 一键安装 (推荐)**

```bash
# 下载安装脚本
curl -fsSL https://ollama.com/install.sh -o /tmp/ollama_install.sh

# 执行安装 (需要 sudo 密码)
sudo bash /tmp/ollama_install.sh
```

**方法 2: 手动安装**

```bash
# 下载 Ollama
curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o /tmp/ollama.tgz

# 解压
sudo tar -C /usr -xzf /tmp/ollama.tgz

# 启动服务
sudo systemctl start ollama
sudo systemctl enable ollama
```

---

### 步骤 2: 验证安装

```bash
# 检查版本
ollama --version

# 检查服务状态
systemctl status ollama
```

**预期输出**:
```
ollama version 0.1.x
```

---

### 步骤 3: 拉取向量化模型

**推荐模型**: **mxbai-embed-large** (适合你的 AMD RX 6800)

```bash
# 拉取模型 (约 2GB，需要 2-5 分钟)
ollama pull mxbai-embed-large
```

**备选模型**:
```bash
# 如果显存不足，可以选择更小的模型
ollama pull nomic-embed-text  # 1GB
ollama pull all-minilm       # 0.5GB
```

---

### 步骤 4: 启动 Ollama 服务

```bash
# 后台运行
ollama serve &

# 或者使用 systemd
sudo systemctl start ollama
sudo systemctl enable ollama
```

**验证服务**:
```bash
curl http://localhost:11434/api/tags
```

**预期输出**:
```json
{
  "models": [
    {
      "name": "mxbai-embed-large",
      "size": 2097152000,
      "digest": "abc123..."
    }
  ]
}
```

---

### 步骤 5: 测试模型

```bash
# 测试嵌入生成
curl http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mxbai-embed-large",
    "prompt": "你好世界"
  }'
```

**预期输出**:
```json
{
  "embedding": [0.123, -0.456, 0.789, ...],
  "total_duration": 67890123,
  "model": "mxbai-embed-large"
}
```

---

## 🔧 配置 OpenClaw

### 修改 Embedding 配置

**文件**: `openclaw/core/memory/embedding.py`

**配置**:
```python
config = EmbeddingConfig(
    use_local=True,
    local_model="mxbai-embed-large",
    dimension=1024,
    local_url="http://localhost:11434"
)
```

---

### 使用示例

```python
from openclaw.core.memory.embedding import EmbeddingGenerator, EmbeddingConfig

# 配置
config = EmbeddingConfig(
    use_local=True,
    local_model="mxbai-embed-large",
    dimension=1024
)

generator = EmbeddingGenerator(config)

# 生成嵌入
embedding = await generator.generate("你好世界")
print(f"维度：{len(embedding)}")  # 1024
```

---

## 📊 性能预期

### AMD RX 6800 性能

| 指标 | 预期 | 说明 |
|------|------|------|
| **单次延迟** | 50-80ms | 本地推理 |
| **批量 100** | 3-5s | 并发优化 |
| **吞吐量** | > 60 emb/s | 持续生成 |
| **显存占用** | ~2GB | GPU 显存 |

---

## 🧪 运行性能测试

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

## ⚠️ 常见问题

### 问题 1: 权限不足

**错误**: `Permission denied`

**解决**:
```bash
sudo usermod -aG render $USER
sudo usermod -aG video $USER
# 注销并重新登录
```

---

### 问题 2: 模型下载慢

**解决**: 使用镜像
```bash
export OLLAMA_DOWNLOAD_URL=https://hf-mirror.com
ollama pull mxbai-embed-large
```

---

### 问题 3: GPU 不支持

**错误**: `GPU not supported`

**解决**: 使用 CPU 模式
```bash
OLLAMA_NUM_GPU=0 ollama serve
```

---

## 🎊 完成验证

### 检查清单

- [ ] Ollama 已安装
- [ ] 模型已下载 (mxbai-embed-large)
- [ ] 服务已启动
- [ ] API 可访问
- [ ] OpenClaw 已配置
- [ ] 性能测试通过

---

### 测试命令

```bash
# 测试 Ollama
curl http://localhost:11434/api/embeddings \
  -d '{"model": "mxbai-embed-large", "prompt": "你好"}'

# 测试 OpenClaw
cd /home/kyj/.openclaw/workspace
pytest openclaw/tests/test_benchmark.py::test_embedding_single_performance -v -s
```

---

## 📊 预期结果

```
============================= test session starts ==============================
openclaw/tests/test_benchmark.py::test_embedding_single_performance 
Single embedding (Ollama): 67.42ms ✅ PASSED

openclaw/tests/test_benchmark.py::test_embedding_batch_performance 
Batch embedding (100): 3.45s ✅ PASSED
Per embedding: 34.50ms
```

---

## 🎊 总结

### 部署步骤

1. ✅ 安装 Ollama
2. ✅ 拉取模型 (mxbai-embed-large)
3. ✅ 启动服务
4. ✅ 测试验证
5. ✅ 配置 OpenClaw
6. ✅ 运行测试

### 预期性能

- **延迟**: 50-80ms/次
- **吞吐量**: > 60 emb/s
- **显存**: ~2GB
- **质量**: ⭐⭐⭐⭐⭐

---

**准备好开始安装了吗？** 🚀

**预计时间**: 5-10 分钟  
**难度**: ⭐⭐ (简单)
