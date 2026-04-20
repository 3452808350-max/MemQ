# ⚠️ 数据文件说明

本仓库只包含 **MemQ 源代码**，**不包含任何数据文件**。

## 需要自行准备的数据

### 1. 测试数据集 (`datasets/`)
- 格式：JSONL，每行一个 QA 对
- 示例格式：
```json
{"question": "MemQ 是什么？", "answer": "MemQ 是一个质量感知的记忆检索系统", "category": "general"}
```

### 2. 记忆数据库 (`memory_db/`)
- 首次运行会自动创建
- 或使用自己的记忆数据

### 3. 缓存目录 (`cache/`)
- 运行时会自动生成

## 快速开始

```bash
pip install -r requirements.txt
python test_complete.py  # 使用示例数据测试
```

## 隐私说明

- ✅ 代码完全开源
- ❌ 数据/记忆/配置不包含在仓库中
- 🔒 敏感信息请使用 `.env` 文件管理
