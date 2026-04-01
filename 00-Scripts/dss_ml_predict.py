#!/usr/bin/env python3
"""
DSS 轻量级预测模块
使用简化特征进行快速预测
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

def get_quick_features(df):
    """提取快速预测特征"""
    close = df['Close']
    volume = df['Volume']
    
    # 价格变化特征
    returns = close.pct_change().dropna()
    
    features = {
        # 动量特征
        'return_1d': returns.tail(1).mean(),
        'return_5d': returns.tail(5).mean(),
        'return_10d': returns.tail(10).mean(),
        'volatility': returns.tail(20).std(),
        
        # 趋势特征
        'ma5': close.tail(5).mean(),
        'ma20': close.tail(20).mean(),
        'price_to_ma5': close.iloc[-1] / (close.tail(5).mean() + 1e-10),
        'price_to_ma20': close.iloc[-1] / (close.tail(20).mean() + 1e-10),
        
        # 成交量特征
        'volume_ratio': volume.iloc[-1] / (volume.tail(20).mean() + 1e-10),
        
        # 波动率
        'high_low_ratio': (close.tail(20).max() - close.tail(20).min()) / close.iloc[-1],
    }
    
    return features

def predict_next_day(df):
    """
    预测次日涨跌（简化版）
    返回: (方向, 置信度)
    """
    # 兼容大小写
    close_col = 'Close' if 'Close' in df.columns else 'close'
    volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
    
    close = df[close_col].dropna()
    
    if len(close) < 30:
        return 'neutral', 0.5
    
    # 简化预测：基于多个指标加权
    score = 0
    weights = 0
    
    # 1. 近期趋势 (权重 30%)
    returns = close.pct_change().dropna()
    recent_return = returns.tail(5).mean()
    score += recent_return * 300
    weights += 30
    
    # 2. 均线交叉 (权重 25%)
    ma5 = close.tail(5).mean()
    ma20 = close.tail(20).mean()
    if ma5 > ma20:
        score += 25
    else:
        score -= 25
    weights += 25
    
    # 3. RSI (权重 20%)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    rsi_series = 100 - 100 / (1 + rs)
    rsi = 50 if pd.isna(rsi_series).any() else rsi_series.iloc[-1]
    
    if rsi < 30:
        score += 20  # 超卖反弹
    elif rsi > 70:
        score -= 20  # 超买回调
    elif rsi < 45:
        score += 10
    elif rsi > 55:
        score -= 10
    weights += 20
    
    # 4. 成交量 (权重 15%)
    vol_col = 'Volume' if 'Volume' in df.columns else 'volume'
    vol_ma = df[vol_col].tail(20).mean()
    volume = df[vol_col].iloc[-1]
    if volume > vol_ma * 1.3:
        score += 15  # 放量
    elif volume < vol_ma * 0.7:
        score -= 10  # 缩量
    weights += 15
    
    # 5. 波动率 (权重 10%)
    volatility = returns.tail(20).std()
    if volatility > 0.03:
        score += 5  # 高波动有机会
    weights += 10
    
    # 归一化
    normalized = score / weights
    
    # 转换为方向和置信度
    if normalized > 0.15:
        direction = 'up'
        confidence = min(0.8, normalized)
    elif normalized < -0.15:
        direction = 'down'
        confidence = min(0.8, abs(normalized))
    else:
        direction = 'neutral'
        confidence = 0.5
    
    return direction, confidence

def get_ml_score(df):
    """
    获取机器学习预测评分 (-25 到 +25)
    """
    direction, confidence = predict_next_day(df)
    
    if direction == 'up':
        score = int(confidence * 25)
    elif direction == 'down':
        score = -int(confidence * 25)
    else:
        score = 0
    
    return score, {
        'direction': direction,
        'confidence': round(confidence, 2)
    }

# 测试
if __name__ == "__main__":
    import baostock as bs
    from datetime import datetime, timedelta
    
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        "sh.600519",
        "date,close,volume",
        start_date=(datetime.now() - timedelta(days=200)).strftime('%Y-%m-%d'),
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
    
    print("="*50)
    print("ML预测测试 - 贵州茅台")
    print("="*50)
    
    score, info = get_ml_score(df)
    print(f"预测方向: {info['direction']}")
    print(f"置信度: {info['confidence']}")
    print(f"ML评分: {score:+d}")
