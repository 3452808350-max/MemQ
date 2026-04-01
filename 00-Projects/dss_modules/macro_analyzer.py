"""
DSS Macro Event Analyzer - 宏观事件分析模块 v0.1

功能：
1. 新闻情绪分析 - 使用 DashScope LLM 分析财经新闻
2. 宏观指标监控 - 油价、VIX、美元指数、国债收益率等
3. 行业冲击评估 - 自动判断事件对哪些行业受益/受损

独立模块，可单独测试，成熟后集成到 DSS 主系统
"""
import os
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dashscope import Generation

# ============ 配置 (环境变量) ============
# ⚠️ 安全提示：API Key 应通过环境变量配置
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
if DASHSCOPE_API_KEY:
    os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY
else:
    print("⚠️  警告：缺少 DASHSCOPE_API_KEY，情绪分析功能不可用")

# 宏观指标 API
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "")

# 缓存目录
MACRO_CACHE_DIR = "/home/kyj/.openclaw/workspace/data_cache/macro"
os.makedirs(MACRO_CACHE_DIR, exist_ok=True)

# 行业分类（用于事件冲击评估）
INDUSTRY_MAP = {
    'airline': ['中国国航', '南方航空', '东方航空', 'sh.601111', 'sh.600029', 'sh.600115'],
    'energy': ['中国石油', '中国石化', '中海油', 'sh.601857', 'sh.600028', 'sz.00883'],
    'bank': ['工商银行', '建设银行', '招商银行', 'sh.601398', 'sh.601939', 'sh.600036'],
    'tech': ['腾讯', '阿里巴巴', '美团', 'hk.00700', 'hk.09988', 'hk.03690'],
    'consumer': ['贵州茅台', '五粮液', '海天味业', 'sh.600519', 'sz.000858', 'sh.603288'],
}

# ============ 宏观指标获取 ============

def get_macro_indicators() -> Dict:
    """
    获取关键宏观指标
    
    Returns:
        dict: 包含油价、VIX、美元指数、国债收益率等
    """
    indicators = {}
    
    # 1. 原油价格 (WTI) - 通过 Alpha Vantage
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=USO&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if 'Global Quote' in data:
            indicators['oil_price'] = float(data['Global Quote'].get('05. price', 0))
    except:
        indicators['oil_price'] = None
    
    # 2. VIX 恐慌指数 - 通过 Alpha Vantage
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=VIX&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if 'Global Quote' in data:
            indicators['vix'] = float(data['Global Quote'].get('05. price', 0))
    except:
        indicators['vix'] = None
    
    # 3. 美元指数 (DXY) - 通过 Alpha Vantage
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=UUP&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if 'Global Quote' in data:
            indicators['dxy'] = float(data['Global Quote'].get('05. price', 0))
    except:
        indicators['dxy'] = None
    
    # 4. 美国 10 年期国债收益率 - 通过 FRED
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={FRED_API_KEY}&file_type=json"
        r = requests.get(url, timeout=10)
        data = r.json()
        if 'observations' in data and len(data['observations']) > 0:
            indicators['treasury_10y'] = float(data['observations'][-1].get('value', 0))
    except:
        indicators['treasury_10y'] = None
    
    # 5. 黄金价格 - 通过 Alpha Vantage
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=GLD&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if 'Global Quote' in data:
            indicators['gold'] = float(data['Global Quote'].get('05. price', 0))
    except:
        indicators['gold'] = None
    
    # 添加时间戳
    indicators['timestamp'] = datetime.now().isoformat()
    
    return indicators


def get_macro_change(macro_current: Dict, macro_history: Dict, days: int = 7) -> Dict:
    """
    计算宏观指标变化率
    
    Args:
        macro_current: 当前宏观指标
        macro_history: 历史宏观指标 (N 天前)
        days: 时间间隔
    
    Returns:
        dict: 各指标变化率
    """
    changes = {}
    for key in ['oil_price', 'vix', 'dxy', 'treasury_10y', 'gold']:
        curr = macro_current.get(key)
        hist = macro_history.get(key)
        if curr and hist and hist > 0:
            changes[f'{key}_change_{days}d'] = (curr - hist) / hist * 100
        else:
            changes[f'{key}_change_{days}d'] = None
    
    return changes


# ============ 新闻情绪分析 ============

NEWS_SOURCES = [
    "https://rsshub.app/passiontimes/category/%E8%B2%A1%E7%B6%93",  # 财经新闻 RSS
    "https://rsshub.app/wallstreetcn/global",  # 华尔街见闻
]

