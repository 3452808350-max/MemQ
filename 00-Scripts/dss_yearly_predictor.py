#!/usr/bin/env python3
"""
DSS 年度市场预测模型
使用上交所历史数据训练
预测下一年市场走势
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import json
import os

# 数据路径
DATA_DIR = '/home/kyj/.openclaw/workspace/data/sse_package'

def load_training_data():
    """加载训练数据"""
    X = pd.read_csv(f'{DATA_DIR}/SSE_DSS特征矩阵_标准化.csv')
    y_binary = pd.read_csv(f'{DATA_DIR}/SSE_DSS目标_二分类.csv')
    y_trend = pd.read_csv(f'{DATA_DIR}/SSE_DSS目标_三分类.csv')
    
    return X, y_binary, y_trend

def train_classification_model(X, y):
    """训练分类模型"""
    # 标准化数据没有年份列，直接使用
    features = X.columns.tolist()
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 训练随机森林
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)
    
    return model, scaler, features

def train_regression_model(X, y):
    """训练回归模型"""
    features = X.columns.tolist()
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)
    
    return model, scaler, features

def predict_next_year(model, scaler, features, current_data):
    """预测下一年"""
    # 准备当前年份数据
    X = pd.DataFrame([current_data])
    
    # 确保列顺序一致
    for col in features:
        if col not in X.columns:
            X[col] = 0
    
    X = X[features]
    X_scaled = scaler.transform(X)
    
    prediction = model.predict(X_scaled)
    probability = model.predict_proba(X_scaled) if hasattr(model, 'predict_proba') else None
    
    return prediction, probability

def get_current_year_features():
    """获取当前年份的特征（从最新数据）"""
    df = pd.read_csv(f'{DATA_DIR}/SSE_DSS特征矩阵_标准化.csv')
    return df.iloc[-1].to_dict()

def analyze_prediction(model, features, current_data, target_name='下年是否上涨'):
    """分析预测结果"""
    prediction, prob = predict_next_year(model[0], model[1], features, current_data)
    
    result = {
        'prediction': int(prediction[0]) if hasattr(prediction, '__iter__') else int(prediction),
        'direction': '上涨' if prediction[0] == 1 else '下跌' if prediction[0] == 0 else '震荡',
    }
    
    if prob is not None:
        result['probability'] = prob[0].tolist()
    
    return result

# 主程序
if __name__ == "__main__":
    print("="*60)
    print("DSS 年度市场预测模型")
    print("="*60)
    
    # 加载数据
    print("\n加载训练数据...")
    X, y_binary, y_trend = load_training_data()
    print(f"特征数: {X.shape[1]}, 样本数: {X.shape[0]}")
    
    # 训练分类模型
    print("\n训练分类模型...")
    clf_model, clf_scaler, features = train_classification_model(X, y_binary)
    print("✓ 分类模型训练完成")
    
    # 获取当前年份特征
    current = get_current_year_features()
    
    # 预测
    print("\n预测下一年市场...")
    prediction, prob = predict_next_year(clf_model, clf_scaler, features, current)
    
    print(f"\n预测结果:")
    print(f"  方向: {'上涨' if prediction[0] == 1 else '下跌'}")
    if prob is not None:
        print(f"  上涨概率: {prob[0][1]*100:.1f}%")
        print(f"  下跌概率: {prob[0][0]*100:.1f}%")
    
    # 特征重要性
    print("\n特征重要性 (Top 10):")
    importance = pd.DataFrame({
        'feature': features,
        'importance': clf_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for i, row in importance.head(10).iterrows():
        print(f"  {row['feature']}: {row['importance']:.4f}")
