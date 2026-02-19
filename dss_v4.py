"""
DSS v4.0 - 改进版
基于Kimi建议的改进:
1. 增加基本面数据 (PE, PB, ROE)
2. 增加风控机制 (止损/止盈)
3. 改进模型 (XGBoost + LightGBM)
4. 增加市场环境判断
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import numpy as np
import pandas as pd
from dss_modules.data_loader import get_stock_data
from dss_modules.features import add_technical_indicators
from dss_modules.models import StockModel

# ============ 模拟基本面数据 (待替换为真实API) ============

def get_fundamentals_simulated(symbol):
    """模拟基本面数据 - 实际项目中应替换为真实API"""
    import random
    np.random.seed(hash(symbol) % 10000)
    
    # 随机生成基本面指标
    fundamentals = {
        'pe_ratio': np.random.uniform(5, 50),      # 市盈率
        'pb_ratio': np.random.uniform(0.5, 10),    # 市净率
        'roe': np.random.uniform(-10, 30),          # 净资产收益率
        'dividend_yield': np.random.uniform(0, 5), # 股息率
        'debt_ratio': np.random.uniform(10, 80),    # 资产负债率
    }
    return fundamentals

# ============ 风控机制 ============

class RiskManager:
    """风险管理器"""
    
    def __init__(self, stop_loss=0.05, take_profit=0.15):
        """
        Args:
            stop_loss: 止损比例 (默认5%)
            take_profit: 止盈比例 (默认15%)
        """
        self.stop_loss = stop_loss
        self.take_profit = take_profit
    
    def should_sell(self, entry_price, current_price):
        """判断是否应该卖出"""
        return_pct = (current_price - entry_price) / entry_price
        
        # 止盈
        if return_pct >= self.take_profit:
            return True, "take_profit"
        
        # 止损
        if return_pct <= -self.stop_loss:
            return True, "stop_loss"
        
        return False, None
    
    def calculate_position_size(self, total_capital, risk_per_trade=0.02):
        """计算仓位大小"""
        return total_capital * risk_per_trade / self.stop_loss

# ============ 改进的选股器 ============

class ImprovedStockPicker:
    """改进版选股器"""
    
    def __init__(self):
        self.risk_manager = RiskManager(stop_loss=0.05, take_profit=0.15)
        self.models = {
            'lgbm': StockModel('lgbm'),
            'xgb': StockModel('xgb'),
        }
    
    def get_comprehensive_features(self, symbol, days=250):
        """获取综合特征 (技术 + 基本面)"""
        # 获取技术数据
        df = get_stock_data(symbol, days, 'baostock')
        if df is None or len(df) < 100:
            return None
        
        # 添加技术指标
        df = add_technical_indicators(df)
        df = df.dropna()
        
        if len(df) < 30:
            return None
        
        # 添加基本面特征 (模拟)
        fundamentals = get_fundamentals_simulated(symbol)
        for key, value in fundamentals.items():
            df[key] = value
        
        return df
    
    def calculate_sentiment_score(self, symbol):
        """计算情绪分数 - 基于技术指标"""
        df = self.get_comprehensive_features(symbol, 60)
        if df is None:
            return 0
        
        latest = df.iloc[-1]
        score = 0
        
        # RSI: 超卖加分, 超买减分
        rsi = latest.get('RSI', 50)
        if rsi < 30:
            score += 20
        elif rsi > 70:
            score -= 20
        
        # MACD: 金叉加分
        if latest.get('MACD', 0) > 0:
            score += 15
        else:
            score -= 15
        
        # 均线多头
        ma5 = latest.get('MA5', 0)
        ma20 = latest.get('MA20', 0)
        if ma5 > ma20:
            score += 10
        else:
            score -= 10
        
        # 成交量
        vol = latest.get('Volume', 0)
        vol_ma = latest.get('volume_MA20', 0)
        if vol > vol_ma * 1.5:
            score += 10
        
        return score
    
    def analyze_stock(self, symbol):
        """综合分析股票"""
        df = self.get_comprehensive_features(symbol)
        if df is None:
            return None
        
        latest = df.iloc[-1]
        
        # 基础分数
        score = 0
        
        # 技术面评分
        rsi = latest.get('RSI', 50)
        if rsi < 30:
            score += 20
        elif rsi > 70:
            score -= 20
        
        macd = latest.get('MACD', 0)
        if macd > 0:
            score += 15
        
        ma5 = latest.get('MA5', 0)
        ma20 = latest.get('MA20', 0)
        if ma5 > ma20:
            score += 10
        
        # 基本面评分
        pe = latest.get('pe_ratio', 20)
        if 10 < pe < 25:
            score += 10
        elif pe > 50:
            score -= 10
        
        roe = latest.get('roe', 0)
        if roe > 15:
            score += 15
        elif roe < 0:
            score -= 10
        
        # 情绪分数
        sentiment = self.calculate_sentiment_score(symbol)
        
        return {
            'symbol': symbol,
            'close': latest['Close'],
            'tech_score': score,
            'sentiment_score': sentiment,
            'total_score': score + sentiment,
            'fundamentals': {
                'pe': latest.get('pe_ratio'),
                'roe': latest.get('roe'),
                'dividend': latest.get('dividend_yield'),
            }
        }
    
    def predict_with_confidence(self, symbol):
        """带置信度的预测"""
        df = self.get_comprehensive_features(symbol, 250)
        if df is None or len(df) < 50:
            return None
        
        # 准备特征
        feature_cols = [c for c in df.columns 
                      if c not in ['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # 添加基本面到特征
        df['label'] = (df['Close'].shift(-5) / df['Close'] > 1.02).astype(int)
        df = df.dropna()
        
        if len(df) < 30:
            return None
        
        X = df[feature_cols].values
        y = df['label'].values
        
        valid = ~np.isnan(X).any(axis=1)
        X, y = X[valid], y[valid]
        
        if len(X) < 25:
            return None
        
        # 用两个模型
        split = len(X) - 10
        
        # LightGBM
        lgbm = StockModel('lgbm')
        lgbm.fit(X[:split], y[:split])
        proba_lgbm = lgbm.predict_proba(X[split:])[0]
        
        # XGBoost
        try:
            xgb = StockModel('xgb')
            xgb.fit(X[:split], y[:split])
            proba_xgb = xgb.predict_proba(X[split:])[0]
        except:
            proba_xgb = proba_lgbm
        
        # 集成预测
        proba_ensemble = (proba_lgbm + proba_xgb) / 2
        
        # 计算置信度
        confidence = abs(proba_ensemble - 0.5) * 2 * 100
        
        return {
            'direction': '上涨' if proba_ensemble > 0.5 else '下跌',
            'confidence': confidence,
            'lgbm_prob': proba_lgbm,
            'xgb_prob': proba_xgb,
            'ensemble_prob': proba_ensemble,
        }

# ============ 入口函数 ============

def pick_best_stocks_improved(stocks=None, top_n=5):
    """改进版选股"""
    if stocks is None:
        # 默认股票池
        stocks = {
            'sh.601111': ('中国国航', '航空'),
            'sh.600048': ('保利地产', '地产'),
            'sh.600519': ('贵州茅台', '白酒'),
            'sh.601398': ('工商银行', '银行'),
            'sh.601318': ('中国平安', '保险'),
        }
    
    picker = ImprovedStockPicker()
    results = []
    
    for code, (name, industry) in stocks.items():
        # 综合分析
        analysis = picker.analyze_stock(code)
        
        # 预测
        prediction = picker.predict_with_confidence(code)
        
        if analysis and prediction:
            analysis['name'] = name
            analysis['industry'] = industry
            analysis['prediction'] = prediction
            results.append(analysis)
    
    # 按总分排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    return results[:top_n]

# ============ 测试 ============

if __name__ == "__main__":
    print("="*60)
    print("DSS v4.0 - 改进版选股测试")
    print("="*60)
    
    # 测试选股
    stocks = {
        'sh.601111': ('中国国航', '航空'),
        'sh.600519': ('贵州茅台', '白酒'),
        'sh.601398': ('工商银行', '银行'),
    }
    
    results = pick_best_stocks_improved(stocks, top_n=3)
    
    print("\n📊 选股结果:")
    print("-"*60)
    for i, r in enumerate(results, 1):
        pred = r['prediction']
        print(f"\n{i}. {r['name']} ({r['symbol']})")
        print(f"   行业: {r['industry']}")
        print(f"   收盘价: ¥{r['close']:.2f}")
        print(f"   技术评分: {r['tech_score']:+d}")
        print(f"   情绪评分: {r['sentiment_score']:+d}")
        print(f"   综合评分: {r['total_score']:+d}")
        print(f"   预测: {pred['direction']} (置信度: {pred['confidence']:.0f}%)")
        print(f"   PE: {r['fundamentals']['pe']:.1f}, ROE: {r['fundamentals']['roe']:.1f}%")
    
    print("\n" + "="*60)