def fetch_finance_news(keywords: List[str] = None, limit: int = 10) -> List[Dict]:
    """
    获取财经新闻
    
    Args:
        keywords: 关键词列表，如 ["伊朗", "石油", "战争"]
        limit: 返回新闻数量
    
    Returns:
        list: 新闻列表 [{title, summary, source, published_at}]
    """
    # 简化版本：使用示例新闻（实际使用时可接入新闻 API）
    # 这里用 RSSHub 或新闻 API
    
    news_list = []
    
    # 示例：可以接入新浪财经、东方财富等 API
    # 暂时返回空列表，实际使用时填充
    
    return news_list


def analyze_news_sentiment(news_text: str, focus: str = "market") -> Dict:
    """
    使用 LLM 分析新闻情绪
    
    Args:
        news_text: 新闻文本
        focus: 分析焦点 ("market", "energy", "tech", etc.)
    
    Returns:
        dict: {sentiment_score, sentiment_label, key_events, affected_industries}
    """
    prompt = f"""
你是一名专业的金融分析师。请分析以下新闻内容，评估对金融市场的影响。

**分析要求：**
1. 情绪评分：-100 (极度负面) 到 +100 (极度正面)
2. 情绪标签：positive / negative / neutral
3. 关键事件：提取影响市场的关键事件
4. 受影响行业：列出受益和受损的行业

**新闻内容：**
{news_text[:3000]}

**输出格式（JSON）：**
{{
    "sentiment_score": 数字 (-100 到 +100),
    "sentiment_label": "positive/negative/neutral",
    "key_events": ["事件 1", "事件 2"],
    "benefit_industries": ["受益行业 1", "受益行业 2"],
    "hurt_industries": ["受损行业 1", "受损行业 2"],
    "confidence": 数字 (0-1，表示分析置信度)
}}

只返回 JSON，不要其他内容。
"""
    
    try:
        response = Generation.call(
            model="qwen-max",
            messages=[{"role": "user", "content": prompt}],
            result_format='message'
        )
        
        if response.status_code == 200:
            content = response.output.choices[0].message.content
            # 解析 JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
    except Exception as e:
        print(f"[!] 新闻情绪分析失败：{e}")
    
    # 默认返回
    return {
        "sentiment_score": 0,
        "sentiment_label": "neutral",
        "key_events": [],
        "benefit_industries": [],
        "hurt_industries": [],
        "confidence": 0.5
    }


# ============ 行业冲击评估 ============

def assess_industry_impact(
    macro_changes: Dict,
    news_analysis: Dict,
    stock_symbol: str,
    stock_industry: str
) -> float:
    """
    评估宏观事件对特定股票/行业的影响
    
    Args:
        macro_changes: 宏观指标变化
        news_analysis: 新闻分析结果
        stock_symbol: 股票代码
        stock_industry: 所属行业
    
    Returns:
        float: 调整系数 (-1.0 到 +1.0)，负值表示负面影响，正值表示正面影响
    """
    impact_score = 0.0
    
    # 1. 油价变化影响
    oil_change = macro_changes.get('oil_price_change_7d', 0) or 0
    if oil_change > 10:  # 油价大涨
        if stock_industry in ['airline', '物流']:
            impact_score -= 0.3  # 航空业受损
        elif stock_industry in ['energy', '石油']:
            impact_score += 0.3  # 能源业受益
    
    # 2. VIX 变化影响（市场恐慌）
    vix_change = macro_changes.get('vix_change_7d', 0) or 0
    if vix_change > 20:  # 恐慌指数大涨
        impact_score -= 0.2  # 整体市场风险偏好下降
    
    # 3. 新闻情绪影响
    news_score = news_analysis.get('sentiment_score', 0)
    news_confidence = news_analysis.get('confidence', 0.5)
    
    # 检查是否在受损行业列表中
    hurt_industries = news_analysis.get('hurt_industries', [])
    benefit_industries = news_analysis.get('benefit_industries', [])
    
    if stock_industry in hurt_industries:
        impact_score -= 0.3 * news_confidence
    elif stock_industry in benefit_industries:
        impact_score += 0.3 * news_confidence
    
    # 4. 黄金/避险情绪
    gold_change = macro_changes.get('gold_change_7d', 0) or 0
    if gold_change > 5:  # 金价大涨，避险情绪
        if stock_industry in ['consumer', '必需品']:
            impact_score += 0.1  # 防御性板块受益
    
    # 限制范围
    impact_score = max(-1.0, min(1.0, impact_score))
    
    return impact_score


# ============ 综合宏观风险指数 ============

