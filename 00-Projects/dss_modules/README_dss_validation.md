# DSS 因子全量验证指南

## 快速开始

### 1. 准备数据

数据格式要求 (CSV/Parquet/Feather):

```
date,symbol,return,momentum_5,momentum_20,rsi,macd,...
2024-01-01,000001.SZ,0.015,0.5,1.2,65,-0.3,...
2024-01-01,000002.SZ,-0.008,0.3,0.8,45,0.1,...
...
```

必需列:
- `date`: 交易日期
- `symbol`: 股票代码
- `return`: 下期收益 (如次日收益率)

### 2. 运行验证

```bash
# 基础用法 (自动识别所有因子)
python validate_dss_factors.py --data-path ./dss_data.csv

# 指定阈值
python validate_dss_factors.py \
    --data-path ./dss_data.csv \
    --ic-ir-threshold 0.5 \
    --pathway-threshold 0.8

# 只验证指定因子
python validate_dss_factors.py \
    --data-path ./dss_data.csv \
    --factors momentum_5 momentum_20 rsi

# 自定义列名
python validate_dss_factors.py \
    --data-path ./dss_data.csv \
    --date-col trade_date \
    --return-col next_return \
    --symbol-col stock_code

# 指定输出格式
python validate_dss_factors.py \
    --data-path ./dss_data.csv \
    --formats json csv
```

### 3. 查看报告

验证完成后生成:
- `dss_factor_validation_YYYY-MM-DD.json` - 完整数据
- `dss_factor_validation_YYYY-MM-DD.csv` - Excel可打开
- `dss_factor_validation_YYYY-MM-DD.md` - 可读报告

## Python API 使用

```python
from validate_dss_factors import validate_dss_factors

# 一键验证
report, files = validate_dss_factors(
    data_path='./dss_data.csv',
    output_dir='./reports',
    ic_ir_threshold=0.3,
    pathway_threshold=0.7
)

# 获取有效因子
from factor_validation_batch import FactorValidationBatch
batch = FactorValidationBatch()
valid_factors = batch.get_valid_factors(report)
print(f"有效因子: {valid_factors}")

# 获取 Top 因子
top_ir = batch.get_top_factors(report, metric='ir', n=10)
```

## 阈值调整建议

| 场景 | IC/IR 阈值 | 稳定性阈值 | 预期通过率 |
|------|-----------|-----------|-----------|
| 严格筛选 | 0.5 | 0.8 | 10-20% |
| 标准筛选 | 0.3 | 0.7 | 20-40% |
| 宽松筛选 | 0.1 | 0.5 | 40-60% |
| 探索性 | 0.0 | 0.0 | 100% |

## 输出指标说明

| 指标 | 说明 | 参考值 |
|------|------|--------|
| IC | 信息系数 (Spearman) | \|IC\| > 0.02 有效 |
| IR | 信息比率 (IC均值/标准差) | IR > 0.5 稳定 |
| 多空夏普 | 多头组-空头组年化夏普 | > 1.0 优秀 |
| 多轨道稳定性 | 20条路径IC变异系数 | > 0.7 稳健 |
| IC半衰期 | 预测能力衰减天数 | 指导持仓周期 |
| 单调性 | 分组收益单调程度 | > 0.5 良好 |

## 集成到 DSS 流程

```python
# 每日收盘后验证
from validate_dss_factors import validate_dss_factors

def daily_factor_check():
    report, _ = validate_dss_factors(
        data_path=f'./data/dss_{today}.csv',
        output_dir='./daily_reports',
        ic_ir_threshold=0.3
    )
    
    # 检查是否有因子失效
    for result in report.results:
        if not result['pass_validation'] and result['factor_name'] in active_factors:
            send_alert(f"因子 {result['factor_name']} 失效!")
    
    # 更新有效因子池
    valid_factors = [r['factor_name'] for r in report.results 
                    if r['pass_validation']]
    update_factor_pool(valid_factors)
```

## 常见问题

**Q: 数据量大时很慢怎么办?**
A: 可以采样测试或并行验证:
```python
# 按日期采样
sample_df = df[df['date'].isin(df['date'].unique()[::5])]  # 每5天取1天
```

**Q: 如何处理缺失值?**
A: 脚本会自动删除包含缺失值的行。建议预处理:
```python
df = df.fillna(method='ffill')  # 前向填充
df = df.dropna()  # 删除仍有缺失的行
```

**Q: 如何验证不同周期的因子?**
A: 分别准备数据文件:
- `dss_daily.csv` - 日频因子
- `dss_weekly.csv` - 周频因子
然后分别运行验证。
