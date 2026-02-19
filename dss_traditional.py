"""
DSS Swarm - 传统行业追踪
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_modules.data_loader import get_stock_data
from dss_modules.features import add_technical_indicators
from dss_modules.models import StockModel
import numpy as np

# 传统行业股票池
STOCKS = {
    'sh.601398': ('工商银行', '银行'),
    'sh.601939': ('建设银行', '银行'),
    'sh.601318': ('中国平安', '保险'),
    'sh.601857': ('中国石油', '能源'),
    'sh.600028': ('中国石化', '能源'),
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    'sh.000002': ('万科A', '地产'),
}

def get_stock_info(symbol):
    df = get_stock_data(symbol, 250, 'baostock')
    if df is None or len(df) < 100:
        return None
    
    df = add_technical_indicators(df)
    df = df.dropna()
    if len(df) < 30:
        return None
    
    latest = df.iloc[-1]
    
    signals = []
    rsi = latest.get('RSI', 50)
    if rsi < 30:
        signals.append('RSI超卖')
    elif rsi > 70:
        signals.append('RSI超买')
    
    macd = latest.get('MACD', 0)
    signals.append('MACD金叉' if macd > 0 else 'MACD死叉')
    
    ma5 = latest.get('MA5', 0)
    ma20 = latest.get('MA20', 0)
    signals.append('MA多头' if ma5 > ma20 else 'MA空头')
    
    # 预测
    df['label'] = (df['Close'].shift(-5) / df['Close'] > 1.02).astype(int)
    df = df.dropna()
    
    pred = conf = None
    if len(df) > 30:
        feature_cols = [c for c in df.columns if c not in ['Open','High','Low','Close','Volume','label']]
        X = df[feature_cols].values
        y = df['label'].values
        valid = ~np.isnan(X).any(axis=1)
        X, y = X[valid], y[valid]
        if len(X) > 25:
            split = len(X) - 10
            model = StockModel('lgbm')
            model.fit(X[:split], y[:split])
            proba = model.predict_proba(X[split:])
            pred = '上涨' if proba[0] > 0.5 else '下跌'
            conf = int(abs(proba[0] - 0.5) * 200)
    
    return {'close': latest['Close'], 'signals': signals, 'pred': pred, 'conf': conf}

def generate_report():
    print('='*65)
    print('          传统行业股票每日监控报告')
    print('='*65)
    
    results = {}
    for code, (name, industry) in STOCKS.items():
        info = get_stock_info(code)
        if info:
            results[industry] = results.get(industry, [])
            results[industry].append({'name': name, **info})
    
    for industry, stocks in results.items():
        print(f'\n[{industry}]')
        print('-'*65)
        for s in stocks:
            signal = s['signals'][0] if s['signals'] else ''
            pred = f"{s['pred']} {s['conf']}%" if s['pred'] else '--'
            print(f"  {s['name']:8s}  收盘:¥{s['close']:8.2f}  信号:{signal:8s}  预测:{pred}")
    
    print('\n' + '='*65)

if __name__ == "__main__":
    generate_report()