def calculate_macro_risk_index(macro_current: Dict, macro_history: Dict = None) -> Dict:
    """
    计算综合宏观风险指数
    
    Args:
        macro_current: 当前宏观指标
        macro_history: 历史宏观指标 (用于计算变化)
    
    Returns:
        dict: {risk_index, risk_level, factors}
    """
    factors = {}
    risk_score = 50  # 基准 50，>50 风险高，<50 风险低
    
    # VIX 因子
    vix = macro_current.get('vix')
    if vix:
        if vix > 30:
            risk_score += 20
            factors['vix'] = "高恐慌"
        elif vix > 20:
            risk_score += 10
            factors['vix'] = "中等恐慌"
        else:
            factors['vix'] = "低恐慌"
    
    # 油价因子
    oil = macro_current.get('oil_price')
    if oil:
        if oil > 100:
            risk_score += 10
            factors['oil'] = "高油价"
        else:
            factors['oil'] = "正常"
    
    # 国债收益率倒挂（经济衰退信号）
    treasury_10y = macro_current.get('treasury_10y')
    if treasury_10y:
        if treasury_10y < 3.5:
            risk_score -= 5
            factors['treasury'] = "宽松"
        elif treasury_10y > 5:
            risk_score += 10
            factors['treasury'] = "紧缩"
        else:
            factors['treasury'] = "正常"
    
    # 黄金（避险情绪）
    gold = macro_current.get('gold')
    if gold:
        if gold > 2000:
            risk_score += 5
            factors['gold'] = "避险情绪高"
        else:
            factors['gold'] = "正常"
    
    # 确定风险等级
    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 60:
        risk_level = "ELEVATED"
    elif risk_score >= 40:
        risk_level = "NORMAL"
    else:
        risk_level = "LOW"
    
    return {
        "risk_index": risk_score,
        "risk_level": risk_level,
        "factors": factors,
        "timestamp": datetime.now().isoformat()
    }


# ============ 主分析函数 ============

def run_macro_analysis(stock_list: List[Tuple[str, str]] = None) -> Dict:
    """
    运行完整的宏观事件分析
    
    Args:
        stock_list: 股票列表 [(symbol, industry), ...]
    
    Returns:
        dict: 分析结果
    """
    if stock_list is None:
        # 默认股票池
        stock_list = [
            ('sh.600519', 'consumer'),
            ('sh.601111', 'airline'),
            ('sh.601857', 'energy'),
            ('sh.601318', 'bank'),
        ]
    
    # 1. 获取宏观指标
    macro_current = get_macro_indicators()
    
    # 2. 加载历史宏观数据（如果有）
    history_file = os.path.join(MACRO_CACHE_DIR, "macro_history.json")
    macro_history = None
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            macro_history = json.load(f)
    
    # 3. 计算宏观变化
    macro_changes = get_macro_change(macro_current, macro_history, days=7) if macro_history else {}
    
    # 4. 计算宏观风险指数
    risk_index = calculate_macro_risk_index(macro_current, macro_history)
    
    # 5. 获取新闻（简化版，暂不实现）
    # news_list = fetch_finance_news(keywords=["石油", "伊朗", "战争"])
    # news_analysis = analyze_news_sentiment(news_text) if news_list else {}
    news_analysis = {"sentiment_score": 0, "hurt_industries": [], "benefit_industries": []}
    
    # 6. 评估各股票影响
    stock_impacts = []
    for symbol, industry in stock_list:
        impact = assess_industry_impact(macro_changes, news_analysis, symbol, industry)
        stock_impacts.append({
            "symbol": symbol,
            "industry": industry,
            "macro_adjustment": impact
        })
    
    # 7. 保存当前宏观数据（用于下次计算变化）
    with open(history_file, 'w') as f:
        json.dump(macro_current, f, indent=2)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "macro_indicators": macro_current,
        "macro_changes_7d": macro_changes,
        "risk_index": risk_index,
        "news_sentiment": news_analysis,
        "stock_impacts": stock_impacts
    }


# ============ CLI 测试入口 ============

if __name__ == "__main__":
    print("="*60)
    print("DSS Macro Event Analyzer - 独立测试")
    print("="*60)
    
    result = run_macro_analysis()
    
    print(f"\n📊 宏观风险指数：{result['risk_index']['risk_index']} ({result['risk_index']['risk_level']})")
    print(f"\n📈 宏观指标:")
    for k, v in result['macro_indicators'].items():
        if k != 'timestamp':
            print(f"  {k}: {v}")
    
    print(f"\n📉 7 天变化:")
    for k, v in result['macro_changes_7d'].items():
        if v is not None:
            print(f"  {k}: {v:+.2f}%")
    
    print(f"\n🎯 个股影响调整:")
    for stock in result['stock_impacts']:
        adj = stock['macro_adjustment']
        if adj != 0:
            print(f"  {stock['symbol']} ({stock['industry']}): {adj:+.2f}")
    
    print("\n✅ 分析完成")
