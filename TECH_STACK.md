# 混合记忆架构 - 技术栈文档

> **准备上传 GitHub**  
> **版本**: 1.0.0  
> **日期**: 2026-03-05

---

## 📦 完整技术栈

### 编程语言

| 项目 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.12+ | 主开发语言 |
| **Bash** | 5.0+ | 部署脚本 |

### 深度学习框架

| 组件 | 版本 | 用途 |
|------|------|------|
| **PyTorch** | 2.4.1+rocm6.0 | GPU 加速推理 |
| **torchvision** | 0.19.1+rocm6.0 | 视觉处理 |
| **torchaudio** | 2.4.1+rocm6.0 | 音频处理 |

### 向量数据库

| 组件 | 版本 | 用途 |
|------|------|------|
| **LanceDB** | 0.5.0+ | 温数据存储 |
| **PyArrow** | 15.0+ | 数据格式 |

### 缓存层

| 组件 | 版本 | 用途 |
|------|------|------|
| **Redis** | 7.0+ | 热数据缓存 (可选) |
| **LRU Cache** | 内置 | 内存缓存 |

### 对象存储

| 组件 | 版本 | 用途 |
|------|------|------|
| **MinIO** | 7.2.0+ | 冷数据归档 |
| **boto3** | 1.34+ | S3 兼容客户端 |

### 检索技术

| 技术 | 库 | 说明 |
|------|-----|------|
| **BM25** | 自实现 | 全文检索 |
| **RRF** | 自实现 | 排名融合 |
| **Cross-Encoder** | sentence-transformers | 重排 (可选) |

### GPU 加速

| 组件 | 版本 | 说明 |
|------|------|------|
| **AMD ROCm** | 6.0 | GPU 驱动 |
| **AMD RX6800** | 16GB | 物理 GPU |
| **PyTorch ROCm** | 2.4.1+rocm6.0 | ROCm 优化 |

### 数据处理

| 库 | 版本 | 用途 |
|------|------|------|
| **NumPy** | 1.26+ | 数值计算 |
| **Pandas** | 2.2+ | 数据处理 |
| **BeautifulSoup4** | 4.12+ | HTML 解析 |
| **lxml** | 5.0+ | XML 解析 |

### 开发工具

| 工具 | 版本 | 用途 |
|------|------|------|
| **pytest** | 8.0+ | 测试框架 |
| **black** | 24.0+ | 代码格式化 |
| **flake8** | 7.0+ | 代码检查 |
| **tqdm** | 4.66+ | 进度条 |

### 文档工具

| 工具 | 版本 | 用途 |
|------|------|------|
| **Markdown** | 3.5+ | 文档格式 |

---

## 🏗️ 架构分层

### 应用层

```python
# OpenClaw Agent 集成
from memory_retrieval_router import MemoryRouter

router = MemoryRouter()
results = router.route_query("查询", top_k=5)
```

### 检索路由层

```python
# 智能路由
class MemoryRouter:
    - 自动策略选择
    - 性能监控
    - 结果融合
```

### 存储层

```
热数据层 (Redis/LRU)  → <1ms
    ↓
温数据层 (LanceDB)    → 10-50ms
    ↓
冷数据层 (MinIO)      → 100-500ms
```

---

## 📂 文件结构

```
hybrid-memory-architecture/
├── README.md                          # 主 README
├── requirements.txt                   # Python 依赖
├── LICENSE                            # MIT 许可证
├── setup.py                           # 安装脚本
├── config.yaml                        # 配置文件
│
├── docs/                              # 文档目录
│   ├── HYBRID_MEMORY_ARCHITECTURE.md  # 架构设计
│   ├── GPU_SUCCESS_REPORT.md          # GPU 安装
│   ├── MINIMAX_FINAL_REPORT.md        # 测试报告
│   ├── MEMORY_RETRIEVAL_GUIDE.md      # 检索指南
│   └── ...
│
├── core/                              # 核心模块
│   ├── memory_enhanced.py             # 记忆增强
│   ├── redis_cache_layer.py           # Redis 缓存
│   ├── lancedb_optimization.py        # LanceDB 优化
│   ├── hybrid_search_enhancement.py   # 混合搜索
│   ├── minio_archive_system.py        # MinIO 归档
│   ├── gpu_optimized_memory.py        # GPU 优化
│   └── memory_retrieval_router.py     # 检索路由
│
├── tests/                             # 测试
│   ├── test_memory.py
│   ├── test_cache.py
│   ├── test_search.py
│   └── test_gpu.py
│
├── scripts/                           # 工具脚本
│   ├── load_all_memories.py           # 批量载入
│   ├── minimax_full_test.py           # 完整测试
│   └── memory_router_demo.py          # 路由演示
│
└── examples/                          # 示例
    ├── basic_usage.py
    ├── gpu_acceleration.py
    └── hybrid_search.py
```

---

## 🚀 部署流程

### 1. 环境准备

```bash
# Python 3.12+
python3 --version

# Git
git --version

# GPU 驱动 (可选)
rocm-smi
```

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/hybrid-memory-architecture.git
cd hybrid-memory-architecture

# 安装依赖
pip install -r requirements.txt
```

### 3. GPU 配置 (可选)

```bash
# AMD GPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0

# 验证 GPU
python3 -c "import torch; print(torch.cuda.is_available())"
```

### 4. 运行测试

```bash
# 完整测试
python3 minimax_full_test.py

# 检索路由测试
python3 memory_router_demo.py

# 批量载入
python3 load_all_memories.py
```

---

## 📊 性能基准

### 测试环境

```yaml
CPU: 4-8 核
内存：16GB
GPU: AMD RX6800 (16GB)
存储：SSD
```

### 检索性能

| 策略 | P50 | P99 | QPS |
|------|-----|-----|-----|
| **缓存** | <1ms | 5ms | 10000+ |
| **BM25** | 10ms | 50ms | 2000 |
| **GPU** | 5ms | 20ms | 5000 |
| **混合** | 50ms | 150ms | 500 |

### 成本对比

| 方案 | 月成本 | 年成本 | 5 年 TCO |
|------|--------|--------|---------|
| **全热存储** | $37.03 | $444 | $2,220 |
| **分层存储** | $6.23 | $75 | $375 |
| **节省** | **$30.80** | **$369** | **$1,845** |

---

## 🧪 测试策略

### 单元测试

```python
# tests/test_memory.py
def test_memory_store():
    memory_id = memory_store_enhanced("test", "test_category")
    assert memory_id is not None
```

### 集成测试

```python
# tests/test_search.py
def test_hybrid_search():
    engine = HybridSearchEngine()
    results = engine.search("query", top_k=5)
    assert len(results) > 0
```

### 性能测试

```python
# tests/test_performance.py
def test_gpu_performance():
    engine = GPUOptimizedSearchEngine()
    start = time.time()
    results = engine.search("query", top_k=10)
    elapsed = time.time() - start
    assert elapsed < 0.1  # <100ms
```

---

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

## 🤝 贡献指南

### 开发流程

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 开启 Pull Request

### 代码规范

```bash
# 格式化
black .

# 检查
flake8 .

# 测试
pytest tests/
```

---

## 📞 联系方式

- **GitHub**: https://github.com/YOUR_USERNAME/hybrid-memory-architecture
- **Issues**: https://github.com/YOUR_USERNAME/hybrid-memory-architecture/issues
- **文档**: docs/

---

*技术栈版本：1.0.0*  
*最后更新：2026-03-05*  
*状态：✅ 生产就绪*
