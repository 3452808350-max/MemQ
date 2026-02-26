#!/usr/bin/env python3
"""
DSS 自适应技术指标模块
- 自适应RSI: 根据波动率动态调整周期
- 自适应MACD: 根据市场状态切换参数
- 市场状态检测: 趋势/震荡判断
"""
import numpy as np
import pandas as pd

def detect_market_regime(prices, window=20):
    """
    检测市场状态
    返回: 'trending' (趋势) 或 'range' (震荡)
    """
    if isinstance(prices, pd.Series):
        prices = prices.iloc[-window:]  # 取最后window个值
    
    # 转换为numpy数组处理
    if isinstance(prices, pd.Series):
        prices_arr = prices.values
    else:
        prices_arr = np.array(prices)
    
    if len(prices_arr) < window:
        return 'range'
    
    # 最近的价格范围
    recent_high = np.max(prices_arr[-window:])
    recent_low = np.min(prices_arr[-window:])
    price_range = recent_high - recent_low
    
    if price_range == 0:
        return 'range'
    
    # 当前价格位置
    current_price = prices_arr[-1]
    position = (current_price - recent_low) / price_range
    
    # 如果价格持续在高位或低位 -> 趋势
    if position > 0.85 or position < 0.15:
        return 'trending'
    
    # 检查是否有明显的趋势（通过比较最近的高/低价）
    last_5 = prices_arr[-5:]
    if np.all(np.diff(last_5) > 0) or np.all(np.diff(last_5) < 0):
        return 'trending'
    
    return 'range'

def adaptive_rsi(prices, base_period=14, lookback=60):
    """
    自适应RSI - 根据波动率动态调整周期
    
    Args:
        prices: 价格序列
        base_period: 基础周期
        lookback: 用于计算波动率的回看周期
    """
    # 计算波动率 (收益率标准差)
    returns = prices.pct_change().dropna()
    volatility = returns.tail(lookback).std()
    
    # 波动率高时使用更长周期以减少噪音
    vol_percentile = returns.tail(252).std()  # 年化波动率
    if volatility > vol_percentile * 1.2:
        period = int(base_period * 1.5)
    elif volatility < vol_percentile * 0.8:
        period = int(base_period * 0.7)
    else:
        period = base_period
    
    period = max(7, min(28, period))  # 限制在7-28之间
    
    # 计算RSI
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    # 动态超买超卖阈值
    rsi_std = rsi.tail(60).std()
    rsi_mean = rsi.tail(60).mean()
    
    # 自适应阈值：波动市场更宽松
    if volatility > vol_percentile * 1.3:
        oversold = 25
        overbought = 75
    else:
        oversold = 30
        overbought = 70
    
    return rsi, {
        'period': period,
        'oversold': oversold,
        'overbought': overbought,
        'volatility': volatility,
        'regime': detect_market_regime(prices)
    }

def adaptive_macd(prices, base_fast=12, base_slow=26, base_signal=9):
    """
    自适应MACD - 根据市场状态动态调整参数
    
    Args:
        prices: 价格序列
        base_fast/slow/signal: 基础参数
    """
    # 检测市场状态
    regime = detect_market_regime(prices)
    
    if regime == 'trending':
        # 趋势市场：用更慢的参数减少假信号
        fast, slow, signal = 8, 21, 9
    else:
        # 震荡市场：用更快的参数捕捉反弹
        fast, slow, signal = 5, 17, 5
    
    # 计算MACD
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram, {
        'fast': fast,
        'slow': slow,
        'signal': signal,
        'regime': regime,
        'cross': 'golden' if macd_line.iloc[-1] > signal_line.iloc[-1] else 'death'
    }

def adaptive_bollinger_bands(prices, window=20):
    """
    自适应布林带 - 根据波动率调整带宽
    """
    # 检测市场状态
    returns = prices.pct_change().dropna()
    volatility = returns.tail(20).std()
    avg_volatility = returns.tail(252).std()
    
    # 波动率高时使用更宽的带
    if volatility > avg_volatility * 1.3:
        num_std = 2.5
    elif volatility < avg_volatility * 0.7:
        num_std = 1.5
    else:
        num_std = 2.0
    
    middle = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    
    upper = middle + num_std * std
    lower = middle - num_std * std
    
    # 计算位置
    bbp = (prices - lower) / (upper - lower + 1e-10)
    
    return upper, middle, lower, bbp

