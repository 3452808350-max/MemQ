#!/usr/bin/env python3
"""
DSS 增强版报告生成器
生成更详细的分析报告
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dss_ml_predict import predict_next_day
from dss_risk import calculate_risk_score, get_position_recommendation

# 核心股票池
CORE_STOCKS = {
    'sh.601398': ('工商银行', '银行'),
    'sh.600036': ('招商银行', '银行'),
    'sh.601318': ('中国平安', '保险'),
    'sh.601857': ('中国石油', '能源'),
    'sh.600028': ('中国石化', '能源'),
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    'sh.000002': ('万科A', '地产'),
    'sh.600048': ('保利地产', '地产'),
    'sh.600104': ('上汽集团', '汽车'),
    'sh.600900': ('长江电力', '电力'),
    'sh.600276': ('恒瑞医药', '医药'),
    'sh.601668': ('中国建筑', '基建'),
    'sh.603986': ('兆易创新', '芯片'),
    'sh.600570': ('恒生电子', '软件'),
    'sz.002594': ('比亚迪', '新能源车'),
    'sz.300750': ('宁德时代', '电池'),
    'sh.601012': ('隆基绿能', '光伏'),
    'sz.002415': ('海康威视', '安防'),
}

def get_stock_details(code, name, industry):
    """获取股票详细信息"""
    try:
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume,amount",
            start_date=(datetime.now() - timedelta(days=250)).strftime('%Y-%m-%d'),
            frequency="d"
        )
        
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list or len(data_list) < 100:
            return None
        
        df = pd.DataFrame(data_list, columns=['date','open','high','low','close','volume','amount'])
        for col in ['open','high','low','close','volume','amount']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()
        
        if len(df) < 100:
            return None
        
        # 计算指标
        close = df['close']
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs_val = gain / (loss + 1e-10)
        rsi = 100 - 100 / (1 + rs_val)
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        
        # 均线
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        
        # 成交量均线
        vol_ma20 = df['volume'].rolling(20).mean()
        
        latest = df.iloc[-1]
        
        # ML预测
        ml_direction, ml_conf = predict_next_day(df)
        
        # 风控
        risk_level, risk_score, position = calculate_risk_score(df)
        
        return {
            'code': code,
            'name': name,
            'industry': industry,
            'close': latest['close'],
            'change_pct': (latest['close'] - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100,
            'volume': latest['volume'],
            'rsi': rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50,
            'macd': '金叉' if macd.iloc[-1] > signal.iloc[-1] else '死叉',
            'ma_cross': '多头' if ma5.iloc[-1] > ma20.iloc[-1] else '空头',
            'volume_ratio': latest['volume'] / vol_ma20.iloc[-1] if not pd.isna(vol_ma20.iloc[-1]) else 1,
            'ml_direction': ml_direction,
            'ml_conf': ml_conf,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'position': position,
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_enhanced_report():
    """生成增强版报告"""
    print("="*70)
    print("DSS 增强版每日分析报告")
    print("="*70)
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Login failed: {lg.error_msg}")
        return
    
    try:
        results = []
        for code, (name, industry) in CORE_STOCKS.items():
            print(f"分析: {name}...", end=" ")
            info = get_stock_details(code, name, industry)
            if info:
                results.append(info)
                print("✓")
            else:
                print("✗")
        
        # 按综合评分排序
        results.sort(key=lambda x: x['change_pct'], reverse=True)
        
        print("\n" + "="*70)
        print("📈 今日涨跌幅排名")
        print("="*70)
        for i, r in enumerate(results[:10], 1):
            print(f"{i:2d}. {r['name']:8s} {r['change_pct']:+.2f}%  "
                  f"RSI:{r['rsi']:5.1f} {r['macd']} {r['ma_cross']} "
                  f"ML:{r['ml_direction']}")
        
        print("\n" + "="*70)
        print("🎯 ML预测方向统计")
        print("="*70)
        up = sum(1 for r in results if r['ml_direction'] == 'up')
        down = sum(1 for r in results if r['ml_direction'] == 'down')
        neutral = sum(1 for r in results if r['ml_direction'] == 'neutral')
        print(f"看涨: {up}只 | 看跌: {down}只 | 中性: {neutral}只")
        
        print("\n" + "="*70)
        print("⚠️ 风险提示")
        print("="*70)
        high_risk = [r for r in results if r['risk_level'] == 'high']
        if high_risk:
            print("高风险股票:")
            for r in high_risk[:5]:
                print(f"  - {r['name']}: 风险分数 {r['risk_score']}")
        else:
            print("无高风险股票")
        
    finally:
        bs.logout()

if __name__ == "__main__":
    generate_enhanced_report()
