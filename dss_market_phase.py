#!/usr/bin/env python3
"""
DSS 历史数据训练模块
使用上交所历史数据进行市场环境识别训练
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import json
import numpy as np
import pandas as pd
from dss_sse_history import get_historical_data, get_dataframe

def analyze_market_phases():
    """分析市场阶段特征"""
    data = get_historical_data()
    df = pd.DataFrame(data)
    
    # 定义市场阶段
    phases = []
    for i, row in df.iterrows():
        year = row['year']
        
        # 根据年收益率判断市场阶段
        if year == 2005:
            # 2005年底收盘1161 vs 2004年底(我需要这个数据)
            # 用高点/低点判断
            phase = 'bear'  # 2005年大部分是熊市
        elif year == 2006:
            phase = 'bull'  # 大牛市
        elif year == 2007:
            phase = 'bull'  # 牛市顶点
        elif year == 2008:
            phase = 'bear'  # 金融危机
        elif year == 2015:
            phase = 'volatile'  # 大涨大跌
        elif year == 2016:
            phase = 'consolidation'  # 震荡
            
        # 计算各项指标
        turnover_rate = row['trading_value'] / row['market_cap_negotiable'] * 100
        
        phases.append({
            'year': year,
            'phase': phase,
            'market_cap': row['market_cap_total'],
            'negotiable_cap': row['market_cap_negotiable'],
            'turnover_rate': turnover_rate,
            'index_high': row['sse_index_high'],
            'index_low': row['sse_index_low'],
            'index_change': (row['sse_index_close'] - row['sse_index_low']) / row['sse_index_low'] * 100,
            'notes': row['notes']
        })
    
    return phases

def get_phase_features():
    """获取各阶段的特征向量"""
    phases = analyze_market_phases()
    
    features = {}
    for p in phases:
        year = p['year']
        
        # 特征向量: [换手率, 市值/流通市值比, 波动率, 指数变化]
        features[year] = {
            'phase': p['phase'],
            'turnover_rate': p['turnover_rate'],
            'cap_ratio': p['market_cap'] / p['negotiable_cap'],
            'volatility': (p['index_high'] - p['index_low']) / p['index_low'] * 100,
            'index_return': p['index_change'],
        }
    
    return features

def get_current_market_phase(current_data):
    """
    判断当前市场属于哪个阶段
    用于DSS自适应指标参数调整
    """
    features = get_phase_features()
    
    # 计算历史平均值
    avg_turnover = np.mean([f['turnover_rate'] for f in features.values()])
    avg_volatility = np.mean([f['volatility'] for f in features.values()])
    avg_cap_ratio = np.mean([f['cap_ratio'] for f in features.values()])
    
    # 当前数据
    current_turnover = current_data.get('trading_value', 0) / current_data.get('negotiable_cap', 1) * 100
    current_volatility = current_data.get('volatility', 10)
    
    # 判断阶段
    if current_turnover > avg_turnover * 1.5:
        if current_volatility > avg_volatility * 1.3:
            return 'bull_high_vol'  # 牛市高波动
        else:
            return 'bull_normal'  # 牛市正常
    elif current_turnover < avg_turnover * 0.5:
        return 'bear'  # 熊市/盘整
    else:
        return 'consolidation'  # 震荡市

# 测试
if __name__ == "__main__":
    print("="*60)
    print("市场阶段分析")
    print("="*60)
    
    phases = analyze_market_phases()
    for p in phases:
        print(f"\n{p['year']}年: {p['phase']}")
        print(f"  换手率: {p['turnover_rate']:.1f}%")
        print(f"  波动率: {(p['index_high']-p['index_low'])/p['index_low']*100:.1f}%")
        print(f"  备注: {p['notes']}")
    
    print("\n" + "="*60)
    print("阶段特征")
    print("="*60)
    features = get_phase_features()
    for year, f in features.items():
        print(f"{year}: 换手{f['turnover_rate']:.0f}%, 波动{f['volatility']:.0f}%, 比例{f['cap_ratio']:.2f}")