def calculate_adaptive_score(prices, rsi_data, macd_data, volume):
    """
    计算综合评分 - 自适应版本
    
    返回: (总分, 详细评分)
    """
    rsi, rsi_info = rsi_data
    macd_line, signal_line, hist, macd_info = macd_data
    
    latest_rsi = rsi.iloc[-1]
    latest_macd = macd_line.iloc[-1]
    latest_signal = signal_line.iloc[-1]
    latest_hist = hist.iloc[-1]
    
    score = 0
    details = []
    
    # RSI评分 (权重: 30%)
    if latest_rsi < rsi_info['oversold']:
        rsi_score = 30
    elif latest_rsi > rsi_info['overbought']:
        rsi_score = -30
    elif latest_rsi > 50:
        rsi_score = 10
    else:
        rsi_score = -10
    score += rsi_score
    details.append(f"RSI({latest_rsi:.1f}): {rsi_score:+d}")
    
    # MACD评分 (权重: 30%)
    if macd_info['cross'] == 'golden':
        macd_score = 20 + min(10, latest_hist * 10)
    else:
        macd_score = -20 + max(-10, latest_hist * 10)
    score += macd_score
    details.append(f"MACD({macd_info['cross']}): {macd_score:+d}")
    
    # 趋势评分 (权重: 20%)
    if macd_info['regime'] == 'trending':
        # 趋势市场中，MA多头排列更可靠
        ma5 = prices.rolling(5).mean().iloc[-1]
        ma20 = prices.rolling(20).mean().iloc[-1]
        if ma5 > ma20:
            trend_score = 20
        else:
            trend_score = -20
    else:
        # 震荡市场中，价格在布林带中轨附近更好
        trend_score = 0
    score += trend_score
    details.append(f"Trend({macd_info['regime']}): {trend_score:+d}")
    
    # 成交量评分 (权重: 20%)
    vol_ma20 = volume.rolling(20).mean().iloc[-1]
    if volume.iloc[-1] > vol_ma20 * 1.2:
        vol_score = 15
    elif volume.iloc[-1] > vol_ma20:
        vol_score = 5
    else:
        vol_score = -5
    score += vol_score
    details.append(f"Volume: {vol_score:+d}")
    
    return int(score), {
        'total': score,
        'details': details,
        'rsi_info': rsi_info,
        'macd_info': macd_info
    }

# 测试
if __name__ == "__main__":
    import baostock as bs
    from datetime import datetime, timedelta
    
    # 获取测试数据
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        "sh.600519",
        "date,close,volume",
        start_date=(datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d'),
        frequency="d"
    )
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    df = pd.DataFrame(data, columns=['date', 'close', 'volume'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])
    df = df.dropna()
    
    prices = df['close']
    volume = df['volume']
    
    # 测试自适应指标
    print("="*50)
    print("自适应指标测试 - 贵州茅台")
    print("="*50)
    
    rsi, rsi_info = adaptive_rsi(prices)
    macd_line, signal_line, hist, macd_info = adaptive_macd(prices)
    
    print(f"\n市场状态: {macd_info['regime']}")
    print(f"RSI周期: {rsi_info['period']}天 (超卖:{rsi_info['oversold']}, 超买:{rsi_info['overbought']})")
    print(f"MACD参数: ({macd_info['fast']}, {macd_info['slow']}, {macd_info['signal']}) - {macd_info['cross']}")
    print(f"最新RSI: {rsi.iloc[-1]:.1f}")
    print(f"最新MACD: {macd_line.iloc[-1]:.2f}")
    
    score, score_details = calculate_adaptive_score(prices, (rsi, rsi_info), (macd_line, signal_line, hist, macd_info), volume)
    print(f"\n综合评分: {score:+d}")
    for d in score_details['details']:
        print(f"  {d}")
