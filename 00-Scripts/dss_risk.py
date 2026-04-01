#!/usr/bin/env python3
"""
DSS 风控模块
- 仓位管理
- 止损止盈
- 风险评分
"""
import numpy as np
import pandas as pd

def calculate_risk_score(df, entry_price=None):
    """
    计算股票风险评分
    
    返回: (风险等级, 风险分数, 建议仓位)
    风险等级: low, medium, high
    """
    # 兼容大小写
    close_col = 'Close' if 'Close' in df.columns else 'close'
    volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
    
    close_price = df[close_col].iloc[-1]
    high20 = df[close_col].tail(20).max()
    low20 = df[close_col].tail(20).min()
    
    # 1. 位置风险 (当前价格在近期高低点位置)
    if len(df) >= 20:
        position = (close_price - low20) / (high20 - low20 + 1e-10)
    else:
        position = 0.5
    
    # 2. 波动率风险
    returns = df[close_col].pct_change().dropna()
    volatility = returns.tail(20).std()
    volatility_risk = min(1.0, volatility / 0.05)  # 5%波动率为满分
    
    # 3. 成交量风险
    vol_ma = df[volume_col].tail(20).mean()
    volume = df[volume_col].iloc[-1]
    volume_risk = 0.5
    if volume < vol_ma * 0.5:
        volume_risk = 0.3  # 缩量风险
    elif volume > vol_ma * 2:
        volume_risk = 0.8  # 放量可能是突破或恐慌
    
    # 4. RSI风险
    delta = df[close_col].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    rsi = (100 - 100 / (1 + rs)).iloc[-1]
    
    rsi_risk = 0.5
    if rsi > 80:
        rsi_risk = 1.0  # 严重超买
    elif rsi > 70:
        rsi_risk = 0.8
    elif rsi < 20:
        rsi_risk = 1.0  # 严重超卖（但可能是机会）
    elif rsi < 30:
        rsi_risk = 0.6
    
    # 综合风险分数 (0-100)
    risk_score = int(
        position * 20 + 
        volatility_risk * 30 + 
        volume_risk * 20 + 
        rsi_risk * 30
    )
    
    # 风险等级
    if risk_score < 35:
        risk_level = 'low'
        position_size = 'full'  # 满仓
    elif risk_score < 60:
        risk_level = 'medium'
        position_size = 'half'  # 半仓
    else:
        risk_level = 'high'
        position_size = 'quarter'  # 轻仓
    
    # 特殊处理：超卖可能是机会
    if rsi < 25:
        risk_level = 'low'
        position_size = 'full'
        risk_score = max(20, risk_score - 20)
    
    return risk_level, risk_score, position_size

def should_stop_loss(entry_price, current_price, stop_loss_pct=0.05):
    """
    判断是否应该止损
    """
    if entry_price is None:
        return False
    
    loss_pct = (current_price - entry_price) / entry_price
    
    if loss_pct <= -stop_loss_pct:
        return True, 'stop_loss'
    elif loss_pct >= stop_loss_pct * 2:  # 止盈
        return True, 'take_profit'
    
    return False, None

def get_position_recommendation(stock_score, risk_level, market_regime='range'):
    """
    获取仓位建议
    
    Args:
        stock_score: 股票评分
        risk_level: 风险等级 (low, medium, high)
        market_regime: 市场状态
    """
    # 基础仓位
    if stock_score > 40:
        base_position = 1.0
    elif stock_score > 20:
        base_position = 0.7
    elif stock_score > 0:
        base_position = 0.5
    else:
        base_position = 0.2
    
    # 风险调整
    if risk_level == 'low':
        risk_multiplier = 1.0
    elif risk_level == 'medium':
        risk_multiplier = 0.7
    else:
        risk_multiplier = 0.4
    
    # 市场状态调整
    if market_regime == 'trending':
        regime_multiplier = 1.1  # 趋势市可以适当加仓
    else:
        regime_multiplier = 0.9  # 震荡市降低仓位
    
    final_position = base_position * risk_multiplier * regime_multiplier
    
    # 转换为建议
    if final_position >= 0.8:
        recommendation = '强烈推荐'
    elif final_position >= 0.5:
        recommendation = '谨慎推荐'
    elif final_position >= 0.3:
        recommendation = '观望'
    else:
        recommendation = '不推荐'
    
    return final_position, recommendation

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
    
    # 测试
    print("="*50)
    print("风控测试 - 贵州茅台")
    print("="*50)
    print("Columns:", df.columns.tolist())
    print(df.head())
    
    risk_level, risk_score, position = calculate_risk_score(df)
    print(f"风险等级: {risk_level}")
    print(f"风险分数: {risk_score}")
    print(f"建议仓位: {position}")
    
    pos, rec = get_position_recommendation(50, risk_level)
    print(f"仓位比例: {pos:.0%}")
    print(f"推荐度: {rec}")
