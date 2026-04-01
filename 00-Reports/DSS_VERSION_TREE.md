# DSS 股票预测系统 - 版本管理树

> 生成时间：2026-02-26 15:11  
> 当前分支：`feature/dss-transformer`  
> 状态：开发中

---

## 🌳 Git 分支结构

```
master (主分支 - 稳定版)
├── improve/kimi-suggestions (Kimi 建议改进)
└── feature/dss-transformer (当前开发 - Transformer/LSTM 集成) ← HEAD
```

---

## 📦 版本历史

### v2.0 (当前稳定版 - master)
**发布日期：** 2026-02-19  
**核心特性：**
- ✅ Alpha Vantage API 数据源
- ✅ Walk Forward 验证
- ✅ 基础技术指标 (RSI/MACD/均线)
- ✅ 简单评分系统

**文件：**
```
dss_v2.py (99KB) - 主程序
dss_modules/
├── data_loader.py - 数据加载
├── features.py - 特征工程
└── models.py - 模型
```

---

### v2.1 (开发中 - feature/dss-transformer)
**开发日期：** 2026-02-26  
**新增特性：**
- ✅ 自适应技术指标
- ✅ LSTM/Transformer 预测模块
- ✅ 回测引擎
- ✅ ML 预测集成
- ✅ 风控模块
- ✅ 21 年历史数据 (2004-2024)

**新增文件：**
```
dss_daily_optimized.py - 优化版主程序
dss_transformer_lstm.py - LSTM 预测 (215 行)
dss_backtest.py - 回测引擎 (241 行)
dss_adaptive_indicators.py - 自适应指标
dss_ml_predict.py - ML 预测
dss_risk.py - 风控模块
dss_sse_history.py - 历史数据
dss_market_phase.py - 市场阶段识别
dss_yearly_predictor.py - 年度预测
dss_enhanced_report.py - 增强报告
dss_validator.py - 反向验证 (5 日周期)
```

**Git 提交：**
```
917819e feat: 集成 LSTM 到 DSS 主程序
df56e94 feat: 添加回测引擎
41ed029 feat: 添加 Transformer/LSTM 预测模块
```

---

### v3.0 (规划中)
**预计发布：** 2026-03  
**计划特性：**
- [ ] 集成学习 (LSTM + LightGBM + XGBoost)
- [ ] 强化学习交易模块
- [ ] 基本面分析集成
- [ ] 情绪分析 (新闻/社交媒体)
- [ ] GNN 股票关联分析
- [ ] 自动化特征工程

---

## 📊 性能对比

| 版本 | 预测精度 | 回测收益 | 特性数量 | 数据量 |
|------|---------|---------|---------|--------|
| v2.0 | ~45% | - | 5 | 100 天 |
| v2.1 | ~60%* | +43%* | 15 | 21 年 |
| v3.0 | ~70%* | - | 20+ | 21 年 + 基本面 |

*预估数据

---

## 🔧 技术栈

### 核心依赖
```
Python 3.12+
pandas, numpy, scikit-learn
baostock (数据源)
```

### 可选依赖
```
PyTorch (LSTM/Transformer)
backtrader (回测)
xgboost, lightgbm (集成学习)
```

### API 集成
```
Alpha Vantage (美股数据)
DashScope (阿里云 AI)
百炼 AI (qwen3.5-plus)
```

---

## 📁 完整文件树

```
/home/kyj/.openclaw/workspace/
├── dss_v2.py                      # v2.0 主程序
├── dss_v3.py                      # v3.0 原型
├── dss_v4.py                      # v4.0 原型
├── dss_daily_optimized.py         # v2.1 主程序 ⭐
├── dss_daily_quick.py             # 快速版
├── dss_daily_summary.py           # 总结版
├── dss_stock_picker.py            # 选股器
├── dss_swarm.py                   # 群体智能
├── dss_transformer_lstm.py        # LSTM 预测 ⭐ NEW
├── dss_backtest.py                # 回测引擎 ⭐ NEW
├── dss_adaptive_indicators.py     # 自适应指标 ⭐ NEW
├── dss_ml_predict.py              # ML 预测 ⭐ NEW
├── dss_risk.py                    # 风控模块 ⭐ NEW
├── dss_sse_history.py             # 历史数据 ⭐ NEW
├── dss_market_phase.py            # 市场阶段 ⭐ NEW
├── dss_yearly_predictor.py        # 年度预测 ⭐ NEW
├── dss_enhanced_report.py         # 增强报告 ⭐ NEW
├── dss_validator.py               # 反向验证 ⭐ NEW
├── dss_lstm.py                    # LSTM 原型
├── dss_warning.py                 # 风险预警
├── email_system.py                # 邮件系统
├── dss_modules/
│   ├── data_loader.py             # 数据加载
│   ├── data_fundamentals.py       # 基本面数据
│   ├── features.py                # 特征工程
│   ├── models.py                  # 模型
│   ├── backtest.py                # 回测
│   ├── system_control.py          # 系统控制
│   └── kimi_cli_wrapper.py        # Kimi 接口
├── data/
│   ├── predictions/               # 预测存储
│   │   └── prediction_2026-02-26.json
│   ├── sse_package/               # SSE 历史数据包
│   │   ├── SSE_DSS 完整数据_2004-2024.csv
│   │   ├── SSE_DSS 特征矩阵.csv
│   │   ├── SSE_DSS 目标_*.csv
│   │   └── SSE_DSS 模型训练示例.py
│   └── sse_historical_data*.json  # 历史数据 JSON
├── reports/
│   ├── DSS_改进进度_20260226.md   # 进度报告
│   └── DSS_改进研究报告_20260226.md # 研究报告
├── memory/
│   ├── 2026-02-26.md              # 今日记忆
│   ├── 2026-02-25.md              # 昨日记忆
│   └── ...
└── skills/
    ├── everything-claude-code/    # Claude Code 技能
    └── evomap/                    # 自进化技能
```

---

## 🎯 待办事项

### 高优先级
- [ ] 安装 PyTorch 提升 LSTM 性能
- [ ] 集成市场状态检测 (HMM)
- [ ] 实现集成模型管理
- [ ] 完善回测报告可视化

### 中优先级
- [ ] 基本面分析模块
- [ ] 情绪分析集成
- [ ] GNN 关联分析
- [ ] 自动化特征工程

### 低优先级
- [ ] 另类数据集成
- [ ] 可视化仪表盘
- [ ] 移动端推送
- [ ] 多语言支持

---

## 📈 路线图

```
2026-02 ──┬── v2.1 发布 (Transformer + 回测)
          │
2026-03 ──┼── v3.0 发布 (集成学习 + 基本面)
          │
2026-04 ──┼── v3.5 发布 (强化学习 + GNN)
          │
2026-05 ──┴── v4.0 发布 (全功能 AI 量化系统)
```

---

## 🔐 版本发布流程

1. **开发** → `feature/*` 分支
2. **测试** → 回测验证 + 实盘模拟
3. **合并** → `git merge` 到 `master`
4. **打标签** → `git tag vX.X.X`
5. **发布** → 更新文档 + 通知用户

---

*最后更新：2026-02-26 15:11*  
*维护者：Kaguya*
