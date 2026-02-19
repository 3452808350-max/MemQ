"""
DSS Swarm - 完整传统行业追踪
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_modules.data_loader import get_stock_data
from dss_modules.features import add_technical_indicators
from dss_modules.models import StockModel
import numpy as np

# 完整传统行业股票池
STOCKS = {
    # 金融
    'sh.601398': ('工商银行', '银行'),
    'sh.601939': ('建设银行', '银行'),
    'sh.601318': ('中国平安', '保险'),
    # 能源
    'sh.601857': ('中国石油', '能源'),
    'sh.600028': ('中国石化', '能源'),
    # 消费
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    # 地产
    'sh.000002': ('万科A', '地产'),
    # 汽车
    'sh.600104': ('上汽集团', '汽车'),
    # 高铁
    'sh.601766': ('中国中车', '高铁'),
    # 航空
    'sh.601111': ('中国国航', '航空'),
    # 铁路
    'sh.601006': ('大秦铁路', '铁路'),
    # 快递
    'sz.002352': ('顺丰控股', '快递'),
    # 电力
    'sh.600900': ('长江电力', '电力'),
    # 水泥
    'sh.600585': ('海螺水泥', '水泥'),
    # 医药
    'sh.600276': ('恒瑞医药', '医药'),
    'sz.000513': ('丽珠集团', '医药'),
    # 珠宝
    'sh.600612': ('老凤祥', '珠宝'),
    # 纺织
    'sz.002293': ('罗莱生活', '纺织'),
    # 农业
    'sh.600108': ('亚盛集团', '农业'),
    # 种业
    'sz.000998': ('隆平高科', '种业'),
    # 基建
    'sh.601668': ('中国建筑', '基建'),
    'sh.601390': ('中国中铁', '基建'),
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
    signals.append('金叉' if macd > 0 else '死叉')
    
    ma5 = latest.get('MA5', 0)
    ma20 = latest.get('MA20', 0)
    signals.append('多头' if ma5 > ma20 else '空头')
    
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
            pred = '涨' if proba[0] > 0.5 else '跌'
            conf = int(abs(proba[0] - 0.5) * 200)
    
    return {'close': latest['Close'], 'signals': signals, 'pred': pred, 'conf': conf}

def generate_report():
    print('='*75)
    print('               传统行业股票每日监控报告 (完整版)')
    print('='*75)
    
    results = {}
    for code, (name, industry) in STOCKS.items():
        info = get_stock_info(code)
        if info:
            results[industry] = results.get(industry, [])
            results[industry].append({'code': code, 'name': name, **info})
    
    for industry, stocks in results.items():
        print(f'\n[{industry}]')
        print('-'*75)
        for s in stocks:
            signal = s['signals'][0] if s['signals'] else ''
            pred = f"{s['pred']} {s['conf']}%" if s['pred'] else '--'
            code = s['code'].replace('sh.', '').replace('sz.', '')
            print(f"  {s['name']:10s} ({code:8s})  ¥{s['close']:8.2f}  信号:{signal:6s}  预测:{pred}")
    
    print('\n' + '='*75)

if __name__ == "__main__":
    generate_report()
