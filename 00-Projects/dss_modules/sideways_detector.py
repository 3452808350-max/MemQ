"""
横盘检测模块 - 改进版
通过多维度指标检测横盘/震荡市场
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Literal

def detect_sideways(
    df: pd.DataFrame,
    window: int = 20,
    atr_threshold: float = 0.02,  # ATR阈值（相对于价格）
    adx_threshold: float = 25,    # ADX阈值
    bb_width_threshold: float = 0.05,  # 布林带宽度阈值
    correlation_threshold: float = 0.3,  # 价格自相关阈值
) -> Tuple[bool, Dict]:
    """
    多维度横盘检测
    
    Args:
        df: DataFrame with OHLCV data
        window: 检测窗口
        atr_threshold: ATR相对于均价的阈值
        adx_threshold: ADX阈值（低于此值为无趋势）
        bb_width_threshold: 布林带宽度阈值
        correlation_threshold: 价格时间相关性阈值
    
    Returns:
        (是否横盘, 详细信息)
    """
    if len(df) < window + 10:
        return False, {"error": "Insufficient data"}
    
    close = df['Close'].iloc[-window:]
    high = df['High'].iloc[-window:]
    low = df['Low'].iloc[-window:]
    
    results = {}
    
    # 1. ATR检测 - 波动率是否足够低
    atr = calculate_atr(df).iloc[-window:]
    avg_price = close.mean()
    atr_ratio = atr.mean() / avg_price
    results['atr_ratio'] = atr_ratio
    results['atr_pass'] = atr_ratio < atr_threshold
    
    # 2. ADX检测 - 趋势强度是否足够低
    adx = calculate_adx(df).iloc[-window:]
    results['adx'] = adx.iloc[-1]
    results['adx_pass'] = adx.iloc[-1] < adx_threshold
    
    # 3. 布林带宽度检测
    bb_width = calculate_bb_width(df).iloc[-window:]
    results['bb_width'] = bb_width.mean()
    results['bb_pass'] = bb_width.mean() < bb_width_threshold
    
    # 4. 价格范围检测 - 最高价与最低价比率
    price_range_ratio = (high.max() - low.min()) / close.mean()
    results['price_range_ratio'] = price_range_ratio
    results['range_pass'] = price_range_ratio < 0.08  # 8%范围内
    
    # 5. 线性趋势检测 - 价格与时间的相关性
    x = np.arange(len(close))
    slope, intercept = np.polyfit(x, close.values, 1)
    correlation = np.corrcoef(x, close.values)[0, 1]
    results['trend_slope'] = slope
    results['trend_correlation'] = abs(correlation)
    results['trend_pass'] = abs(correlation) < correlation_threshold
    
    # 6. 支撑阻力位检测 - 价格是否在一定区间内震荡
    support = low.min()
    resistance = high.max()
    channel_width = (resistance - support) / close.mean()
    results['channel_width'] = channel_width
    results['channel_pass'] = channel_width < 0.06  # 6%通道宽度
    
    # 7. 成交量萎缩检测（可选）
    if 'Volume' in df.columns:
        volume = df['Volume'].iloc[-window:]
        vol_ma = df['Volume'].iloc[-window*2:-window].mean()
        vol_ratio = volume.mean() / vol_ma if vol_ma > 0 else 1
        results['volume_ratio'] = vol_ratio
        results['volume_pass'] = vol_ratio < 1.2  # 成交量未放大
    else:
        results['volume_pass'] = True
    
    # 综合判断 - 多数指标通过才算横盘
    passes = [
        results['atr_pass'],
        results['adx_pass'],
        results['bb_pass'],
        results['range_pass'],
        results['trend_pass'],
        results['channel_pass'],
        results['volume_pass'],
    ]
    
    # 至少5/7个指标通过才算横盘
    is_sideways = sum(passes) >= 5
    results['passes'] = sum(passes)
    results['total_checks'] = len(passes)
    results['is_sideways'] = is_sideways
    
    # 置信度评分
    confidence = sum(passes) / len(passes)
    results['confidence'] = confidence
    
    return is_sideways, results


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算ATR"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """计算ADX（平均趋向指数）"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # +DM和-DM
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # TR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR
    atr = tr.rolling(window=period).mean()
    
    # +DI和-DI
    plus_di = 100 * plus_dm.rolling(window=period).mean() / atr
    minus_di = 100 * minus_dm.rolling(window=period).mean() / atr
    
    # DX和ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx = dx.rolling(window=period).mean()
    
    return adx


def calculate_bb_width(df: pd.DataFrame, period: int = 20, num_std: float = 2) -> pd.Series:
    """计算布林带宽度"""
    close = df['Close']
    
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    upper = middle + num_std * std
    lower = middle - num_std * std
    
    # 布林带宽度 = (上轨 - 下轨) / 中轨
    width = (upper - lower) / (middle + 1e-10)
    
    return width


