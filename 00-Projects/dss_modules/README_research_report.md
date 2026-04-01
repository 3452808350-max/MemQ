# 研报摘要爬虫模块

## 功能概述

从东方财富研报中心获取股票研报摘要、评级和目标价。

## 数据来源

- 东方财富研报中心: https://data.eastmoney.com/report/
- API: `https://reportapi.eastmoney.com/report/list`

## 安装依赖

```bash
pip install requests pandas
```

## 快速使用

```python
from research_report_crawler import (
    get_research_reports,
    parse_rating,
    parse_target_price,
    get_rating_summary,
    get_hot_reports,
    get_batch_rating_summary
)

# 1. 获取单只股票研报
reports = get_research_reports('600519', page_size=10)
for r in reports:
    print(f"{r['title']} - {r['broker_short']} - {r['rating']}")

# 2. 获取评级汇总统计
summary = get_rating_summary('600519', days=90)
print(f"综合评级: {summary['consensus']}")
print(f"买入: {summary['buy_count']}, 增持: {summary['overweight_count']}")
print(f"平均目标价: {summary['target_price_avg']}")

# 3. 解析评级
rating = parse_rating('买入')
# {'name': '买入', 'value': 3, 'direction': 'positive', 'description': '强烈推荐买入'}

# 4. 获取热门研报
hot = get_hot_reports(page_size=20)

# 5. 批量获取评级汇总
symbols = ['600519', '002594', '300750', '601318']
summaries = get_batch_rating_summary(symbols, days=90)
```

## API函数说明

### get_research_reports(symbol, page_size=20, days=None, rating_filter=None)

获取股票研报摘要。

**参数:**
- `symbol`: 股票代码 (如 '600519', 'SH600519')
- `page_size`: 返回研报数量 (默认20)
- `days`: 限制天数 (如30表示最近30天)
- `rating_filter`: 评级过滤 ('买入', '增持', '中性', '减持', '卖出')

**返回:**
```python
[{
    'title': '研报标题',
    'stock_name': '股票名称',
    'stock_code': '股票代码',
    'broker': '券商全称',
    'broker_short': '券商简称',
    'publish_date': datetime,
    'publish_date_str': '2026-03-25',
    'rating': '买入',
    'rating_value': 3,
    'target_price': 1773.0,
    'target_price_low': 1686.0,
    'eps_next_year': 73.886,
    'pe_next_year': 19.6,
    'researcher': '研究员姓名',
    'pdf_url': '研报PDF链接',
}]
```

### get_rating_summary(symbol, days=90)

获取评级汇总统计。

**返回:**
```python
{
    'total_reports': 28,
    'buy_count': 21,
    'overweight_count': 5,
    'neutral_count': 2,
    'sell_count': 0,
    'avg_rating': 2.68,
    'consensus': '强烈推荐',  # 强烈推荐/推荐/中性偏多/中性/谨慎/回避
    'target_price_avg': 1707.0,
    'target_price_median': 1773.0,
    'latest_reports': [...],  # 最近5条研报
}
```

### parse_rating(rating_str)

解析评级字符串。

```python
>>> parse_rating('买入')
{'name': '买入', 'value': 3, 'direction': 'positive', 'description': '强烈推荐买入'}

>>> parse_rating('优于大市')  # 自动标准化
{'name': '增持', 'value': 2, 'direction': 'positive', 'description': '建议增持'}
```

### parse_target_price(report)

解析目标价信息。

```python
>>> parse_target_price(report)
{
    'target_price': 1773.0,
    'target_price_low': 1686.0,
    'price_range': '1686.00 - 1773.00',
    'has_target': True,
    'upside': None,  # 需要传入当前价格
}
```

## 评级系统说明

| 评级 | 数值 | 方向 |
|------|------|------|
| 买入 | 3 | positive |
| 增持 | 2 | positive |
| 持有/中性 | 1 | neutral |
| 减持 | -1 | negative |
| 卖出 | -2 | negative |

**综合评级判断:**
- avg_rating >= 2.5: 强烈推荐
- avg_rating >= 1.5: 推荐
- avg_rating >= 0.5: 中性偏多
- avg_rating >= -0.5: 中性
- avg_rating >= -1.5: 谨慎
- avg_rating < -1.5: 回避

## 注意事项

1. 该模块使用东方财富公开API，无需登录
2. 请求有频率限制，批量获取时自动添加随机延时
3. 研报PDF下载链接需要登录东方财富账号
4. 目标价、EPS、PE等数据来自券商研报，仅供参考