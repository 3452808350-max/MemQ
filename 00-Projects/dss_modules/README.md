# Seeking Alpha 爬虫模块

获取Seeking Alpha中概股分析文章的Python爬虫。

## 功能

- ✅ `get_seeking_alpha_analysis(symbol)` - 获取股票分析文章
- ✅ `get_trending_china_stocks()` - 获取热门中概股列表
- ✅ 解析文章标题、作者、日期、链接
- ✅ 从标题推断评级 (Bullish/Bearish)
- ✅ 反爬处理：随机UA、请求间隔、重试机制

## 使用方法

```python
from seeking_alpha_crawler import SeekingAlphaCrawler

# 创建爬虫实例
crawler = SeekingAlphaCrawler(delay_range=(2, 5))  # 延迟2-5秒

# 获取BABA分析文章
articles = crawler.get_seeking_alpha_analysis("BABA", pages=2)
for article in articles:
    print(f"标题: {article['title']}")
    print(f"作者: {article['author']}")
    print(f"日期: {article['date']}")
    print(f"评级: {article['rating']}")
    print(f"链接: {article['link']}")
    print()

# 获取热门中概股
stocks = crawler.get_trending_china_stocks()
for stock in stocks:
    print(f"{stock['symbol']}: {stock['name']}")

# 获取文章摘要
summary = crawler.get_article_summary(article['link'])
print(summary['summary'])
```

## 便捷函数

```python
from seeking_alpha_crawler import get_seeking_alpha_analysis, get_trending_china_stocks

# 快速获取文章
articles = get_seeking_alpha_analysis("BABA")

# 快速获取中概股列表
stocks = get_trending_china_stocks()
```

## 支持的中概股

| 代码 | 公司 |
|------|------|
| BABA | 阿里巴巴 |
| JD | 京东 |
| PDD | 拼多多 |
| NIO | 蔚来 |
| BIDU | 百度 |
| TME | 腾讯音乐 |
| BILI | 哔哩哔哩 |
| LI | 理想汽车 |
| XPEV | 小鹏汽车 |
| FUTU | 富途控股 |

## 返回数据结构

### 文章数据
```python
{
    "article_id": "4885021",
    "title": "Alibaba Q3: AI Transition...",
    "author": "Johnny Zhang, CFA",
    "date": "2026-03-23",
    "comments": 5,
    "link": "https://seekingalpha.com/article/4885021-...",
    "rating": "Bullish",  # 或 "Bearish", "Neutral", None
    "symbol": "BABA",
    "crawled_at": "2026-03-25T08:43:50.123456"
}
```

### 股票数据
```python
{
    "symbol": "BABA",
    "name": "Alibaba Group Holding Limited",
    "price": "125.48",
    "change": "-0.46%",
    "url": "https://seekingalpha.com/symbol/BABA"
}
```

## 注意事项

1. **请求间隔**：默认延迟2-5秒，避免触发反爬
2. **403错误**：部分请求可能被拦截，爬虫会自动重试
3. **登录墙**：完整文章内容需要登录查看
4. **数据准确性**：评级是从标题推断，仅供参考

## 测试结果

```
✅ 获取到 40 篇 BABA 分析文章
✅ 评级识别：Bullish/Bearish
✅ 作者、日期、链接正确提取
✅ 部分股票信息获取成功（受反爬限制）
```

## 文件位置

```
/home/kyj/.openclaw/workspace/dss_modules/seeking_alpha_crawler.py
```