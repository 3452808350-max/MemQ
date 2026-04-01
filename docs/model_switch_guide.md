# 模型切换指南

> **主模型已切换为 Kimi 2.5**

---

## 🎯 当前配置

### 主模型：Kimi 2.5
```json
{
  "name": "Kimi-2.5",
  "provider": "dashscope",
  "base_url": "https://coding.dashscope.aliyuncs.com/v1",
  "capabilities": ["chat", "code", "analysis"],
  "context_window": 128000,
  "max_tokens": 8192
}
```

**优势**：
- ✅ **快速**：适合批量任务
- ✅ **长上下文**：128K tokens
- ✅ **代码能力强**：适合编程任务
- ✅ **成本低**：性价比高

**适用场景**：
- 日常对话
- 代码生成
- 数据分析
- 批量处理

---

### 备用模型：Qwen3.5-Plus
```json
{
  "name": "Qwen3.5-Plus",
  "provider": "bailian",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "capabilities": ["chat", "code", "reasoning"],
  "context_window": 32000,
  "max_tokens": 8192
}
```

**优势**：
- ✅ **推理能力强**：复杂逻辑推理
- ✅ **高质量输出**：文章写作、创意生成
- ✅ **多语言支持**：中英文混合

**适用场景**：
- 复杂推理
- 创意写作
- 高质量内容生成
- 需要深度思考的任务

---

## 🔧 如何切换模型

### 方法 A：配置文件切换

**编辑配置文件**：
```bash
nano config/model_config.json
```

**修改主模型**：
```json
{
  "primary_model": {
    "name": "Kimi-2.5",  // 或 "Qwen3.5-Plus"
    ...
  }
}
```

---

### 方法 B：运行时切换

**Python 代码**：
```python
from openai import OpenAI
import os

# 切换到 Kimi 2.5
client = OpenAI(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    base_url='https://coding.dashscope.aliyuncs.com/v1'
)

# 切换到 Qwen3.5-Plus
client = OpenAI(
    api_key=os.getenv('DASHSCOPE_API_KEY'),
    base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
)
```

---

### 方法 C：OpenClaw 配置

**编辑 OpenClaw 配置**：
```bash
nano ~/.openclaw/openclaw.json
```

**修改默认模型**：
```json
{
  "default_model": "dashscope/kimi-2.5",
  "models": {
    "dashscope/kimi-2.5": {
      "base_url": "https://coding.dashscope.aliyuncs.com/v1"
    },
    "dashscope/qwen3.5-plus": {
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
    }
  }
}
```

---

## 📊 性能对比

| 指标 | Kimi 2.5 | Qwen3.5-Plus |
|------|----------|--------------|
| **响应速度** | ⚡⚡⚡ 快 | ⚡⚡ 中等 |
| **代码能力** | ⭐⭐⭐⭐ 强 | ⭐⭐⭐⭐ 强 |
| **推理能力** | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐⭐ 强 |
| **写作质量** | ⭐⭐⭐ 良好 | ⭐⭐⭐⭐⭐ 优秀 |
| **上下文长度** | 128K | 32K |
| **成本** | 💰💰 低 | 💰💰💰 中等 |

---

## 🎯 推荐用法

### 日常使用（默认 Kimi 2.5）
```python
# 大部分任务使用 Kimi 2.5
# 快速、经济、够用
```

### 复杂任务（临时切换 Qwen3.5-Plus）
```python
# 需要深度推理时切换
# 例如：数学证明、逻辑推理、创意写作
```

### 批量任务（必须 Kimi 2.5）
```python
# 批量标注、数据清洗、批量生成
# 速度快、成本低
```

---

## 📝 切换记录

| 日期 | 主模型 | 原因 |
|------|--------|------|
| 2026-03-15 | Kimi 2.5 | 速度快、适合批量任务 |
| 之前 | Qwen3.5-Plus | 推理能力强 |

---

## 🔍 验证切换

**测试命令**：
```bash
# 测试 Kimi 2.5
curl -X POST https://coding.dashscope.aliyuncs.com/v1/chat/completions \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "kimi-2.5", "messages": [{"role": "user", "content": "Hello"}]}'

# 测试 Qwen3.5-Plus
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3.5-plus", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

## ⚠️ 注意事项

1. **API Key 通用**：两个模型都使用 DASHSCOPE_API_KEY
2. **Base URL 不同**：注意区分
3. **模型名称**：确保拼写正确
4. **上下文限制**：Kimi 2.5 支持 128K，但不要超过必要长度

---

## 🚀 最佳实践

### 1. 智能切换
```python
def get_model_for_task(task_type):
    if task_type in ['batch', 'code', 'analysis']:
        return 'kimi-2.5'
    elif task_type in ['reasoning', 'creative', 'writing']:
        return 'qwen3.5-plus'
    else:
        return 'kimi-2.5'  # 默认
```

### 2. 成本控制
```python
# 批量任务使用 Kimi 2.5
# 可以节省 50-70% 成本
```

### 3. 质量优先
```python
# 重要报告、对外内容使用 Qwen3.5-Plus
# 确保高质量输出
```

---

**切换完成！现在主模型是 Kimi 2.5** 🎉
