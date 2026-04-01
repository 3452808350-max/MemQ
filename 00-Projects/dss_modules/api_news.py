"""
新闻情绪分析模块
获取财经新闻并分析市场情绪
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import re

# News API 配置
NEWSAPI_BASE = "https://newsapi.org/v2"
NEWSAPI_KEY = ""  # 用户需自行申请：https://newsapi.org/register

# 备用免费新闻源
CURRENTS_API_BASE = "https://api.currentsapi.services/v1"
CURRENTS_API_KEY = ""  # https://currentsapi.services/

# 财经关键词（中文 + 英文）
FINANCE_KEYWORDS_CN = [
    '股票', '股市', '财经', '经济', '金融', '投资', '基金', '债券',
    '利率', '通胀', 'GDP', '财报', '盈利', '亏损', '并购', 'IPO'
]

FINANCE_KEYWORDS_EN = [
    'stock', 'market', 'finance', 'economy', 'investment', 'fund',
    'interest rate', 'inflation', 'GDP', 'earnings', 'profit', 'loss',
    'merger', 'acquisition', 'IPO', 'Federal Reserve'
]

# 股票相关新闻搜索模板
STOCK_NEWS_QUERIES = {
    'AAPL': ['Apple', 'iPhone', 'Tim Cook'],
    'TSLA': ['Tesla', 'Elon Musk', 'EV'],
    'NVDA': ['NVIDIA', 'AI chip', 'GPU'],
    'MSFT': ['Microsoft', 'Azure', 'AI'],
    'GOOGL': ['Google', 'Alphabet', 'Search'],
    'AMZN': ['Amazon', 'AWS', 'E-commerce'],
    'META': ['Meta', 'Facebook', 'Metaverse'],
}


def get_finance_news(keywords: List[str] = None, language: str = 'zh', page_size: int = 20) -> List[Dict]:
    """
    获取财经新闻
    
    Args:
        keywords: 搜索关键词
        language: 语言 (zh/en)
        page_size: 返回数量
    
    Returns:
        新闻列表
    """
    if not NEWSAPI_KEY:
        print("[!] NewsAPI Key 未配置，使用模拟数据")
        return _get_mock_news()
    
    try:
        url = f"{NEWSAPI_BASE}/everything"
        
        # 构建搜索词
        if keywords is None:
            keywords = FINANCE_KEYWORDS_EN if language == 'en' else FINANCE_KEYWORDS_CN
        
        query = ' OR '.join(keywords)
        
        params = {
            'q': query,
            'language': language,
            'sortBy': 'publishedAt',
            'pageSize': page_size,
            'apiKey': NEWSAPI_KEY
        }
        
        # 只获取最近 24 小时新闻
        from_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        params['from'] = from_date
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') != 'ok':
            print(f"[!] NewsAPI 错误：{data.get('message', 'Unknown error')}")
            return []
        
        articles = []
        for article in data.get('articles', []):
            articles.append({
                'source': article.get('source', {}).get('name', ''),
                'author': article.get('author', ''),
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'url': article.get('url', ''),
                'published_at': article.get('publishedAt', ''),
                'content': article.get('content', '')[:500] if article.get('content') else ''
            })
        
        return articles
    except Exception as e:
        print(f"[!] 获取新闻错误：{e}")
        return _get_mock_news()


def get_stock_news(symbol: str, page_size: int = 10) -> List[Dict]:
    """
    获取特定股票相关新闻
    
    Args:
        symbol: 股票代码 (如 'AAPL')
        page_size: 返回数量
    
    Returns:
        新闻列表
    """
    # 获取相关搜索词
    queries = STOCK_NEWS_QUERIES.get(symbol, [symbol])
    
    return get_finance_news(queries, language='en', page_size=page_size)


def analyze_sentiment(text: str) -> Dict:
    """
    分析文本情绪（简化版）
    
    使用关键词匹配 + 规则判断
    
    Args:
        text: 待分析文本
    
    Returns:
        情绪分析结果
    """
    if not text:
        return {'sentiment': 'neutral', 'score': 0, 'confidence': 0.5}
    
    text_lower = text.lower()
    
    # 正面关键词
    positive_words = [
        'rise', 'increase', 'grow', 'growth', 'gain', 'profit', 'beat', 'outperform',
        'strong', 'positive', 'optimistic', 'bullish', 'record', 'high', 'success',
        '上涨', '增长', '盈利', '突破', '利好', '强势', '创新高', '成功'
    ]
    
    # 负面关键词
    negative_words = [
        'fall', 'drop', 'decline', 'decrease', 'loss', 'miss', 'underperform',
        'weak', 'negative', 'pessimistic', 'bearish', 'low', 'fail', 'crash',
        '下跌', '下滑', '亏损', '跌破', '利空', '弱势', '崩盘', '失败'
    ]
    
    # 计算情绪得分
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    total = positive_count + negative_count
    
    if total == 0:
        return {'sentiment': 'neutral', 'score': 0, 'confidence': 0.3}
    
    # 情绪分数 (-1 到 +1)
    score = (positive_count - negative_count) / total
    
    # 判断情绪类别
    if score > 0.2:
        sentiment = 'positive'
        confidence = min(0.9, 0.5 + abs(score) * 0.4)
    elif score < -0.2:
        sentiment = 'negative'
        confidence = min(0.9, 0.5 + abs(score) * 0.4)
    else:
        sentiment = 'neutral'
        confidence = 0.5 + (1 - abs(score)) * 0.3
    
    return {
        'sentiment': sentiment,
        'score': round(score, 3),
        'confidence': round(confidence, 2),
        'positive_count': positive_count,
        'negative_count': negative_count
    }


def analyze_news_sentiment(articles: List[Dict], include_article_scores: bool = False) -> Dict:
    """
    分析一批新闻的整体情绪
    
    Args:
        articles: 新闻列表
        include_article_scores: 是否返回每篇文章的情绪分数
    
    Returns:
        整体情绪分析（可选包含每篇文章分数）
    """
    if not articles:
        return {'sentiment': 'neutral', 'score': 0, 'article_count': 0}
    
    article_scores = []  # ✅ 保存每篇文章的分数，避免重复计算
    sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
    
    for i, article in enumerate(articles):
        # 分析标题
        title_sentiment = analyze_sentiment(article.get('title', ''))
        # 分析摘要
        desc_sentiment = analyze_sentiment(article.get('description', ''))
        
        # 加权平均（标题权重更高）
        combined_score = title_sentiment['score'] * 0.6 + desc_sentiment['score'] * 0.4
        
        # ✅ 保存文章索引和分数，供后续复用
        article_scores.append({
            'index': i,
            'title': article.get('title', ''),
            'url': article.get('url', ''),
            'score': combined_score
        })
        
        # 统计情绪类别
        if combined_score > 0.2:
            sentiments['positive'] += 1
        elif combined_score < -0.2:
            sentiments['negative'] += 1
        else:
            sentiments['neutral'] += 1
    
    # 计算平均情绪分数
    scores = [a['score'] for a in article_scores]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # 判断整体情绪
    if avg_score > 0.15:
        overall_sentiment = 'positive'
    elif avg_score < -0.15:
        overall_sentiment = 'negative'
    else:
        overall_sentiment = 'neutral'
    
    result = {
        'overall_sentiment': overall_sentiment,
        'overall_score': round(avg_score, 3),
        'article_count': len(articles),
        'sentiment_distribution': sentiments,
        'positive_ratio': round(sentiments['positive'] / len(articles), 2) if articles else 0,
        'negative_ratio': round(sentiments['negative'] / len(articles), 2) if articles else 0,
    }
    
    # ✅ 返回每篇文章的分数，供后续复用
    if include_article_scores:
        result['article_scores'] = article_scores
    
    return result


def get_market_sentiment_report() -> Dict:
    """
    获取市场情绪报告
    
    Returns:
        完整的情绪报告
    """
    # 获取财经新闻
    articles = get_finance_news(language='en', page_size=50)
    
    # ✅ 分析情绪 - 一次调用返回所有分数，避免重复分析
    sentiment_analysis = analyze_news_sentiment(articles, include_article_scores=True)
    
    # 生成报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'news_source': 'NewsAPI',
        'articles_analyzed': len(articles),
        'sentiment': sentiment_analysis,
        'top_positive': [],
        'top_negative': [],
        'key_topics': []
    }
    
    # ✅ 复用已计算的文章分数，不再重复调用 analyze_sentiment
    article_scores = sentiment_analysis.get('article_scores', [])
    if article_scores:
        # 按分数排序
        article_scores.sort(key=lambda x: x['score'], reverse=True)
        
        report['top_positive'] = [
            {'title': a['title'], 'url': a['url'], 'score': a['score']}
            for a in article_scores[:3] if a['score'] > 0.3
        ]
        
        report['top_negative'] = [
            {'title': a['title'], 'url': a['url'], 'score': a['score']}
            for a in article_scores[-3:] if a['score'] < -0.3
        ]
    
    return report


def _get_mock_news() -> List[Dict]:
    """模拟新闻数据（用于测试）"""
    return [
        {
            'source': 'Mock Finance',
            'author': 'AI',
            'title': 'Stock Market Reaches New High Amid Strong Earnings',
            'description': 'Major indices climb as tech companies report better-than-expected quarterly results.',
            'url': 'https://example.com/news1',
            'published_at': datetime.now().isoformat(),
            'content': 'The stock market continued its upward trend...'
        },
        {
            'source': 'Mock Finance',
            'author': 'AI',
            'title': 'Fed Signals Potential Rate Cut in Next Meeting',
            'description': 'Federal Reserve hints at monetary policy shift to support economic growth.',
            'url': 'https://example.com/news2',
            'published_at': datetime.now().isoformat(),
            'content': 'Federal Reserve officials indicated...'
        },
        {
            'source': 'Mock Finance',
            'author': 'AI',
            'title': 'Tech Sector Faces Headwinds from Regulatory Concerns',
            'description': 'New antitrust proposals could impact major technology companies.',
            'url': 'https://example.com/news3',
            'published_at': datetime.now().isoformat(),
            'content': 'Regulators are considering new measures...'
        }
    ]


def calculate_news_impact_score(sentiment_report: Dict) -> float:
    """
    计算新闻对市场的潜在影响分数
    
    Args:
        sentiment_report: 情绪报告
    
    Returns:
        影响分数 (-1 到 +1)
    """
    sentiment = sentiment_report.get('sentiment', {})
    overall_score = sentiment.get('overall_score', 0)
    positive_ratio = sentiment.get('positive_ratio', 0)
    article_count = sentiment_report.get('articles_analyzed', 0)
    
    # 基础分数
    base_score = overall_score
    
    # 正面新闻比例加成
    ratio_bonus = (positive_ratio - 0.5) * 0.3
    
    # 新闻数量可信度（新闻越多越可信）
    confidence = min(1.0, article_count / 50)
    
    # 最终分数
    final_score = (base_score + ratio_bonus) * confidence
    
    return round(final_score, 3)


# 测试
if __name__ == "__main__":
    print("="*60)
    print("DSS 新闻情绪分析模块测试")
    print("="*60)
    
    # 测试获取新闻
    print("\n📰 获取财经新闻:")
    articles = get_finance_news(language='en', page_size=5)
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title']}")
        print(f"   来源：{article['source']}")
        print(f"   时间：{article['published_at'][:16]}")
    
    # 测试单文本情绪分析
    print("\n\n📊 单文本情绪分析测试:")
    test_texts = [
        "Stock market surges to record high on strong earnings",
        "Tech stocks crash amid regulatory concerns",
        "Market remains stable as investors wait for Fed decision"
    ]
    
    for text in test_texts:
        result = analyze_sentiment(text)
        print(f"\n   文本：{text[:50]}...")
        print(f"   情绪：{result['sentiment']} (分数：{result['score']:+.3f})")
    
    # 测试完整报告
    print("\n\n📈 市场情绪报告:")
    report = get_market_sentiment_report()
    print(f"   分析文章数：{report['articles_analyzed']}")
    print(f"   整体情绪：{report['sentiment']['overall_sentiment']}")
    print(f"   情绪分数：{report['sentiment']['overall_score']:+.3f}")
    print(f"   正面比例：{report['sentiment']['positive_ratio']*100:.0f}%")
    
    # 影响分数
    impact_score = calculate_news_impact_score(report)
    print(f"\n   🎯 新闻影响分数：{impact_score:+.3f}")
    
    print("\n" + "="*60)
