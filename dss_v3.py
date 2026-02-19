#!/usr/bin/env python3
"""DSS v3.0 - 模块化股票预测系统"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# 导入模块
from dss_modules.data_loader import get_stock_data, fetch_multi_source, SYMBOLS
from dss_modules.features import add_technical_indicators, prepare_features, create_labels
from dss_modules.models import StockModel, walk_forward_train
from dss_modules.backtest import Backtester, evaluate_predictions

class MarketRegimeDetector:
    """市场状态检测"""
    
    @staticmethod
    def detect(df: pd.DataFrame) -> str:
        ma20 = df['Close'].rolling(20).mean()
        ma60 = df['Close'].rolling(60).mean()
        volatility = df['Close'].pct_change().rolling(20).std()
        
        if len(ma20) < 60 or pd.isna(ma60.iloc[-1]):
            return 'unknown'
        
        price = df['Close'].iloc[-1]
        
        # 牛市
        if price > ma20.iloc[-1] > ma60.iloc[-1]:
            return 'bull'
        # 熊市
        elif price < ma20.iloc[-1] < ma60.iloc[-1]:
            return 'bear'
        # 高波动
        elif volatility.iloc[-1] > volatility.quantile(0.8):
            return 'volatile'
        # 震荡
        else:
            return 'sideways'

class DSSv3:
    """DSS主系统"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or list(SYMBOLS.keys())[:5]
        self.models = {}
    
    def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """分析单个股票"""
        print(f"[DSS] 分析 {symbol}...")
        
        # 获取数据
        df = get_stock_data(symbol, 150)
        if df is None or len(df) < 100:
            print(f"[!] {symbol} 数据不足")
            return None
        
        # 特征工程
        df = add_technical_indicators(df)
        df = df.dropna()
        
        if len(df) < 50:
            return None
        
        # 准备数据
        X = prepare_features(df).values
        y = create_labels(df).iloc[prepare_features(df).index].values
        
        # 过滤NaN
        valid = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
        X, y = X[valid], y[valid]
        
        if len(X) < 50:
            return None
        
        # 训练模型
        model = StockModel('lgbm')
        
        # 简单划分
        split = int(len(X) * 0.7)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        model.fit(X_train, y_train)
        
        # 预测
        pred = model.predict(X_test)
        proba = model.predict_proba(X_test)
        
        # 评估
        metrics = evaluate_predictions(y_test, pred)
        
        # 回测
        bt = Backtester(initial_capital=100000, stop_loss=0.05, take_profit=0.10)
        prices = df['Close'].iloc[split:]
        signals = pred[:len(prices)]
        result = bt.run(prices, signals)
        
        # 市场状态
        regime = MarketRegimeDetector.detect(df)
        
        return {
            'symbol': symbol,
            'accuracy': metrics['accuracy'],
            'precision': metrics['precision'],
            'return': result.total_return,
            'sharpe': result.sharpe_ratio,
            'max_dd': result.max_drawdown,
            'regime': regime,
            'confidence': float(np.mean(proba))
        }
    
    def run(self) -> List[Dict]:
        """运行分析"""
        results = []
        
        for symbol in self.symbols:
            result = self.analyze_symbol(symbol)
            if result:
                results.append(result)
                print(f"  → {symbol}: 准确率={result['accuracy']:.1%}, "
                      f"收益={result['return']:.1%}, 市场={result['regime']}")
        
        return results

def main():
    """主入口"""
    print("="*50)
    print("DSS v3.0 - 模块化股票预测系统")
    print("="*50)
    
    dss = DSSv3(symbols=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'])
    results = dss.run()
    
    if results:
        print("\n📊 汇总结果:")
        avg_acc = np.mean([r['accuracy'] for r in results])
        avg_ret = np.mean([r['return'] for r in results])
        print(f"  平均准确率: {avg_acc:.1%}")
        print(f"  平均收益: {avg_ret:.1%}")

if __name__ == '__main__':
    main()
