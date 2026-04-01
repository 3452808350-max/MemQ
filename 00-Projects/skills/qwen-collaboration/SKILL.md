# Qwen协作Skill

## 概述
这个Skill定义了Kaguya和Qwen之间的高效协作协议，包含专用术语、任务格式和响应模板。

## 核心概念

### 1. 任务类型编码
```
F-xxx: 金融分析任务
P-xxx: 论文理解任务  
C-xxx: 代码开发任务
R-xxx: 研究报告任务
A-xxx: 算法优化任务
```

### 2. 数据格式标准
```json
{
  "task_id": "F-001",
  "priority": "high|medium|low",
  "data_format": "technical_indicators|paper_abstract|code_spec",
  "expected_output": "analysis_report|summary_table|code_file",
  "timeout_minutes": 10
}
```

### 3. 响应模板
```
✅ [任务完成] F-001
📊 分析结果: [简要总结]
🔍 关键发现: [1-3个要点]
📈 建议: [具体建议]
⏱️ 用时: X分钟
```

## 具体协议

### 金融分析协议 (F-协议)
```
Kaguya -> Qwen:
[F-分析] {股票代码} {时间范围} {分析深度}

Qwen -> Kaguya:
[F-结果] {综合评分} {趋势判断} {关键信号}
```

### 论文精读协议 (P-协议)
```
Kaguya -> Qwen:
[P-精读] {论文标题/摘要} {重点领域}

Qwen -> Kaguya:  
[P-摘要] {创新点} {技术细节} {实用价值}
```

### 代码开发协议 (C-协议)
```
Kaguya -> Qwen:
[C-开发] {功能描述} {输入输出} {约束条件}

Qwen -> Kaguya:
[C-完成] {代码文件} {测试结果} {使用说明}
```

## 使用示例

### 示例1: 快速金融分析
```python
# Kaguya发送
task = {
    "type": "F-快速分析",
    "symbol": "AAPL",
    "indicators": ["RSI", "MACD", "MA20"],
    "urgency": "high"
}

# Qwen回复
result = {
    "status": "完成",
    "summary": "温和多头，建议持有",
    "signals": ["价格>MA20", "MACD金叉"],
    "risk_level": "低"
}
```

### 示例2: 论文技术要点
```python
# Kaguya发送  
task = {
    "type": "P-技术要点",
    "paper": "StockMixer论文",
    "focus": ["架构创新", "性能对比"]
}

# Qwen回复
result = {
    "innovations": ["MLP基础", "多尺度混合"],
    "performance": "58.7%方向准确率",
    "significance": "SOTA水平"
}
```

## 实施步骤

1. **初始化协议**
   - 双方确认使用此Skill
   - 测试基本通信

2. **任务路由**
   - Kaguya根据任务类型选择协议
   - 使用标准化格式发送

3. **结果处理**
   - Qwen使用模板回复
   - Kaguya解析并呈现给用户

## 优势

1. **效率提升** - 减少自然语言歧义
2. **一致性** - 标准化输入输出格式  
3. **可扩展** - 容易添加新协议类型
4. **可追溯** - 任务ID便于跟踪

## 文件位置
- 此文件: `/home/kyj/.openclaw/workspace/skills/qwen-collaboration/SKILL.md`
- 相关脚本: `/home/kyj/.openclaw/workspace/skills/qwen-collaboration/`

---
*创建日期: 2026-02-17*
*版本: 1.0*
