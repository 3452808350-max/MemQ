"""
新闻情绪分析模块 (News Sentiment Analysis Module)
用于DSS选股系统的情绪评分组件

功能：
- 关键词情绪分析（正面/负面词汇表）
- 新闻重要性评分
- 情绪综合评分
- 股票特定情绪分析

输出格式：
- sentiment: -1 到 +1
- confidence: 0 到 1
- key_topics: 关键话题列表
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from collections import Counter
from dataclasses import dataclass, field, asdict

# =============================================================================
# 情绪词汇库 (Sentiment Vocabulary)
# =============================================================================

# 正面词汇 - 中文
POSITIVE_WORDS_CN = {
    # 涨幅相关
    '上涨': 1.0, '大涨': 1.5, '暴涨': 2.0, '飙升': 1.8, '创新高': 1.5,
    '突破': 1.2, '反弹': 0.8, '回升': 0.9, '走高': 1.0, '拉升': 1.2,
    '涨停': 1.8, '连涨': 1.3, '大涨': 1.5, '翻红': 0.8,
    # 盈利相关
    '盈利': 1.2, '利润': 0.8, '盈利增长': 1.5, '净利润': 0.9,
    '超预期': 1.5, '业绩优异': 1.5, '业绩增长': 1.3, '营收增长': 1.2,
    '扭亏为盈': 1.8, '同比大增': 1.5, '环比增长': 1.0,
    # 利好消息
    '利好': 1.5, '重大利好': 2.0, '特大利好': 2.2, '利好政策': 1.5,
    '政策支持': 1.3, '政策利好': 1.5, '减税': 1.2, '降息': 1.3,
    '降准': 1.2, '宽松': 1.0, '刺激': 1.0, '扶持': 1.0,
    # 市场信心
    '看好': 1.2, '增持': 1.3, '买入': 1.0, '推荐': 0.9,
    '牛市': 1.5, '强势': 1.2, '乐观': 1.0, '信心': 0.8,
    '机构青睐': 1.5, '资金流入': 1.3, '主力抢筹': 1.8, '外资买入': 1.3,
    # 企业发展
    '并购': 1.2, '重组': 1.0, '合作': 0.8, '签约': 0.7,
    '中标': 1.3, '订单': 0.8, '扩产': 1.0, '新项目': 0.9,
    '技术突破': 1.5, '产品发布': 1.0, '市场份额': 0.8,
    # 分红回报
    '分红': 1.2, '高送转': 1.5, '回购': 1.3, '注销': 1.0,
}

# 正面词汇 - 英文
POSITIVE_WORDS_EN = {
    # Price movements
    'rise': 1.0, 'rising': 1.0, 'surge': 1.5, 'surging': 1.5,
    'soar': 1.8, 'soaring': 1.8, 'rally': 1.3, 'rallying': 1.3,
    'jump': 1.2, 'jumping': 1.2, 'climb': 1.0, 'climbing': 1.0,
    'gain': 1.0, 'gaining': 1.0, 'advance': 0.8, 'advancing': 0.8,
    'breakthrough': 1.5, 'record high': 1.5, 'all-time high': 1.8,
    'outperform': 1.5, 'beat': 1.2, 'beating': 1.2,
    
    # Earnings
    'profit': 1.0, 'profitable': 1.2, 'earnings': 0.5,
    'beat expectations': 1.5, 'beat estimates': 1.5,
    'strong earnings': 1.5, 'record profit': 1.8,
    'revenue growth': 1.3, 'growth': 1.0, 'growing': 1.0,
    
    # Positive news
    'bullish': 1.5, 'optimistic': 1.2, 'upgrade': 1.3,
    'buy': 1.0, 'buying': 1.0, 'buyback': 1.3, 'dividend': 1.2,
    'merger': 1.0, 'acquisition': 1.0, 'deal': 0.8,
    'launch': 0.8, 'expand': 1.0, 'expansion': 1.0,
    'innovation': 1.0, 'breakthrough': 1.5,
    
    # Market sentiment
    'confidence': 0.8, 'positive': 1.0, 'strong': 1.0,
    'support': 0.8, 'stimulus': 1.2, 'recovery': 1.0,
    'inflow': 1.2, 'accumulation': 1.3,
}

# 负面词汇 - 中文
NEGATIVE_WORDS_CN = {
    # 跌幅相关
    '下跌': 1.0, '大跌': 1.5, '暴跌': 2.0, '崩盘': 2.5, '跳水': 1.8,
    '跌破': 1.3, '下挫': 1.2, '走低': 0.9, '下行': 0.8,
    '跌停': 1.8, '连跌': 1.3, '重挫': 1.7, '翻绿': 0.8,
    # 亏损相关
    '亏损': 1.5, '巨亏': 2.0, '亏损扩大': 1.8, '净利润下滑': 1.5,
    '不及预期': 1.5, '业绩下滑': 1.3, '营收下降': 1.2,
    '同比大降': 1.6, '环比下滑': 1.2, '减收': 1.0,
    # 利空消息
    '利空': 1.5, '重大利空': 2.0, '特大利空': 2.2,
    '政策收紧': 1.3, '加息': 1.2, '收紧': 1.0,
    '监管': 0.8, '处罚': 1.5, '罚款': 1.2, '立案': 1.8,
    # 市场风险
    '看空': 1.5, '减持': 1.3, '卖出': 1.0, '抛售': 1.5,
    '熊市': 1.5, '弱势': 1.0, '悲观': 1.0, '恐慌': 1.5,
    '资金流出': 1.3, '主力出逃': 1.8, '外资撤离': 1.5,
    # 企业危机
    '破产': 2.5, '倒闭': 2.5, '违约': 2.0, '债务危机': 2.2,
    '诉讼': 1.5, '纠纷': 1.0, '问题': 0.8, '风险': 0.7,
    '裁员': 1.5, '关停': 1.8, '停产': 1.5, '召回': 1.2,
    # 其他负面
    '内幕': 1.8, '造假': 2.2, '违规': 1.8, '失信': 1.5,
}

# 负面词汇 - 英文
NEGATIVE_WORDS_EN = {
    # Price movements
    'fall': 1.0, 'falling': 1.0, 'drop': 1.2, 'dropping': 1.2,
    'plunge': 2.0, 'plunging': 2.0, 'crash': 2.5, 'crashing': 2.5,
    'tumble': 1.5, 'tumbling': 1.5, 'slide': 1.0, 'sliding': 1.0,
    'decline': 1.0, 'declining': 1.0, 'sink': 1.3, 'sinking': 1.3,
    'slump': 1.5, 'slumping': 1.5, 'selloff': 1.8,
    
    # Losses
    'loss': 1.2, 'losses': 1.2, 'unprofitable': 1.5,
    'miss expectations': 1.5, 'miss estimates': 1.5,
    'miss': 1.0, 'underperform': 1.3, 'weak earnings': 1.5,
    'revenue decline': 1.5, 'shrink': 1.2, 'shrinking': 1.2,
    
    # Negative news
    'bearish': 1.5, 'pessimistic': 1.2, 'downgrade': 1.3,
    'sell': 1.0, 'selling': 1.0, 'lawsuit': 1.5, 'fraud': 2.2,
    'investigation': 1.5, 'probe': 1.3, 'scandal': 2.0,
    'bankruptcy': 2.5, 'default': 2.0, 'debt crisis': 2.2,
    'layoff': 1.5, 'layoffs': 1.5, 'cut': 1.0, 'cuts': 1.0,
    
    # Market sentiment
    'fear': 1.2, 'panic': 1.5, 'uncertainty': 1.0,
    'risk': 0.8, 'concern': 0.8, 'warning': 1.0,
    'outflow': 1.2, 'distribution': 1.0,
}

# 中性词汇（用于判断新闻是否具有明确情绪倾向）
NEUTRAL_WORDS = {
    '发布', '公布', '披露', '公告', '通知',
    'announced', 'reported', 'stated', 'released', 'said',
    '计划', '预计', '预测', 'forecast', 'expected', 'planned',
}

# 重要性词汇（影响新闻权重）
IMPORTANCE_WORDS = {
    # 高重要性
    '重大': 2.0, '重要': 1.5, '关键': 1.5, '核心': 1.3,
    'major': 2.0, 'important': 1.5, 'key': 1.5, 'critical': 1.8,
    '首次': 1.5, '历史': 1.3, '突破': 1.5, '里程碑': 2.0,
    'first': 1.5, 'historic': 1.5, 'milestone': 2.0, 'breakthrough': 1.5,
    # 中等重要性
    '较大': 1.2, '显著': 1.3, '明显': 1.2,
    'significant': 1.3, 'notable': 1.2, 'substantial': 1.3,
}

# 行业关键词（用于话题提取）
INDUSTRY_KEYWORDS = {
    '科技': ['科技', '芯片', '半导体', 'AI', '人工智能', '软件', '互联网', '云计算', '大数据'],
    '金融': ['银行', '保险', '证券', '金融', '基金', '投资'],
    '能源': ['石油', '煤炭', '新能源', '光伏', '风电', '锂电池'],
    '医药': ['医药', '生物', '疫苗', '医疗', '创新药'],
    '消费': ['消费', '零售', '电商', '食品', '饮料', '白酒'],
    '房地产': ['房地产', '地产', '住房', '楼盘'],
    '汽车': ['汽车', '新能源车', '电动车', '智能汽车'],
    '军工': ['军工', '国防', '武器', '航天'],
}

# 合并词汇表
POSITIVE_WORDS = {**POSITIVE_WORDS_CN, **POSITIVE_WORDS_EN}
NEGATIVE_WORDS = {**NEGATIVE_WORDS_CN, **NEGATIVE_WORDS_EN}


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class SentimentResult:
    """情绪分析结果"""
    sentiment: float = 0.0  # -1 到 +1
    confidence: float = 0.5  # 0 到 1
    key_topics: List[str] = field(default_factory=list)
    positive_count: int = 0
    negative_count: int = 0
    importance_score: float = 0.5
    details: Dict = field(default_factory=dict)


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    content: str = ""
    source: str = ""
    published_at: str = ""
    url: str = ""
    importance: float = 0.5  # 0-1


# =============================================================================
# 核心功能函数
# =============================================================================

def extract_keywords(text: str) -> List[str]:
    """
    提取文本中的关键词
    
    Args:
        text: 待分析文本
    
    Returns:
        关键词列表
    """
    if not text:
        return []
    
    text_lower = text.lower()
    keywords = []
    
    # 检查情绪词汇
    for word, weight in POSITIVE_WORDS.items():
        if word.lower() in text_lower:
            keywords.append(word)
    
    for word, weight in NEGATIVE_WORDS.items():
        if word.lower() in text_lower:
            keywords.append(word)
    
    # 检查行业关键词
    for industry, words in INDUSTRY_KEYWORDS.items():
        for word in words:
            if word.lower() in text_lower:
                keywords.append(f"[{industry}]")
                break
    
    return list(set(keywords))


def calculate_importance_score(title: str, content: str = "") -> float:
    """
    计算新闻重要性分数
    
    Args:
        title: 新闻标题
        content: 新闻内容
    
    Returns:
        重要性分数 (0-1)
    """
    text = f"{title} {content}".lower()
    
    # 基础分数
    score = 0.5
    
    # 检查重要性词汇
    for word, weight in IMPORTANCE_WORDS.items():
        if word.lower() in text:
            score += (weight - 1.0) * 0.2  # 将权重映射到增量
    
    # 标题长度因子（标题太短可能不够重要）
    title_len = len(title)
    if title_len < 20:
        score *= 0.9
    elif title_len > 50:
        score *= 1.05
    
    # 包含具体数字的标题通常更重要
    if re.search(r'\d+', title):
        score *= 1.1
    
    # 包含股票代码
    if re.search(r'[A-Z]{1,5}\s*[\(（]', title):
        score *= 1.15
    
    return min(1.0, max(0.1, score))


def _is_chinese_char(char: str) -> bool:
    """判断是否为中文字符"""
    return '\u4e00' <= char <= '\u9fff'


def _is_chinese_word(word: str) -> bool:
    """判断是否为中文词汇"""
    return any(_is_chinese_char(c) for c in word)


def analyze_single_text(text: str) -> Tuple[float, int, int, List[str]]:
    """
    分析单个文本的情绪
    
    Args:
        text: 待分析文本
    
    Returns:
        (情绪分数, 正面计数, 负面计数, 匹配的关键词列表)
    """
    if not text:
        return 0.0, 0, 0, []
    
    text_lower = text.lower()
    
    positive_score = 0.0
    negative_score = 0.0
    positive_count = 0
    negative_count = 0
    matched_keywords = []
    
    # 计算正面得分
    for word, weight in POSITIVE_WORDS.items():
        # 中文词汇直接子串匹配，英文词汇使用词边界匹配
        if _is_chinese_word(word):
            # 中文词汇：直接子串匹配
            matches = text_lower.count(word.lower())
        else:
            # 英文词汇：使用词边界匹配
            pattern = r'\b' + re.escape(word.lower()) + r'\b'
            matches = len(re.findall(pattern, text_lower))
        
        if matches > 0:
            positive_score += weight * matches
            positive_count += matches
            matched_keywords.append(f"+{word}")
    
    # 计算负面得分
    for word, weight in NEGATIVE_WORDS.items():
        if _is_chinese_word(word):
            matches = text_lower.count(word.lower())
        else:
            pattern = r'\b' + re.escape(word.lower()) + r'\b'
            matches = len(re.findall(pattern, text_lower))
        
        if matches > 0:
            negative_score += weight * matches
            negative_count += matches
            matched_keywords.append(f"-{word}")
    
    # 计算情绪分数 (-1 到 +1)
    total_score = positive_score + negative_score
    if total_score == 0:
        return 0.0, 0, 0, []
    
    # 情绪分数：正面得分 / 总得分，映射到 -1 到 +1
    sentiment = (positive_score - negative_score) / (positive_score + negative_score)
    
    # 应用 tanh 函数进行归一化，避免极端值
    import math
    sentiment = math.tanh(sentiment * 1.5)
    
    return sentiment, positive_count, negative_count, matched_keywords


def analyze_news_sentiment(news_list: List[Dict], 
                           time_decay: bool = True,
                           importance_weight: bool = True) -> SentimentResult:
    """
    分析新闻列表的整体情绪
    
    Args:
        news_list: 新闻列表，每个元素包含 title, content, source, published_at 等
        time_decay: 是否应用时间衰减因子
        importance_weight: 是否应用重要性权重
    
    Returns:
        SentimentResult: 情绪分析结果
    """
    if not news_list:
        return SentimentResult(
            sentiment=0.0,
            confidence=0.3,
            key_topics=[],
            details={'message': 'No news to analyze'}
        )
    
    now = datetime.now()
    
    # 收集分析结果
    sentiments = []
    weights = []
    all_keywords = []
    importance_scores = []
    details = {
        'articles': [],
        'time_range': None,
    }
    
    # 时间范围
    timestamps = []
    
    for news in news_list:
        title = news.get('title', '')
        content = news.get('content', '') or news.get('description', '')
        published_at = news.get('published_at', '')
        
        # 合并标题和内容分析
        title_sentiment, title_pos, title_neg, title_kw = analyze_single_text(title)
        content_sentiment, content_pos, content_neg, content_kw = analyze_single_text(content)
        
        # 标题权重更高 (60%)，内容次之 (40%)
        combined_sentiment = title_sentiment * 0.6 + content_sentiment * 0.4
        
        # 计算重要性分数
        importance = calculate_importance_score(title, content)
        importance_scores.append(importance)
        
        # 计算权重
        weight = 1.0
        if importance_weight:
            weight *= importance
        
        # 时间衰减
        if time_decay and published_at:
            try:
                if 'T' in published_at:
                    pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                else:
                    pub_time = datetime.strptime(published_at, '%Y-%m-%d %H:%M:%S')
                
                # 计算时间差（小时）
                hours_ago = (now - pub_time.replace(tzinfo=None)).total_seconds() / 3600
                
                # 衰减函数：24小时内权重1.0，之后逐渐衰减
                if hours_ago > 24:
                    decay = 1.0 / (1.0 + 0.02 * (hours_ago - 24))
                    weight *= decay
                
                timestamps.append(pub_time)
            except:
                pass
        
        sentiments.append(combined_sentiment)
        weights.append(weight)
        all_keywords.extend(title_kw)
        all_keywords.extend(content_kw)
        
        # 保存文章详情
        details['articles'].append({
            'title': title,
            'sentiment': round(combined_sentiment, 3),
            'importance': round(importance, 3),
            'weight': round(weight, 3),
            'keywords': list(set(title_kw + content_kw))[:5]
        })
    
    # 加权平均情绪
    total_weight = sum(weights)
    if total_weight > 0:
        weighted_sentiment = sum(s * w for s, w in zip(sentiments, weights)) / total_weight
    else:
        weighted_sentiment = sum(sentiments) / len(sentiments)
    
    # 计算置信度
    # 基于新闻数量和一致性
    news_count_factor = min(1.0, len(news_list) / 20)  # 20条新闻达到饱和
    
    # 计算情绪一致性（方差越小，置信度越高）
    if len(sentiments) > 1:
        import statistics
        variance = statistics.variance(sentiments)
        consistency_factor = 1.0 / (1.0 + variance * 2)  # 方差越大，置信度越低
    else:
        consistency_factor = 0.5  # 单条新闻置信度中等
    
    confidence = 0.4 + 0.3 * news_count_factor + 0.3 * consistency_factor
    confidence = min(0.95, max(0.3, confidence))
    
    # 提取关键话题
    topic_counter = Counter(all_keywords)
    key_topics = [word for word, _ in topic_counter.most_common(10)]
    
    # 清理话题（移除+/-前缀）
    clean_topics = []
    for topic in key_topics:
        if topic.startswith('+') or topic.startswith('-'):
            clean_topics.append(topic[1:])
        else:
            clean_topics.append(topic)
    clean_topics = list(dict.fromkeys(clean_topics))[:8]  # 去重并限制数量
    
    # 统计正负面计数
    total_positive = sum(a['sentiment'] > 0.1 for a in details['articles'])
    total_negative = sum(a['sentiment'] < -0.1 for a in details['articles'])
    
    # 时间范围
    if timestamps:
        details['time_range'] = {
            'earliest': min(timestamps).isoformat(),
            'latest': max(timestamps).isoformat()
        }
    
    return SentimentResult(
        sentiment=round(weighted_sentiment, 4),
        confidence=round(confidence, 4),
        key_topics=clean_topics,
        positive_count=total_positive,
        negative_count=total_negative,
        importance_score=round(sum(importance_scores) / len(importance_scores), 4),
        details=details
    )


def get_sentiment_score(symbol: str, 
                        news_list: Optional[List[Dict]] = None,
                        days_back: int = 7) -> Dict:
    """
    获取特定股票的情绪分数
    
    Args:
        symbol: 股票代码
        news_list: 新闻列表（可选，如果不提供则使用模拟数据）
        days_back: 回溯天数
    
    Returns:
        包含情绪分数、置信度和关键话题的字典
    """
    from .api_news import get_stock_news, get_finance_news
    
    # 如果没有提供新闻列表，尝试获取
    if news_list is None:
        try:
            news_list = get_stock_news(symbol, page_size=30)
        except Exception as e:
            print(f"[!] 获取 {symbol} 新闻失败: {e}")
            # 尝试获取一般财经新闻
            try:
                news_list = get_finance_news(language='en', page_size=20)
            except:
                news_list = []
    
    if not news_list:
        return {
            'symbol': symbol,
            'sentiment': 0.0,
            'confidence': 0.0,
            'key_topics': [],
            'news_count': 0,
            'message': 'No news available for analysis'
        }
    
    # 过滤相关新闻（包含股票代码或相关关键词）
    symbol_lower = symbol.lower()
    related_news = []
    
    # 股票相关词汇映射
    symbol_keywords = {
        'AAPL': ['apple', 'iphone', 'ipad', 'mac', 'tim cook', 'aapl'],
        'TSLA': ['tesla', 'elon musk', 'ev', 'model', 'tsla', 'spacex'],
        'NVDA': ['nvidia', 'gpu', 'ai chip', 'data center', 'nvda'],
        'MSFT': ['microsoft', 'azure', 'windows', 'office', 'satya nadella', 'msft'],
        'GOOGL': ['google', 'alphabet', 'search', 'youtube', 'googl'],
        'AMZN': ['amazon', 'aws', 'prime', 'bezos', 'amzn'],
        'META': ['meta', 'facebook', 'instagram', 'zuckerberg', 'meta'],
    }
    
    keywords = symbol_keywords.get(symbol.upper(), [symbol_lower])
    keywords = [k.lower() for k in keywords]
    
    for news in news_list:
        title = news.get('title', '').lower()
        content = news.get('content', '') or news.get('description', '')
        content = content.lower()
        
        # 检查是否相关
        is_related = any(kw in title or kw in content for kw in keywords)
        
        if is_related:
            related_news.append(news)
    
    # 如果相关新闻太少，使用所有新闻
    if len(related_news) < 3:
        related_news = news_list
    
    # 分析情绪
    result = analyze_news_sentiment(related_news)
    
    return {
        'symbol': symbol,
        'sentiment': result.sentiment,
        'confidence': result.confidence,
        'key_topics': result.key_topics,
        'positive_count': result.positive_count,
        'negative_count': result.negative_count,
        'importance_score': result.importance_score,
        'news_count': len(related_news),
        'time_range': result.details.get('time_range'),
        'sentiment_label': _sentiment_to_label(result.sentiment),
        'analysis_timestamp': datetime.now().isoformat()
    }


def _sentiment_to_label(sentiment: float) -> str:
    """将情绪分数转换为标签"""
    if sentiment >= 0.5:
        return '非常乐观'
    elif sentiment >= 0.2:
        return '乐观'
    elif sentiment >= 0.1:
        return '偏乐观'
    elif sentiment > -0.1:
        return '中性'
    elif sentiment > -0.2:
        return '偏悲观'
    elif sentiment > -0.5:
        return '悲观'
    else:
        return '非常悲观'


def get_market_sentiment(days_back: int = 3) -> Dict:
    """
    获取整体市场情绪
    
    Args:
        days_back: 回溯天数
    
    Returns:
        市场情绪报告
    """
    from .api_news import get_finance_news
    
    try:
        news_list = get_finance_news(language='en', page_size=50)
    except Exception as e:
        print(f"[!] 获取市场新闻失败: {e}")
        news_list = []
    
    result = analyze_news_sentiment(news_list)
    
    return {
        'market_sentiment': result.sentiment,
        'confidence': result.confidence,
        'key_topics': result.key_topics,
        'positive_count': result.positive_count,
        'negative_count': result.negative_count,
        'importance_score': result.importance_score,
        'news_count': len(news_list) if news_list else 0,
        'sentiment_label': _sentiment_to_label(result.sentiment),
        'analysis_timestamp': datetime.now().isoformat()
    }


# =============================================================================
# 测试代码
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("新闻情绪分析模块测试")
    print("=" * 70)
    
    # 测试数据
    test_news = [
        {
            'title': '科技股大涨，苹果创新高',
            'content': '苹果公司今日股价大涨3%，创历史新高。分析师上调目标价至200美元。',
            'source': 'Mock News',
            'published_at': datetime.now().isoformat()
        },
        {
            'title': '美联储暗示可能降息',
            'content': '美联储主席表示，如果通胀持续下降，今年可能会考虑降息。',
            'source': 'Mock News',
            'published_at': datetime.now().isoformat()
        },
        {
            'title': '某科技公司业绩不及预期，股价暴跌',
            'content': '该公司季度财报显示营收大幅下滑，股价盘后暴跌15%。',
            'source': 'Mock News',
            'published_at': datetime.now().isoformat()
        },
        {
            'title': '市场保持稳定，投资者观望',
            'content': '今日股市平稳，成交量有所下降，投资者等待更多信号。',
            'source': 'Mock News',
            'published_at': datetime.now().isoformat()
        },
    ]
    
    # 测试单文本分析
    print("\n📊 单文本情绪分析测试:")
    print("-" * 50)
    test_texts = [
        "苹果股价大涨，创新高！利润超预期",
        "市场暴跌，投资者恐慌抛售",
        "今日股市平稳运行",
    ]
    for text in test_texts:
        sentiment, pos, neg, kw = analyze_single_text(text)
        print(f"\n文本: {text}")
        print(f"  情绪分数: {sentiment:+.3f}")
        print(f"  正面词: {pos}, 负面词: {neg}")
        print(f"  关键词: {kw}")
    
    # 测试新闻列表分析
    print("\n\n📰 新闻列表情绪分析测试:")
    print("-" * 50)
    result = analyze_news_sentiment(test_news)
    print(f"整体情绪: {result.sentiment:+.3f} ({_sentiment_to_label(result.sentiment)})")
    print(f"置信度: {result.confidence:.2f}")
    print(f"关键话题: {result.key_topics}")
    print(f"正面新闻: {result.positive_count}, 负面新闻: {result.negative_count}")
    print(f"重要性分数: {result.importance_score:.2f}")
    
    # 测试股票情绪
    print("\n\n📈 股票情绪分析测试 (AAPL):")
    print("-" * 50)
    stock_result = get_sentiment_score('AAPL', test_news)
    print(f"股票: {stock_result['symbol']}")
    print(f"情绪: {stock_result['sentiment']:+.3f} ({stock_result['sentiment_label']})")
    print(f"置信度: {stock_result['confidence']:.2f}")
    print(f"关键话题: {stock_result['key_topics']}")
    
    # 测试市场情绪
    print("\n\n🌍 市场情绪测试:")
    print("-" * 50)
    market = get_market_sentiment()
    print(f"市场情绪: {market.get('market_sentiment', 'N/A')}")
    print(f"情绪标签: {market.get('sentiment_label', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)