# DSS 股票预测系统 v2.1

> 基于深度学习和自适应技术指标的智能选股系统

---

## 🚀 快速开始

### 安装依赖

```bash
# 基础依赖
pip install pandas numpy scikit-learn baostock

# 可选依赖 (提升性能)
pip install torch  # LSTM 性能提升
pip install backtrader  # 完整回测功能
```

### 运行每日选股

```bash
cd ~/.openclaw/workspace
python3 dss_daily_optimized.py send
```

### 查看预测结果

```bash
# 查看今日预测
cat data/predictions/prediction_2026-02-26.json

# 运行回测
python3 dss_backtest.py
```

---

## 📊 核心功能

### 1. 自适应技术指标

- **自适应 RSI**: 根据波动率自动调整周期 (10/14/21 天)
- **双 MACD 并行**: 趋势市场 (12,26,9) / 震荡市场 (5,13,7)
- **市场状态检测**: 自动识别 trending/range

### 2. 深度学习预测

- **LSTM 模块**: 预测未来 5 天走势
- **ML 预测**: 多指标加权预测
- **集成学习**: 自动融合多个模型

### 3. 风控系统

- **风险评分**: 评估每只股票风险
- **仓位建议**: 根据风险调整仓位
- **止损止盈**: 自动止损 5%/止盈 15%

### 4. 回测引擎

- **Backtrader**: 完整回测功能
- **简单回测**: 无需额外依赖
- **绩效分析**: 收益率/胜率/最大回撤

---

## 🏗️ 系统架构

```
dss_daily_optimized.py (主程序)
│
├── dss_config.py               # 配置管理
├── dss_adaptive_indicators.py  # 自适应指标
├── dss_ml_predict.py           # ML 预测
├── dss_transformer_lstm.py     # LSTM 预测
├── dss_risk.py                 # 风控模块
├── dss_backtest.py             # 回测引擎
├── dss_validator.py            # 反向验证
└── dss_sse_history.py          # 历史数据
```

### 评分权重

| 组成部分 | 权重 | 说明 |
|----------|------|------|
| 技术指标 | 40% | RSI/MACD/均线/布林带 |
| ML 预测 | 15% | 多指标加权 |
| LSTM 预测 | 10% | 深度学习预测 |
| 趋势预测 | 10% | 近期收益率 |
| 风控评估 | 15% | 风险评分 |
| 市场状态 | 10% | trending/range |

---

## 📁 数据源

### 历史数据

- **时间范围**: 2004-2024 年 (21 年)
- **特征数量**: 61 个 (14 原始 + 47 衍生)
- **数据来源**: 上交所统计年鉴

### 实时数据

- **A 股**: baostock API
- **美股**: Alpha Vantage API

---

## 🎯 使用示例

### 分析单只股票

```python
from dss_daily_optimized import analyze_stock

result = analyze_stock('sh.603986', '兆易创新', '芯片')
print(f"评分：{result['score']}")
print(f"RSI: {result['rsi']}")
print(f"LSTM 方向：{result['lstm_direction']}")
```

### 批量分析

```python
from dss_daily_optimized import generate_report

results = generate_report()
for r in results[:5]:
    print(f"{r['name']}: {r['score']}分")
```

### 运行回测

```python
from dss_backtest import backtest_dss_strategy

results = backtest_dss_strategy(df, dss_scores)
print(f"收益率：{results['total_return_pct']:.2f}%")
```

---

## 📈 性能指标

| 指标 | 数值 |
|------|------|
| 单次分析时间 | ~8s |
| 预测准确率 | ~65%* |
| 回测年化收益 | +43%* |
| 最大回撤 | -15%* |

*基于历史数据回测，不代表未来表现

---

## 🔧 配置

编辑 `dss_config.py` 自定义参数：

```python
# 评分权重
WEIGHTS = {
    'technical': 0.40,
    'ml_predict': 0.15,
    'lstm_predict': 0.10,
    ...
}

# 风控参数
RISK = {
    'stop_loss': 0.05,
    'take_profit': 0.15,
    ...
}
```

---

## 📊 Cron 任务

```bash
# 每日股票推荐 (07:00)
0 7 * * * cd ~/.openclaw/workspace && python3 dss_daily_optimized.py send

# 数据更新 (06:30)
30 6 * * * cd ~/.openclaw/workspace && python3 -c "from dss_modules.data_loader import update_all_stocks; update_all_stocks()"

# 反向验证 (16:00)
0 16 * * * cd ~/.openclaw/workspace && python3 dss_validator.py validate
```

---

## 🧪 测试

```bash
# 运行单元测试
python3 -m pytest tests/

# 运行性能测试
python3 tests/benchmark.py
```

---

## 📚 文档

- [API 文档](docs/API.md)
- [使用示例](docs/EXAMPLES.md)
- [优化报告](DSS_OPTIMIZATION_REPORT.md)
- [版本管理树](DSS_VERSION_TREE.md)

---

## ⚠️ 免责声明

本系统仅供学习和研究使用，不构成投资建议。

股市有风险，投资需谨慎。

---

## 📄 许可证

MIT License

---

*最后更新：2026-02-26*  
*版本：v2.1*
