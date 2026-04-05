# 异步情绪分析功能添加完成

## 文件位置
`~/文档/anlyse/dss-project/integration/real_data_sources.py`

## 新增内容

### 1. 导入语句更新
- 添加了 `asyncio`, `aiohttp`
- 添加了 `dataclass`, `OrderedDict`, `time`

### 2. AsyncSentimentAnalyzer 类
完整实现了异步情绪分析器，包含：

#### 核心功能
- **异步 HTTP 请求**: 使用 `aiohttp` 进行非阻塞网络请求
- **并发获取**: 使用 `asyncio.gather()` 同时获取多个股票的情绪数据
- **多数据源支持**:
  - Reddit (Tradestie API) - 免费，无需认证
  - NewsAPI - 需要 API 密钥
  - Twitter/X - 需要 Bearer Token

#### 缓存机制
- **TTL 缓存**: 默认 5 分钟 (300秒)
- **LRU 淘汰**: 最大 100 条缓存
- **缓存键**: `{source}:{ticker}`
- **方法**: `clear_cache()` 支持按条件清除

#### 主要方法
- `fetch_reddit_sentiment(ticker)` - 获取 Reddit 情绪
- `fetch_news_sentiment(ticker, days)` - 获取新闻情绪
- `fetch_twitter_sentiment(ticker)` - 获取 Twitter 情绪
- `async_fetch_sentiment(tickers, sources)` - 并发获取多股票情绪
- `close()` - 关闭 aiohttp session

### 3. RealDataSources 类更新

#### 新增方法
- `get_sentiment_async(tickers, sources)` - 异步入口方法
- `get_sentiment_sync(tickers, sources)` - 同步包装器（向后兼容）
- `close_async_resources()` - 清理异步资源

### 4. 测试函数
- `test_async_sentiment_analyzer()` - 异步功能测试
- `test_sync_sentiment()` - 同步包装器测试

## 使用示例

### 异步方式（推荐）
```python
import asyncio
from integration.real_data_sources import RealDataSources

async def main():
    ds = RealDataSources()
    
    # 并发获取多股票情绪
    results = await ds.get_sentiment_async(
        tickers=['AAPL', 'MSFT', 'GOOGL'],
        sources=['reddit', 'news']  # 可选: 'reddit', 'news', 'twitter'
    )
    
    for ticker, data in results.items():
        agg = data['aggregated_sentiment']
        print(f"{ticker}: {agg['interpretation']} (score: {agg['score']})")
    
    await ds.close_async_resources()

asyncio.run(main())
```

### 同步方式（向后兼容）
```python
from integration.real_data_sources import RealDataSources

ds = RealDataSources()
results = ds.get_sentiment_sync(['AAPL', 'MSFT'], sources=['reddit'])
```

### 直接使用 AsyncSentimentAnalyzer
```python
from integration.real_data_sources import AsyncSentimentAnalyzer

analyzer = AsyncSentimentAnalyzer(
    news_api_key='your_key',
    twitter_bearer_token='your_token',
    cache_ttl=300
)

# 单个数据源
reddit_data = await analyzer.fetch_reddit_sentiment('AAPL')

# 多数据源并发
results = await analyzer.async_fetch_sentiment(
    ['AAPL', 'MSFT'],
    sources=['reddit', 'news', 'twitter']
)

await analyzer.close()
```

## 返回数据结构

```python
{
    'AAPL': {
        'ticker': 'AAPL',
        'sources': {
            'reddit': {...},
            'news': {...},
            'twitter': {...}
        },
        'aggregated_sentiment': {
            'score': 0.65,           # 聚合情绪分数 (0-1)
            'confidence': 0.67,      # 置信度 (基于数据源数量)
            'sources_used': 2,       # 使用的数据源数量
            'interpretation': '看涨'  # 中文解读
        },
        'timestamp': '2026-04-04T...'
    }
}
```

## 向后兼容性
✅ 原有同步方法完全保留
✅ `get_reddit_sentiment_data()` 继续可用
✅ 所有现有功能不受影响

## 文件大小
- 原文件: ~400 行
- 新文件: ~900+ 行
- 新增代码: ~500 行

## 依赖
- `aiohttp` - 异步 HTTP 客户端
- `asyncio` - Python 标准库

## 注意事项
1. Reddit API (Tradestie) 是免费的，无需认证
2. NewsAPI 和 Twitter API 需要配置密钥
3. 使用完后建议调用 `close_async_resources()` 或 `analyzer.close()` 清理资源
4. 缓存默认 TTL 5 分钟，可通过参数调整
