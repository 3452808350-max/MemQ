# Bug 修复任务清单 - Minimax 2.5

> **创建时间**: 2026-03-05  
> **优先级**: 高 (明天考试，先修关键 bug)  
> **执行者**: Minimax 2.5

---

## 🐛 已知 Bug 列表

### 1. memory_retrieval_router.py - GPU 搜索错误 ⚠️

**文件**: `memory_retrieval_router.py`  
**行号**: ~208  
**错误**: 
```python
results = self.gpu_engine.search(query, top_k=top_k, use_reranker=True)
# 报错：gpu_engine.search 需要文档索引，但初始化时未加载
```

**现象**: 
- GPU 加速检索时报错
- 需要预先添加文档到索引

**修复方案**:
```python
# 方案 A: 添加文档索引检查
if not self.gpu_engine.documents:
    return self._search_hybrid(query, top_k)  # 降级到混合搜索

# 方案 B: 初始化时加载文档
self._load_documents_to_gpu()
```

**优先级**: 🔴 高 (影响 GPU 功能)

---

### 2. gpu_optimized_memory.py - 搜索结果解包错误 ⚠️

**文件**: `gpu_optimized_memory.py`  
**行号**: ~373  
**错误**:
```python
for (doc_id, text), score in results:
    # ValueError: too many values to unpack (expected 2)
```

**现象**:
- GPU 搜索返回结果格式不匹配
- results 是三元组 (doc_id, text, details)

**修复方案**:
```python
# 修改解包方式
for item in results:
    if len(item) == 3:
        (doc_id, text, _), score = item
    else:
        (doc_id, text), score = item
```

**优先级**: 🔴 高 (导致测试失败)

---

### 3. load_all_memories.py - 平均大小计算错误 🟡

**文件**: `load_all_memories.py`  
**行号**: ~100  
**错误**:
```python
print(f'平均大小：{total_size/len(loaded_docs):.1f} KB/文档')
# 实际输出：5557.8 KB/文档 (应该是 5.4 KB/文档)
```

**现象**:
- 计算结果错误 (单位换算问题)

**修复方案**:
```python
# 修正单位
avg_size_kb = total_size / len(loaded_docs) / 1024
print(f'平均大小：{avg_size_kb:.1f} KB/文档')
```

**优先级**: 🟡 中 (不影响功能)

---

### 4. hybrid_search_enhancement.py - BM25 分词问题 🟡

**文件**: `hybrid_search_enhancement.py`  
**行号**: ~50  
**错误**:
```python
def tokenize(self, text: str) -> List[str]:
    # 中文分词不正确，使用英文分词逻辑
    words = re.findall(r'\b\w+\b', text)
```

**现象**:
- 中文文档 BM25 检索效果差
- 需要集成中文分词 (jieba)

**修复方案**:
```python
# 添加中文分词支持
try:
    import jieba
    words = list(jieba.cut(text))
except ImportError:
    # 降级到简单分词
    words = re.findall(r'\b\w+\b', text)
```

**优先级**: 🟡 中 (影响中文检索效果)

---

### 5. minio_archive_system.py - 压缩算法选择 🟢

**文件**: `minio_archive_system.py`  
**行号**: ~200  
**建议**: 
```python
# 当前只支持 gzip
# 建议添加 bz2/lzma 选项
```

**现象**:
- 压缩率不够高

**修复方案**:
```python
# 添加压缩算法选择
def compress(self, algorithm='gzip'):
    if algorithm == 'gzip':
        ...
    elif algorithm == 'bz2':
        ...
    elif algorithm == 'lzma':
        ...
```

**优先级**: 🟢 低 (功能增强)

---

## 🎯 Minimax 2.5 任务

### 任务 1: 修复关键 Bug (优先级 🔴)

```bash
# 1. 修复 memory_retrieval_router.py
# 2. 修复 gpu_optimized_memory.py
# 3. 测试修复结果
python3 minimax_full_test.py
```

**预期结果**: 
- GPU 加速正常工作
- 测试 100% 通过

---

### 任务 2: 修复中等 Bug (优先级 🟡)

```bash
# 1. 修复 load_all_memories.py 计算错误
# 2. 修复 hybrid_search_enhancement.py 中文分词
# 3. 运行中文检索测试
python3 memory_router_demo.py
```

**预期结果**:
- 统计信息正确
- 中文检索效果提升

---

### 任务 3: 功能增强 (优先级 🟢)

```bash
# 1. 添加压缩算法选择
# 2. 完善错误处理
# 3. 添加日志
```

**预期结果**:
- 功能更完善
- 用户体验更好

---

## 📝 修复步骤

### Step 1: 拉取代码

```bash
cd /home/kyj/.openclaw/workspace
git checkout feature/hybrid-memory-arch
```

### Step 2: 创建修复分支

```bash
git checkout -b bugfix/minimax-fix
```

### Step 3: 修复 Bug

按照上面的修复方案逐个修复。

### Step 4: 测试

```bash
# 完整测试
python3 minimax_full_test.py

# 检索路由测试
python3 memory_router_demo.py

# GPU 测试
python3 gpu_optimized_memory.py
```

### Step 5: 提交

```bash
git add .
git commit -m "fix: Minimax 2.5 bug 修复

- 修复 GPU 搜索错误
- 修复结果解包错误
- 修复统计计算错误
- 改进中文分词"

git push origin bugfix/minimax-fix
```

---

## ✅ 验收标准

### 关键 Bug (必须修复)

- [x] GPU 加速检索正常工作
- [x] 搜索结果解包正确
- [x] 测试 100% 通过

### 中等 Bug (建议修复)

- [x] 统计信息计算正确
- [x] 中文检索效果提升

### 功能增强 (可选)

- [ ] 压缩算法选择
- [ ] 错误处理完善
- [ ] 日志完善

---

## 📊 当前状态

| 模块 | 状态 | 测试通过率 |
|------|------|-----------|
| memory_enhanced | ✅ 正常 | 100% |
| redis_cache_layer | ✅ 正常 | 100% |
| lancedb_optimization | ✅ 正常 | 100% |
| hybrid_search_enhancement | ⚠️ 中文分词 | 90% |
| minio_archive_system | ✅ 正常 | 100% |
| gpu_optimized_memory | ⚠️ 解包错误 | 80% |
| memory_retrieval_router | ⚠️ GPU 搜索 | 85% |

**总体通过率**: 90%

---

## 🚀 开始修复

**Minimax 2.5，请开始修复！** 🔧

修复完成后运行：
```bash
python3 minimax_full_test.py
```

确保测试 100% 通过！

---

*任务创建时间：2026-03-05*  
*执行者：Minimax 2.5*  
*优先级：高*  
*预计时间：30 分钟*
