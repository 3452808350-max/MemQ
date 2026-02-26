#!/usr/bin/env python3
"""
DSS 回测引擎
基于 Backtrader 的策略回测系统
优先级：高 (策略验证能力)
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 尝试导入 backtrader
try:
    import backtrader as bt
    BACKTRADER_AVAILABLE = True
    print("✓ Backtrader available")
    
    class DSSStrategy(bt.Strategy):
        """DSS 交易策略"""
        params = (
            ('dss_threshold', 30),
            ('stop_loss', 0.05),
            ('take_profit', 0.15),
            ('position_size', 0.1),
        )
        
        def __init__(self):
            self.dataclose = self.datas[0].close
            self.order = None
            self.buyprice = None
            self.buycomm = None
            self.sma20 = bt.indicators.SimpleMovingAverage(self.datas[0], period=20)
        
        def notify_order(self, order):
            if order.status in [order.Submitted, order.Accepted]:
                return
            if order.status in [order.Completed]:
                if order.isbuy():
                    self.buyprice = order.executed.price
                    self.buycomm = order.executed.comm
                else:
                    self.buyprice = None
                    self.buycomm = None
            self.order = None
        
        def notify_trade(self, trade):
            if not trade.isclosed:
                return
            print(f"  交易完成 - 毛利：{trade.pnl:.2f}, 净利：{trade.pnlcomm:.2f}")
        
        def next(self):
            if self.order:
                return
            if not self.position:
                if self.dataclose[0] < self.sma20[0] * 0.95:
                    size = int(self.broker.getcash() * self.params.position_size / self.dataclose[0])
                    if size > 0:
                        self.order = self.buy(size=size)
            else:
                if self.dataclose[0] > self.buyprice * (1 + self.params.take_profit):
                    self.order = self.sell(size=self.position.size)
                elif self.dataclose[0] < self.buyprice * (1 - self.params.stop_loss):
                    self.order = self.sell(size=self.position.size)

except ImportError:
    BACKTRADER_AVAILABLE = False
    print("✗ Backtrader not available, using simple backtest")

class SimpleBacktest:
    """简单回测引擎（Backtrader 不可用时）"""
    def __init__(self, initial_cash=1000000):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.position = 0
        self.trades = []
    
    def run(self, df, buy_signals, sell_signals):
        """运行回测"""
        for i in range(len(df)):
            if buy_signals[i] and self.cash > 0:
                # 买入
                shares = int(self.cash * 0.95 / df.iloc[i])
                if shares > 0:
                    cost = shares * df.iloc[i]
                    self.cash -= cost
                    self.position = shares
                    self.trades.append({'type': 'buy', 'price': df.iloc[i], 'shares': shares, 'date': df.index[i]})
            
            elif sell_signals[i] and self.position > 0:
                # 卖出
                revenue = self.position * df.iloc[i]
                self.cash = revenue
                self.trades.append({'type': 'sell', 'price': df.iloc[i], 'shares': self.position, 'date': df.index[i]})
                self.position = 0
        
        # 清仓
        if self.position > 0:
            self.cash = self.position * df.iloc[-1]
            self.trades.append({'type': 'sell', 'price': df.iloc[-1], 'shares': self.position, 'date': df.index[-1]})
            self.position = 0
        
        return self.calculate_metrics(df)
    
    def calculate_metrics(self, df):
        """计算回测指标"""
        total_return = (self.cash - self.initial_cash) / self.initial_cash
        
        # 计算交易次数
        buy_count = len([t for t in self.trades if t['type'] == 'buy'])
        
        # 计算胜率
        wins = 0
        for i in range(0, len(self.trades)-1, 2):
            if i+1 < len(self.trades):
                if self.trades[i+1]['price'] > self.trades[i]['price']:
                    wins += 1
        
        win_rate = wins / max(1, buy_count)
        
        return {
            'initial_cash': self.initial_cash,
            'final_cash': self.cash,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'trade_count': buy_count,
            'win_rate': win_rate,
            'trades': self.trades
        }

def backtest_dss_strategy(df, dss_scores, initial_cash=1000000):
    """
    回测 DSS 策略
    
    Args:
        df: 价格数据 (DataFrame with 'close')
        dss_scores: DSS 评分序列
        initial_cash: 初始资金
    
    Returns:
        回测结果字典
    """
    if BACKTRADER_AVAILABLE:
        return backtest_with_bt(df, dss_scores, initial_cash)
    else:
        return backtest_simple(df, dss_scores, initial_cash)

def backtest_with_bt(df, dss_scores, initial_cash=1000000):
    """使用 Backtrader 回测"""
    if not BACKTRADER_AVAILABLE:
        return backtest_simple(df, dss_scores, initial_cash)
    
    # 准备数据
    data = bt.feeds.PandasData(dataname=df)
    
    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(DSSStrategy, dss_threshold=30, stop_loss=0.05, take_profit=0.15)
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)
    
    print(f"初始资金：{initial_cash:,.2f}")
    
    initial_value = cerebro.broker.getvalue()
    cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    total_return = (final_value - initial_value) / initial_value
    
    return {
        'initial_cash': initial_cash,
        'final_cash': final_value,
        'total_return': total_return,
        'total_return_pct': total_return * 100,
        'trade_count': 0,
        'win_rate': 0
    }

def backtest_simple(df, dss_scores, initial_cash=1000000):
    """简单回测"""
    # 生成买卖信号
    buy_signals = dss_scores > 40
    sell_signals = dss_scores < -20
    
    backtester = SimpleBacktest(initial_cash)
    results = backtester.run(df['close'], buy_signals, sell_signals)
    
    return results

def analyze_backtest(results):
    """分析回测结果"""
    print("\n" + "="*60)
    print("回测结果分析")
    print("="*60)
    print(f"初始资金：¥{results['initial_cash']:,.2f}")
    print(f"最终资金：¥{results['final_cash']:,.2f}")
    print(f"总收益率：{results['total_return_pct']:.2f}%")
    print(f"交易次数：{results['trade_count']}")
    print(f"胜率：{results['win_rate']*100:.1f}%")
    print("="*60)

# 测试
if __name__ == "__main__":
    import baostock as bs
    
    print("="*60)
    print("DSS 回测引擎测试")
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
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    df['close'] = pd.to_numeric(df['close'])
    
    # 模拟 DSS 评分
    np.random.seed(42)
    dss_scores = pd.Series(np.random.randn(len(df)) * 30, index=df.index)
    
    print(f"\n数据：{len(df)}天")
    print(f"价格范围：¥{df['close'].min():.2f} - ¥{df['close'].max():.2f}")
    
    # 运行回测
    results = backtest_dss_strategy(df, dss_scores, initial_cash=1000000)
    analyze_backtest(results)
