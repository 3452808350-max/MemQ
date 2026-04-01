"""特征工程模块"""
import numpy as np
import pandas as pd
from typing import List

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """技术指标计算"""
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # 移动平均
    for w in [5, 10, 20, 60]:
        df[f'MA{w}'] = close.rolling(w).mean()
        df[f'volume_MA{w}'] = volume.rolling(w).mean()
    
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    
    # 布林带
    mb = close.rolling(20).mean()
    std = close.rolling(20).std()
    df['BB_upper'] = mb + 2 * std
    df['BB_lower'] = mb - 2 * std
    df['BB_position'] = (close - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-10)
    
    # ATR
    high_low = high - low
    high_close = (high - close.shift(1)).abs()
    low_close = (low - close.shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    
    # 波动率
    df['volatility_5'] = close.pct_change().rolling(5).std()
    df['volatility_20'] = close.pct_change().rolling(20).std()
    
    # OBV
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    df['OBV'] = obv
    
    # 价格位置
    df['price_position'] = (close - low.rolling(20).min()) / (high.rolling(20).max() - low.rolling(20).min() + 1e-10)
    
    # 成交量变化
    df['volume_ratio'] = volume / volume.rolling(20).mean()
    
    # 动量
    for w in [5, 10, 20]:
        df[f'momentum_{w}'] = close.pct_change(w)
    
    # Stochastic
    low_min = low.rolling(14).min()
    high_max = high.rolling(14).max()
    df['stoch_k'] = 100 * (close - low_min) / (high_max - low_min + 1e-10)
    df['stoch_d'] = df['stoch_k'].rolling(3).mean()
    
    # Williams %R
    df['williams_r'] = -100 * (high_max - close) / (high_max - low_min + 1e-10)
    
    # ADX
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    df['ADX'] = ((plus_dm.rolling(14).mean() + minus_dm.rolling(14).mean()) / (tr + 1e-10)).rolling(14).mean() * 100
    
    # Pivot Points
    df['Pivot'] = (high + low + close) / 3
    df['R1'] = 2 * df['Pivot'] - low.rolling(2).min()
    df['S1'] = 2 * df['Pivot'] - high.rolling(2).max()
    
    return df

def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """准备特征矩阵"""
    feature_cols = [c for c in df.columns if c not in ['Open', 'High', 'Low', 'Close', 'Volume']]
    result = df[feature_cols].iloc[60:]
    if len(result) == 0:
        return df[feature_cols].tail(10)
    return result.iloc[:-5] if len(result) > 5 else result

def create_labels(df: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """创建预测标签"""
    future_return = df['Close'].shift(-horizon) / df['Close'] - 1
    labels = (future_return > 0).astype(int)
    # 去掉最后的NaN
    labels = labels[:-horizon] if horizon > 0 else labels
    return labels