def get_sideways_strength(df: pd.DataFrame, window: int = 20) -> float:
    """
    获取横盘强度评分 (0-100)
    越高表示越可能是横盘
    """
    is_sideways, details = detect_sideways(df, window)
    
    if not is_sideways:
        return 0.0
    
    # 基于置信度计算强度
    base_score = details['confidence'] * 100
    
    # 根据ADX调整（ADX越低，横盘越明显）
    adx_factor = max(0, (25 - details['adx']) / 25)
    
    # 根据波动率调整
    vol_factor = max(0, 1 - details['atr_ratio'] / 0.02)
    
    final_score = base_score * (0.5 + 0.25 * adx_factor + 0.25 * vol_factor)
    
    return min(100, final_score)


def detect_sideways_zones(
    df: pd.DataFrame,
    min_window: int = 10,
    max_window: int = 60,
    step: int = 5
) -> list:
    """
    检测多个时间窗口的横盘区间
    
    Returns:
        横盘区间列表，每个元素为 (start_idx, end_idx, strength)
    """
    zones = []
    
    for window in range(min_window, max_window + 1, step):
        if len(df) < window:
            continue
            
        # 滑动窗口检测
        for i in range(len(df) - window + 1):
            window_df = df.iloc[i:i+window]
            is_sideways, details = detect_sideways(window_df, window)
            
            if is_sideways and details['confidence'] > 0.7:
                strength = get_sideways_strength(window_df, window)
                zones.append({
                    'start': i,
                    'end': i + window,
                    'window': window,
                    'strength': strength,
                    'details': details
                })
    
    # 合并重叠区间
    zones = merge_overlapping_zones(zones)
    
    return zones


def merge_overlapping_zones(zones: list) -> list:
    """合并重叠的横盘区间"""
    if not zones:
        return []
    
    # 按起始位置排序
    zones = sorted(zones, key=lambda x: x['start'])
    
    merged = [zones[0]]
    
    for current in zones[1:]:
        last = merged[-1]
        
        # 检查是否重叠
        if current['start'] <= last['end']:
            # 合并
            last['end'] = max(last['end'], current['end'])
            last['strength'] = max(last['strength'], current['strength'])
            last['window'] = max(last['window'], current['window'])
        else:
            merged.append(current)
    
    return merged


# 测试代码
if __name__ == "__main__":
    import baostock as bs
    from datetime import datetime, timedelta
    
    # 获取测试数据
    lg = bs.login()
    
    # 测试几只股票
    test_stocks = ["sh.600519", "sz.000001", "sh.000001"]
    
    for stock in test_stocks:
        print(f"\n{'='*60}")
        print(f"测试股票: {stock}")
        print('='*60)
        
        rs = bs.query_history_k_data_plus(
            stock,
            "date,open,high,low,close,volume",
            start_date=(datetime.now() - timedelta(days=120)).strftime('%Y-%m-%d'),
            frequency="d"
        )
        
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        
        df = pd.DataFrame(data, columns=['date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col])
        df = df.dropna()
        
        if len(df) < 30:
            print(f"数据不足: {len(df)}")
            continue
        
        # 检测当前是否横盘
        is_sideways, details = detect_sideways(df)
        
        print(f"\n当前是否横盘: {'是' if is_sideways else '否'}")
        print(f"置信度: {details.get('confidence', 0):.2%}")
        print(f"通过指标: {details.get('passes', 0)}/{details.get('total_checks', 7)}")
        
        print(f"\n详细指标:")
        print(f"  ATR比率: {details.get('atr_ratio', 0):.4f} {'✓' if details.get('atr_pass') else '✗'}")
        print(f"  ADX: {details.get('adx', 0):.1f} {'✓' if details.get('adx_pass') else '✗'}")
        print(f"  布林带宽度: {details.get('bb_width', 0):.4f} {'✓' if details.get('bb_pass') else '✗'}")
        print(f"  价格区间: {details.get('price_range_ratio', 0):.4f} {'✓' if details.get('range_pass') else '✗'}")
        print(f"  趋势相关性: {details.get('trend_correlation', 0):.4f} {'✓' if details.get('trend_pass') else '✗'}")
        print(f"  通道宽度: {details.get('channel_width', 0):.4f} {'✓' if details.get('channel_pass') else '✗'}")
        
        # 检测横盘区间
        zones = detect_sideways_zones(df)
        print(f"\n检测到 {len(zones)} 个横盘区间")
        for i, zone in enumerate(zones[:3]):  # 只显示前3个
            print(f"  区间{i+1}: 第{zone['start']}-{zone['end']}天, 强度:{zone['strength']:.1f}")
    
    bs.logout()
