#!/usr/bin/env python3
"""
DSS LSTM 预测模块
基于LSTM的股票价格预测
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')

# 尝试导入TensorFlow/Keras
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
    print("✓ TensorFlow available")
except ImportError:
    TF_AVAILABLE = False
    print("✗ TensorFlow not available, using fallback")

def create_sequences(data, seq_length):
    """创建时间序列数据"""
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length])
    return np.array(X), np.array(y)

def prepare_data(prices, seq_length=20):
    """准备LSTM训练数据"""
    # 归一化
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(prices.values.reshape(-1, 1))
    
    # 创建序列
    X, y = create_sequences(scaled_data, seq_length)
    
    # 划分训练/测试 (80/20)
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    
    return X_train, y_train, X_test, y_test, scaler

def build_lstm_model(seq_length):
    """构建LSTM模型"""
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=(seq_length, 1)),
        Dropout(0.2),
        LSTM(32, return_sequences=False),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dense(1)
    ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def train_and_predict(prices, seq_length=20, epochs=50):
    """
    训练LSTM模型并预测
    
    返回: (预测方向, 置信度, 模型预测值)
    """
    if not TF_AVAILABLE:
        # 简化版：使用线性回归作为fallback
        returns = prices.pct_change().dropna()
        recent_mean = returns.tail(10).mean()
        
        if recent_mean > 0.01:
            return 'up', min(0.8, recent_mean * 10), recent_mean
        elif recent_mean < -0.01:
            return 'down', min(0.8, abs(recent_mean) * 10), recent_mean
        else:
            return 'neutral', 0.5, recent_mean
    
    try:
        # 准备数据
        X_train, y_train, X_test, y_test, scaler = prepare_data(prices, seq_length)
        
        if len(X_train) < 50:
            # 数据太少，使用fallback
            returns = prices.pct_change().dropna()
            recent_mean = returns.tail(10).mean()
            if recent_mean > 0.005:
                return 'up', 0.6, recent_mean
            elif recent_mean < -0.005:
                return 'down', 0.6, recent_mean
            else:
                return 'neutral', 0.5, recent_mean
        
        # 构建模型
        model = build_lstm_model(seq_length)
        
        # 早停
        early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
        
        # 训练
        model.fit(
            X_train, y_train,
            epochs=min(epochs, 30),
            batch_size=32,
            validation_split=0.1,
            callbacks=[early_stop],
            verbose=0
        )
        
        # 预测未来5天
        last_seq = scaler.transform(prices.values[-seq_length:].reshape(-1, 1))
        predictions = []
        
        for _ in range(5):
            pred = model.predict(last_seq.reshape(1, seq_length, 1), verbose=0)
            predictions.append(pred[0, 0])
            
            # 更新序列
            last_seq = np.append(last_seq[1:], pred[0, 0]).reshape(-1, 1)
        
        # 反归一化
        predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        
        # 计算预测方向和置信度
        current_price = prices.iloc[-1]
        avg_pred = predictions.mean()
        change_pct = (avg_pred - current_price) / current_price
        
        # 置信度基于预测变化的幅度
        confidence = min(0.85, abs(change_pct) * 5)
        
        if change_pct > 0.01:
            direction = 'up'
        elif change_pct < -0.01:
            direction = 'down'
        else:
            direction = 'neutral'
        
        return direction, confidence, change_pct
        
    except Exception as e:
        print(f"LSTM error: {e}")
        # Fallback
        returns = prices.pct_change().dropna()
        recent_mean = returns.tail(10).mean()
        if recent_mean > 0.005:
            return 'up', 0.5, recent_mean
        elif recent_mean < -0.005:
            return 'down', 0.5, recent_mean
        else:
            return 'neutral', 0.5, recent_mean

def get_lstm_score(prices):
    """
    获取LSTM预测评分 (-30 到 +30)
    """
    direction, confidence, change_pct = train_and_predict(prices)
    
    if direction == 'up':
        score = int(confidence * 30)
    elif direction == 'down':
        score = -int(confidence * 30)
    else:
        score = 0
    
    return score, {
        'direction': direction,
        'confidence': round(confidence, 2),
        'change_pct': round(change_pct * 100, 2)
    }

# 测试
if __name__ == "__main__":
    import baostock as bs
    from datetime import datetime, timedelta
    
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        "sh.600519",
        "date,close",
        start_date=(datetime.now() - timedelta(days=300)).strftime('%Y-%m-%d'),
        frequency="d"
    )
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    df = pd.DataFrame(data, columns=['date', 'close'])
    df['close'] = pd.to_numeric(df['close'])
    prices = df['close'].dropna()
    
    print("="*50)
    print("LSTM预测测试 - 贵州茅台")
    print("="*50)
    
    score, info = get_lstm_score(prices)
    print(f"预测方向: {info['direction']}")
    print(f"置信度: {info['confidence']}")
    print(f"预测变化: {info['change_pct']}%")
    print(f"LSTM评分: {score:+d}")
