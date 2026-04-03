# DSS Factor Validation 模块

借鉴 [ShenzhenLime/quant](https://github.com/ShenzhenLime/quant) 项目的因子验证统计方法，为 DSS 生产环境提供标准化的因子有效性检验。

## 核心功能

| 功能 | 说明 | 来源 |
|-----|------|------|
| **IC/IR 计算** | Spearman 秩相关系数，衡量因子预测能力 | quant |
| **多空夏普** | 分组多空组合的年化夏普比率 | quant |
| **索替诺比率** | 只考虑下行波动的风险调整后收益 | quant |
| **多轨道测试** | 偏移调仓日期，检验因子稳健性 | quant |
| **IC 半衰期** | 因子预测能力的衰减速度 | quant |
| **单调性检验** | 分组收益是否呈现单调趋势 | quant |
| **Calmar 比率** | 年化收益 / 最大回撤 | quant |

## 快速开始

### 1. 基础验证

```python
from factor_validation import FactorValidator

# 准备数据 (date, symbol, factor, return)
df = pd.read_csv('your_factor_data.csv')

# 创建验证器
validator = FactorValidator(
    ic_ir_threshold=0.5,      # IC/IR 通过阈值
    pathway_threshold=0.8     # 多轨道稳定性阈值
)

# 验证因子
result = validator.validate(
    df, 
    factor_col='momentum_20',
    return_col='next_day_return',
    date_col='date',
    factor_name='momentum_20'
)

print(f"IC: {result.ic_mean:.4f}")
print(f"IR: {result.ir:.2f}")
print(f"通过验证: {result.pass_validation}")
```

### 2. 快速验证 (一行代码)

```python
from factor_validation import quick_validate

# 因子数据
factor_df = df[['date', 'symbol', 'momentum_20']].rename(columns={'momentum_20': 'factor'})
return_df = df[['date', 'symbol', 'next_day_return']].rename(columns={'next_day_return': 'return'})

# 快速验证
result = quick_validate(factor_df, return_df, 'momentum_20')
print(result)
```

### 3. 多因子批量验证

```python
# 验证多个因子
factors = ['momentum_5', 'momentum_20', 'rsi', 'macd']
results = []

for factor in factors:
    result = validator.validate(df, factor, 'return', 'date', factor)
    results.append(result.to_dict())
    
# 筛选有效因子
valid_factors = [r for r in results if r['pass_validation']]
```

## 核心指标解释

### IC (Information Coefficient)
- **定义**: 因子值与下期收益的 Spearman 秩相关系数
- **范围**: -1 到 1
- **解读**:
  - |IC| > 0.05: 有一定预测能力
  - |IC| > 0.1: 预测能力较强
  - IC > 0: 正向预测 (因子值高 → 收益高)
  - IC < 0: 反向预测 (因子值高 → 收益低)

### IR (Information Ratio)
- **定义**: IC均值 / IC标准差
- **解读**:
  - IR > 0.5: 因子较稳定
  - IR > 1.0: 因子优秀
  - IR < 0.3: 噪声过大

### 多轨道稳定性
- **定义**: 1 - (20轨道IC标准差 / |IC均值|)
- **解读**:
  - 稳定性 > 0.8: 因子稳健，不依赖特定日期
  - 稳定性 < 0.5: 因子可能过拟合

### IC 半衰期
- **定义**: IC 衰减至初始值一半所需的交易日数
- **应用**: 指导调仓频率
  - 半衰期 5-10 天 → 日度/周度调仓
  - 半衰期 15-25 天 → 月度调仓

## DSS 集成建议

### 1. 因子入库前验证

```python
# 新因子上线前必须通过验证
def validate_before_deploy(factor_df, return_df, factor_name):
    result = quick_validate(factor_df, return_df, factor_name)
    
    if not result['pass_validation']:
        raise ValueError(f"因子 {factor_name} 未通过验证: IR={result['ir']}")
    
    return result
```

### 2. 实时监控

```python
# 每日检查因子有效性
class FactorMonitor:
    def __init__(self):
        self.validator = FactorValidator()
        self.alert_threshold = 0.3
    
    def check(self, recent_data):
        ic_series = self.validator.calc_ic_series(
            recent_data, 'date', 'factor', 'return'
        )
        
        recent_ic = ic_series.tail(20)
        
        if abs(recent_ic.mean()) < 0.02:
            send_alert(f"因子 IC 过低: {recent_ic.mean():.4f}")
        
        if recent_ic.std() > 0.15:
            send_alert(f"因子 IC 波动过大: {recent_ic.std():.4f}")
```

### 3. 与现有回测整合

```python
from backtest import Backtester
from factor_validation import FactorValidator

class ValidatedBacktester:
    def __init__(self):
        self.backtester = Backtester()
        self.validator = FactorValidator()
    
    def run(self, prices, signals, factor_data):
        # 先验证因子
        validation = self.validator.validate(
            factor_data, 'factor', 'return', 'date'
        )
        
        if not validation.pass_validation:
            print(f"警告: 因子未通过验证 (IR={validation.ir:.2f})")
        
        # 再运行回测
        return self.backtester.run(prices, signals)
```

## 配置文件建议

```yaml
# dss/config/factor_validation.yaml
validation:
  ic_ir_threshold: 0.5
  pathway_threshold: 0.8
  min_ic_size: 10
  n_groups: 10
  annual_trading_days: 242

monitoring:
  ic_alert_threshold: 0.02
  volatility_alert_threshold: 0.15
  lookback_days: 20
```

## 与 quant 项目的区别

| 方面 | quant | DSS factor_validation |
|-----|-------|----------------------|
| 定位 | 研究框架 | 生产验证 |
| 数据源 | Tushare + DuckDB | 任意 DataFrame |
| 回测深度 | 完整多轨道 + 真实成本 | 简化版多轨道 |
| 实时性 | 离线研究 | 支持实时监控 |
| 输出 | 报告 + 图表 | 结构化结果 + 预警 |

## 依赖

```
pandas >= 2.0.0
numpy >= 1.24.0
scipy >= 1.10.0
```

## 参考

- [ShenzhenLime/quant](https://github.com/ShenzhenLime/quant) - 原始量化研究框架
- quant 的 `factor_analyze.py` - 统计方法来源
