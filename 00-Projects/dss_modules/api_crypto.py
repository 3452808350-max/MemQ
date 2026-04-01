"""
加密货币数据模块 - CoinGecko API
获取加密货币价格、市值、交易量等数据
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# CoinGecko API 配置
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# 主流加密货币列表
CRYPTO_IDS = [
    'bitcoin', 'ethereum', 'binancecoin', 'ripple', 'cardano',
    'solana', 'polkadot', 'dogecoin', 'avalanche-2', 'shiba-inu'
]

# 加密货币与股票关联映射
CRYPTO_STOCK_CORRELATION = {
    'bitcoin': ['COIN', 'MSTR', 'RIOT', 'MARA'],  # 加密货币相关股票
    'ethereum': ['COIN', 'ETHG'],
    'binancecoin': ['COIN'],
}


def get_crypto_price(coin_id: str, currency: str = 'usd') -> Optional[Dict]:
    """
    获取单个加密货币当前价格
    
    Args:
        coin_id: 币种 ID (如 'bitcoin')
        currency: 货币单位 (usd/cny)
    
    Returns:
        价格信息字典
    """
    try:
        url = f"{COINGECKO_BASE}/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': currency,
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true',
            'include_market_cap': 'true',
            'include_last_updated_at': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if coin_id in data:
            return {
                'coin_id': coin_id,
                'price': data[coin_id].get(currency, 0),
                'volume_24h': data[coin_id].get(f'{currency}_24h_vol', 0),
                'change_24h': data[coin_id].get(f'{currency}_24h_change', 0),
                'market_cap': data[coin_id].get(f'{currency}_market_cap', 0),
                'last_updated': data[coin_id].get('last_updated_at', 0)
            }
        return None
    except Exception as e:
        print(f"[!] CoinGecko API 错误：{e}")
        return None


def get_top_cryptos(limit: int = 20, currency: str = 'usd') -> List[Dict]:
    """
    获取前 N 个加密货币（按市值排序）
    
    Args:
        limit: 返回数量
        currency: 货币单位
    
    Returns:
        加密货币列表
    """
    try:
        url = f"{COINGECKO_BASE}/coins/markets"
        params = {
            'vs_currency': currency,
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': 'false'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        result = []
        for coin in data:
            result.append({
                'rank': coin.get('market_cap_rank', 0),
                'coin_id': coin.get('id', ''),
                'symbol': coin.get('symbol', '').upper(),
                'name': coin.get('name', ''),
                'price': coin.get('current_price', 0),
                'market_cap': coin.get('market_cap', 0),
                'volume_24h': coin.get('total_volume', 0),
                'change_24h': coin.get('price_change_percentage_24h', 0),
                'change_7d': coin.get('price_change_percentage_7d_in_currency', 0),
            })
        return result
    except Exception as e:
        print(f"[!] CoinGecko 顶部币种错误：{e}")
        return []


def get_crypto_history(coin_id: str, days: int = 30, currency: str = 'usd') -> Optional[pd.DataFrame]:
    """
    获取加密货币历史价格
    
    Args:
        coin_id: 币种 ID
        days: 天数
        currency: 货币单位
    
    Returns:
        DataFrame(日期，价格，市值，成交量)
    """
    try:
        url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': currency,
            'days': days,
            'interval': 'daily'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 解析价格数据
        prices = data.get('prices', [])
        market_caps = data.get('market_caps', [])
        volumes = data.get('total_volumes', [])
        
        df = pd.DataFrame({
            'date': [datetime.fromtimestamp(p[0]/1000) for p in prices],
            'price': [p[1] for p in prices],
            'market_cap': [m[1] for m in market_caps],
            'volume': [v[1] for v in volumes]
        })
        
        df = df.set_index('date')
        return df
    except Exception as e:
        print(f"[!] CoinGecko 历史数据错误：{e}")
        return None


def calculate_crypto_sentiment() -> Dict:
    """
    计算加密货币市场情绪
    
    Returns:
        情绪指标字典
    """
    top_cryptos = get_top_cryptos(20, 'usd')
    
    if not top_cryptos:
        return {'sentiment': 'neutral', 'score': 0}
    
    # 计算上涨/下跌比例
    up_count = sum(1 for c in top_cryptos if c['change_24h'] > 0)
    down_count = sum(1 for c in top_cryptos if c['change_24h'] < 0)
    
    # 计算平均涨跌幅
    avg_change = sum(c['change_24h'] for c in top_cryptos) / len(top_cryptos)
    
    # 比特币主导性
    btc = next((c for c in top_cryptos if c['coin_id'] == 'bitcoin'), None)
    btc_dominance = btc['market_cap'] / sum(c['market_cap'] for c in top_cryptos) if btc else 0
    
    # 情绪评分 (-1 到 +1)
    up_ratio = up_count / len(top_cryptos)
    sentiment_score = (up_ratio - 0.5) * 2  # -1 到 +1
    
    # 判断情绪
    if sentiment_score > 0.3:
        sentiment = 'bullish'
    elif sentiment_score < -0.3:
        sentiment = 'bearish'
    else:
        sentiment = 'neutral'
    
    return {
        'sentiment': sentiment,
        'score': round(sentiment_score, 3),
        'up_count': up_count,
        'down_count': down_count,
        'avg_change_24h': round(avg_change, 2),
        'btc_dominance': round(btc_dominance * 100, 1),
        'bitcoin_change': btc['change_24h'] if btc else 0
    }


def get_crypto_stock_correlation(crypto_id: str = 'bitcoin') -> Dict:
    """
    获取加密货币与相关股票的关联性
    
    Args:
        crypto_id: 币种 ID
    
    Returns:
        关联股票列表及关联度
    """
    related_stocks = CRYPTO_STOCK_CORRELATION.get(crypto_id, [])
    
    # 获取加密货币当前表现
    crypto_data = get_crypto_price(crypto_id)
    if not crypto_data:
        return {'correlation': 'unknown', 'stocks': []}
    
    crypto_change = crypto_data['change_24h']
    
    # 关联度分析（简化版）
    correlation_strength = 'strong' if abs(crypto_change) > 5 else 'moderate' if abs(crypto_change) > 2 else 'weak'
    
    return {
        'crypto_id': crypto_id,
        'crypto_change_24h': crypto_change,
        'correlation_strength': correlation_strength,
        'related_stocks': related_stocks,
        'note': f"{crypto_id} 24h 涨跌 {crypto_change:+.2f}%, 可能影响相关股票"
    }


def analyze_crypto_impact_on_stocks() -> Dict:
    """
    分析加密货币市场对股票市场的潜在影响
    
    Returns:
        影响分析报告
    """
    # 获取市场情绪
    sentiment = calculate_crypto_sentiment()
    
    # 获取比特币相关性
    btc_correlation = get_crypto_stock_correlation('bitcoin')
    eth_correlation = get_crypto_stock_correlation('ethereum')
    
    # 综合影响评分
    impact_score = sentiment['score'] * 0.5 + (btc_correlation['crypto_change_24h'] / 100) * 0.3
    
    # 影响方向
    if impact_score > 0.2:
        impact = 'positive'
        note = "加密货币市场走强，可能带动相关科技股"
    elif impact_score < -0.2:
        impact = 'negative'
        note = "加密货币市场走弱，可能拖累相关股票"
    else:
        impact = 'neutral'
        note = "加密货币市场平稳，对股市影响有限"
    
    return {
        'overall_impact': impact,
        'impact_score': round(impact_score, 3),
        'crypto_sentiment': sentiment,
        'bitcoin_correlation': btc_correlation,
        'ethereum_correlation': eth_correlation,
        'note': note
    }


# 测试
if __name__ == "__main__":
    print("="*60)
    print("DSS 加密货币模块测试")
    print("="*60)
    
    # 测试获取比特币价格
    print("\n📊 比特币价格:")
    btc = get_crypto_price('bitcoin', 'usd')
    if btc:
        print(f"   价格：${btc['price']:,.2f}")
        print(f"   24h 涨跌：{btc['change_24h']:+.2f}%")
        print(f"   市值：${btc['market_cap']:,.0f}")
    
    # 测试前 10 加密货币
    print("\n🏆 Top 10 加密货币:")
    top10 = get_top_cryptos(10, 'usd')
    for i, coin in enumerate(top10, 1):
        print(f"   {i}. {coin['name']} ({coin['symbol']}) ${coin['price']:,.2f} ({coin['change_24h']:+.2f}%)")
    
    # 测试市场情绪
    print("\n📈 市场情绪:")
    sentiment = calculate_crypto_sentiment()
    print(f"   情绪：{sentiment['sentiment']} (分数：{sentiment['score']:+.3f})")
    print(f"   上涨/下跌：{sentiment['up_count']}/{sentiment['down_count']}")
    print(f"   比特币主导率：{sentiment['btc_dominance']:.1f}%")
    
    # 测试影响分析
    print("\n🔗 对股市影响:")
    impact = analyze_crypto_impact_on_stocks()
    print(f"   整体影响：{impact['overall_impact']}")
    print(f"   影响分数：{impact['impact_score']:+.3f}")
    print(f"   说明：{impact['note']}")
    
    print("\n" + "="*60)
