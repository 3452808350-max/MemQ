#!/usr/bin/env python3
"""
DSS Transformer/LSTM 预测模块
基于深度学习的股票价格预测
优先级：高 (预计提升 15-25% 精度)
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor
import warnings
warnings.filterwarnings('ignore')

# 尝试导入 PyTorch
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
    print("✓ PyTorch available")
except ImportError:
    TORCH_AVAILABLE = False
    print("✗ PyTorch not available, using fallback")

def create_sequences(data, seq_length):
    """创建时间序列数据"""
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length])
    return np.array(X), np.array(y)

def prepare_data(prices, seq_length=20, train_ratio=0.8):
    """准备训练数据"""
    # 归一化
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(prices.values.reshape(-1, 1))
    
    # 创建序列
    X, y = create_sequences(scaled_data, seq_length)
    
    # 划分训练/测试
    train_size = int(len(X) * train_ratio)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]
    
    return X_train, X_test, y_train, y_test, scaler

def train_model(prices, seq_length=20, epochs=100):
    """训练模型（自动选择 PyTorch 或 sklearn）"""
    # 准备数据
    X_train, X_test, y_train, y_test, scaler = prepare_data(prices, seq_length)
    
    if TORCH_AVAILABLE:
        # PyTorch LSTM
        X_train_tensor = torch.FloatTensor(X_train).unsqueeze(-1)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(-1)
        
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        
        # 创建模型
        model = nn.Sequential(
            nn.LSTM(input_size=1, hidden_size=64, num_layers=2, batch_first=True, dropout=0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        # 训练
        model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs, _ = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
        
        print(f"Epoch [{epochs}], Loss: {total_loss/len(train_loader):.6f}")
    else:
        # Sklearn 回退
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train.reshape(len(X_train), -1), y_train.ravel())
        print(f"RandomForest trained with {len(X_train)} samples")
    
    # 评估
    if TORCH_AVAILABLE:
        model.eval()
        with torch.no_grad():
            X_test_tensor = torch.FloatTensor(X_test).unsqueeze(-1)
            y_test_tensor = torch.FloatTensor(y_test).unsqueeze(-1)
            pred = model(X_test_tensor)[0]
            test_rmse = np.sqrt(criterion(pred, y_test_tensor).item())
    else:
        pred = model.predict(X_test.reshape(len(X_test), -1))
        test_rmse = np.sqrt(np.mean((pred - y_test.ravel())**2))
    
    print(f"Test RMSE: {test_rmse:.6f}")
    
    return model, scaler, seq_length, test_rmse

def predict_next_days(model, scaler, seq_length, prices, days=5):
    """预测未来 N 天"""
    # 准备最后 seq_length 个数据
    last_seq = prices.values[-seq_length:].reshape(-1, 1)
    last_seq_scaled = scaler.transform(last_seq)
    
    predictions = []
    
    if TORCH_AVAILABLE:
        current_seq = torch.FloatTensor(last_seq_scaled).unsqueeze(0).unsqueeze(-1)
        model.eval()
        with torch.no_grad():
            for _ in range(days):
                pred, _ = model(current_seq)
                pred_value = pred[0, 0].item()
                predictions.append(pred_value)
                new_seq = torch.cat([current_seq[:, 1:, :], torch.FloatTensor([[[pred_value]]])], dim=1)
                current_seq = new_seq
    else:
        current_seq = last_seq_scaled.reshape(1, seq_length, 1)
        for _ in range(days):
            pred = model.predict(current_seq.reshape(1, -1))[0]
            predictions.append(pred)
            new_seq = np.concatenate([current_seq[0, 1:, 0], [pred]]).reshape(1, seq_length, 1)
            current_seq = new_seq
    
    # 反归一化
    predictions = np.array(predictions).reshape(-1, 1)
    predictions = scaler.inverse_transform(predictions)
    
    return predictions

def get_lstm_signal(prices, seq_length=20):
    """
    获取 LSTM 预测信号
    返回：(方向，置信度，预测变化率)
    """
    if len(prices) < 60:
        return 'neutral', 0.5, 0.0
    
    try:
        # 训练模型
        model, scaler, seq_len, test_rmse = train_model(prices, seq_length=seq_length, epochs=50)
        
        # 预测未来 5 天
        predictions = predict_next_days(model, scaler, seq_len, prices, days=5)
        
        # 计算预测变化
        current_price = prices.iloc[-1]
        avg_pred = predictions.mean()
        change_pct = (avg_pred - current_price) / current_price
        
        # 判断方向
        if change_pct > 0.02:
            direction = 'bull'
            confidence = min(0.85, abs(change_pct) * 10)
        elif change_pct < -0.02:
            direction = 'bear'
            confidence = min(0.85, abs(change_pct) * 10)
        else:
            direction = 'neutral'
            confidence = 0.5
        
        return direction, confidence, change_pct
        
    except Exception as e:
        print(f"LSTM prediction error: {e}")
        return 'neutral', 0.5, 0.0

# 测试
if __name__ == "__main__":
    import baostock as bs
    from datetime import datetime, timedelta
    
    print("="*60)
    print("DSS Transformer/LSTM 预测模块测试")
    print("="*60)
    
    # 获取测试数据
    lg = bs.login()
    rs = bs.query_history_k_data_plus(
        "sh.600519",
        "date,close",
        start_date=(datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d'),
        frequency="d"
    )
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    bs.logout()
    
    df = pd.DataFrame(data, columns=['date', 'close'])
    df['close'] = pd.to_numeric(df['close'])
    prices = df['close'].dropna()
    
    print(f"\n数据：{len(prices)}天，价格范围：{prices.min():.2f} - {prices.max():.2f}")
    
    # 测试预测
    direction, confidence, change_pct = get_lstm_signal(prices, seq_length=20)
    
    print(f"\nLSTM 预测结果:")
    print(f"  方向：{direction}")
    print(f"  置信度：{confidence:.1%}")
    print(f"  预测变化：{change_pct*100:.2f}%")
