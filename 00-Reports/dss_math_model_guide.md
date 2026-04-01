# DSS 系统 - Math 模型使用指南

## 何时使用 Math 模型

### ✅ 推荐使用

1. **复杂数学计算**
   - 财务比率计算（ROE、PE、PB 等）
   - 统计指标（夏普比率、索提诺比率等）
   - 风险评估（VaR、波动率等）

2. **统计检验**
   - 假设检验（t 检验、卡方检验）
   - 相关性分析（皮尔逊、斯皮尔曼）
   - 回归分析

3. **时间序列**
   - 移动平均、指数平滑
   - ARIMA 模型参数计算
   - 季节性分解

4. **公式推导**
   - 量化策略公式验证
   - 数学证明
   - 算法复杂度分析

### ❌ 不推荐使用

1. **数据获取** - 用 Alpha Vantage API
2. **数据清洗** - 用 Pandas
3. **实时计算** - 用 Python 脚本
4. **图表生成** - 用 Matplotlib
5. **回测执行** - 用 DSS 回测引擎

## 调用示例

```python
# 调用 Math 模型
def calculate_financial_ratios(data):
    prompt = f"""
    请计算以下财务指标：
    - 净利润：{data['net_income']}
    - 股东权益：{data['equity']}
    - 股价：{data['price']}
    - 每股收益：{data['eps']}
    
    请计算：ROE、PE、PB
    """
    
    response = call_model("bailian/qwen-math-plus", prompt)
    return parse_response(response)
```

## 性能对比

| 任务 | Math 模型 | Python 脚本 | 推荐 |
|------|----------|------------|------|
| 简单计算 | 3 秒 | 0.01 秒 | Python |
| 复杂公式推导 | 5 秒 | N/A | Math |
| 统计检验 | 4 秒 | 0.1 秒 | Python |
| 公式解释 | 3 秒 | N/A | Math |
| 批量计算 | 10 秒 | 0.5 秒 | Python |

## 最佳实践

1. **混合使用** - Math 模型负责公式推导，Python 负责实际计算
2. **缓存结果** - Math 模型计算结果缓存起来重复使用
3. **验证输出** - Math 模型可能出错，需要验证
4. **限制场景** - 只在复杂数学场景使用，避免滥用

---

*最后更新：2026-03-13*
