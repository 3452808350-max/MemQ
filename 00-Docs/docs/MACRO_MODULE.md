# DSS 宏观事件分析模块

> **状态**: 独立测试阶段 (v0.1)  
> **创建时间**: 2026-03-02  
> **目标**: 测试成熟后集成到 DSS 主系统

---

## 📋 功能概述

本模块为 DSS 选股系统增加宏观事件分析能力，解决原有系统无法捕捉地缘政治、宏观经济事件的问题。

### 核心功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 📊 宏观指标监控 | 油价、VIX、美元指数、国债收益率、黄金 | ✅ 已实现 |
| 📰 新闻情绪分析 | 使用 DashScope LLM 分析财经新闻 | 🟡 框架就绪 (需接入新闻 API) |
| 🎯 行业冲击评估 | 自动判断事件对哪些行业受益/受损 | ✅ 已实现 |
| ⚠️ 风险指数计算 | 综合宏观风险指数 (0-100) | ✅ 已实现 |

---

## 🚀 使用方法

### 独立测试

```bash
# 运行完整测试套件
python3 /home/kyj/.openclaw/workspace/test_macro_analyzer.py
```

### 在 Python 中调用

```python
from dss_modules.macro_analyzer import run_macro_analysis

# 运行分析
result = run_macro_analysis(stock_list=[
    ('sh.600519', 'consumer'),  # 贵州茅台
    ('sh.601111', 'airline'),   # 中国国航
    ('sh.601857', 'energy'),    # 中国石油
])

# 查看结果
print(f"宏观风险指数：{result['risk_index']['risk_index']}")
print(f"个股影响：{result['stock_impacts']}")
```

### 获取宏观指标

```python
from dss_modules.macro_analyzer import get_macro_indicators

indicators = get_macro_indicators()
print(indicators)
# 输出：
# {
#   'oil_price': 78.5,
#   'vix': 18.2,
#   'dxy': 103.5,
#   'treasury_10y': 4.2,
#   'gold': 1950.0,
#   'timestamp': '2026-03-02T10:30:00'
# }
```

### 评估个股影响

```python
from dss_modules.macro_analyzer import assess_industry_impact

macro_changes = {
    'oil_price_change_7d': 15.0,  # 油价上涨 15%
    'vix_change_7d': 25.0,        # VIX 上涨 25%
}

news_analysis = {
    'sentiment_score': -30,
    'hurt_industries': ['airline'],
    'benefit_industries': ['energy'],
    'confidence': 0.7
}

impact = assess_industry_impact(
    macro_changes=macro_changes,
    news_analysis=news_analysis,
    stock_symbol='sh.601111',
    stock_industry='airline'
)

print(f"影响系数：{impact}")  # 输出：-0.3 (负面影响)
```

---

## 📁 文件结构

```
/home/kyj/.openclaw/workspace/
├── dss_modules/
│   └── macro_analyzer.py      # 宏观分析模块
├── test_macro_analyzer.py      # 独立测试脚本
├── docs/
│   └── MACRO_MODULE.md         # 本文档
└── data_cache/
    └── macro/
        ├── macro_history.json  # 历史宏观数据 (自动保存)
        └── macro_report_*.json # 分析报告 (自动保存)
```

---

## 🔧 配置说明

### API Keys

在 `macro_analyzer.py` 顶部配置：

```python
DASHSCOPE_API_KEY = "sk-e8b53592ebe841f28a03d4d54024761c"  # LLM 新闻分析
FRED_API_KEY = "c917a48f98933615e6a208e7474b810c"        # 美国宏观经济数据
ALPHA_VANTAGE_KEY = "BBQTETM9CS8X8LI8"                     # 油价、VIX 等
```

### 行业分类

在 `INDUSTRY_MAP` 中配置股票与行业的映射：

```python
INDUSTRY_MAP = {
    'airline': ['中国国航', '南方航空', 'sh.601111', 'sh.600029'],
    'energy': ['中国石油', '中国石化', 'sh.601857', 'sh.600028'],
    'bank': ['工商银行', '建设银行', 'sh.601398', 'sh.601939'],
    # ... 添加更多
}
```

---

## 📊 输出说明

### 宏观风险指数

| 指数范围 | 等级 | 含义 |
|----------|------|------|
| 0-39 | 🟢 LOW | 低风险，市场环境良好 |
| 40-59 | 🟡 NORMAL | 正常风险水平 |
| 60-69 | 🟠 ELEVATED | 风险升高，需谨慎 |
| 70-100 | 🔴 HIGH | 高风险，建议防御 |

### 个股影响系数

| 系数范围 | 含义 | 建议 |
|----------|------|------|
| +0.2 ~ +1.0 | 正面影响 | 可考虑加分 |
| -0.2 ~ +0.2 | 中性影响 | 无需调整 |
| -1.0 ~ -0.2 | 负面影响 | 建议减分 |

---

## 🔄 集成到 DSS 主系统

测试成熟后，可按以下方式集成：

### 1. 在 `dss_v4.py` 中导入

```python
from dss_modules.macro_analyzer import run_macro_analysis

def analyze_stock_with_macro(symbol, name, industry, base_score):
    """带宏观调整的个股分析"""
    # 运行宏观分析
    macro_result = run_macro_analysis(stock_list=[(symbol, industry)])
    
    # 获取宏观调整系数
    macro_adjustment = macro_result['stock_impacts'][0]['macro_adjustment']
    
    # 调整原始评分
    adjusted_score = base_score + (macro_adjustment * 20)  # 放大 20 倍
    
    return adjusted_score
```

### 2. 在选股流程中调用

```python
# 原有流程
analysis = picker.analyze_stock(code)
base_score = analysis['total_score']

# 增加宏观调整
adjusted_score = analyze_stock_with_macro(code, name, industry, base_score)

# 使用调整后的评分排序
```

---

## 🧪 测试计划

### 阶段 1: 独立测试 (当前阶段)

- [x] 宏观指标获取测试
- [x] 风险指数计算测试
- [x] 个股影响评估测试
- [ ] 新闻情绪分析测试 (需接入新闻 API)
- [ ] 回测验证 (用历史事件验证准确性)

### 阶段 2: 集成测试

- [ ] 与 DSS v4 集成
- [ ] 对比集成前后选股表现
- [ ] 调整参数优化效果

### 阶段 3: 生产部署

- [ ] 加入每日定时任务
- [ ] 生成宏观事件报告
- [ ] 邮件推送重大风险预警

---

## 📝 待改进事项

1. **新闻 API 接入** - 当前新闻分析为框架，需接入真实新闻源
   - 可选：新浪财经、东方财富、华尔街见闻
   - 或使用 RSSHub 抓取财经 RSS

2. **更多宏观指标** - 当前指标有限，可增加：
   - 信用利差 (Credit Spread)
   - 波动率期限结构
   - 资金流向数据

3. **行业分类细化** - 当前行业分类较粗，可细化到：
   - 航空 → 国际航空 / 国内航空
   - 能源 → 石油开采 / 炼油 / 新能源

4. **回测验证** - 用历史事件验证模块准确性：
   - 2020 年疫情爆发
   - 2022 年俄乌冲突
   - 2023 年硅谷银行事件

---

## 📚 参考资料

- [Microsoft Qlib](https://github.com/microsoft/qlib) - AI 量化平台
- [Microsoft RD-Agent](https://github.com/microsoft/RD-Agent) - 自动化量化 R&D
- [FRED API](https://fred.stlouisfed.org/docs/api/fred/) - 美国宏观经济数据
- [Alpha Vantage](https://www.alphavantage.co/) - 金融市场数据 API

---

*最后更新：2026-03-02*
