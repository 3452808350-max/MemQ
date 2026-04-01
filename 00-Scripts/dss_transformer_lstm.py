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
    # 检查 GPU
    if torch.cuda.is_available():
        DEVICE = torch.device('cuda')
        print(f"✓ PyTorch available + CUDA GPU: {torch.cuda.get_device_name(0)}")
    else:
        DEVICE = torch.device('cpu')
        print("✓ PyTorch available (CPU only)")
except ImportError:
    TORCH_AVAILABLE = False
    DEVICE = torch.device('cpu')
    print("✗ PyTorch not available, using fallback")

class LSTMModel(nn.Module):
    """自定义 LSTM 模型，正确处理 LSTM 输出"""
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, 
                           num_layers=num_layers, batch_first=True, dropout=dropout)
        self.fc1 = nn.Linear(hidden_size, 32)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(32, 1)
    
    def forward(self, x):
        # LSTM 输出：(output, (hn, cn))
        lstm_out, _ = self.lstm(x)
        # 取最后一个时间步的输出
        last_output = lstm_out[:, -1, :]  # (batch, hidden_size)
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.fc2(out)
        return out

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
        # 数据量检查
        if len(X_train) < 30:
            print(f"  LSTM: 数据不足 ({len(X_train)} samples), 使用简化训练")
            epochs = min(epochs, 10)
        
        # PyTorch LSTM - GPU 加速
        # X_train shape: (batch, seq_length, features) - already 3D
        X_train_tensor = torch.FloatTensor(X_train).to(DEVICE)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(-1).to(DEVICE)
        X_test_tensor = torch.FloatTensor(X_test).to(DEVICE)
        y_test_tensor = torch.FloatTensor(y_test).unsqueeze(-1).to(DEVICE)
        
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        
        # 创建模型并移到 GPU
        model = LSTMModel(input_size=1, hidden_size=64, num_layers=2, dropout=0.2).to(DEVICE)
        
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        # 训练 + early stopping
        model.train()
        best_loss = float('inf')
        patience = 5
        patience_counter = 0
        avg_loss = 0
        
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            avg_loss = total_loss / len(train_loader)
            
            # Early stopping
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"  LSTM: Early stop at epoch {epoch+1}, loss: {avg_loss:.6f}")
                    break
        
        print(f"  LSTM: Trained {epoch+1} epochs on {DEVICE}, loss: {avg_loss:.6f}")
    else:
        # Sklearn 回退
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train.reshape(len(X_train), -1), y_train.ravel())
        print(f"RandomForest trained with {len(X_train)} samples")
    
    # 评估
    if TORCH_AVAILABLE:
        model.eval()
        with torch.no_grad():
            pred = model(X_test_tensor)
            test_rmse = np.sqrt(criterion(pred, y_test_tensor).item())
        print(f"  LSTM: Test RMSE: {test_rmse:.6f}")
    else:
        # Sklearn 回退
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train.reshape(len(X_train), -1), y_train.ravel())
        pred = model.predict(X_test.reshape(len(X_test), -1))
        test_rmse = np.sqrt(np.mean((pred - y_test.ravel())**2))
        print(f"  RF: Test RMSE: {test_rmse:.6f}")
    
    return model, scaler, seq_length, test_rmse

def predict_next_days(model, scaler, seq_length, prices, days=5):
    """预测未来 N 天"""
    # 准备最后 seq_length 个数据
    last_seq = prices.values[-seq_length:].reshape(-1, 1)
    last_seq_scaled = scaler.transform(last_seq)
    
    predictions = []
    
    if TORCH_AVAILABLE:
        # Reshape to (1, seq_length, 1) for batch_first LSTM
        current_seq = torch.FloatTensor(last_seq_scaled).unsqueeze(0).to(DEVICE)  # (1, seq_length, 1)
        model.eval()
        with torch.no_grad():
            for _ in range(days):
                pred = model(current_seq)
                pred_value = pred[0, 0].cpu().item()
                predictions.append(pred_value)
                # 更新序列：去掉第一个，添加新的预测值
                new_value = torch.FloatTensor([[pred_value]]).to(DEVICE)
                new_seq = torch.cat([current_seq[:, 1:, :], new_value.unsqueeze(0)], dim=1)
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
    获取 LSTM 预测信号 - CPU 优化版 (使用 sklearn RandomForest)
    返回：(方向，置信度，预测变化率)
    """
    if len(prices) < 60:
        return 'neutral', 0.5, 0.0
    
    try:
        from sklearn.ensemble import RandomForestRegressor
        
        # 准备数据
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(prices.values.reshape(-1, 1))
        
        # 创建序列
        X, y = create_sequences(scaled_data, seq_length)
        
        if len(X) < 30:
            return 'neutral', 0.5, 0.0
        
        # 训练集/测试集
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # 训练模型 - CPU 上 RandomForest 比 LSTM 快 10 倍 +
        model = RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42, n_jobs=-1)
        model.fit(X_train.reshape(len(X_train), -1), y_train.ravel())
        
        # 预测未来 5 天
        last_seq = scaled_data[-seq_length:].reshape(1, seq_length, 1)
        predictions = []
        
        for _ in range(5):
            pred = model.predict(last_seq.reshape(1, -1))[0]
            predictions.append(pred)
            last_seq = np.concatenate([last_seq[0, 1:, 0], [pred]]).reshape(1, seq_length, 1)
        
        # 反归一化
        predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        
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
