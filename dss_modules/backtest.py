"""回测模块"""
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Trade:
    """交易记录"""
    date: str
    action: str  # 'buy' or 'sell'
    price: float
    shares: int

@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trades: List[Trade]

class Backtester:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000,
                 transaction_cost: float = 0.001,
                 stop_loss: float = 0.05,
                 take_profit: float = 0.10):
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.stop_loss = stop_loss
        self.take_profit = take_profit
    
    def run(self, prices, signals) -> BacktestResult:
        """运行回测"""
        if hasattr(prices, 'iloc'):
            prices = prices.values
        cash = self.initial_capital
        shares = 0
        trades = []
        portfolio_values = []
        
        for i in range(len(signals)):
            price = prices[i] if isinstance(prices, np.ndarray) else prices.iloc[i]
            signal = signals[i]
            date = str(i)
            
            # 买入信号
            if signal == 1 and shares == 0:
                shares = int(cash / price * (1 - self.transaction_cost))
                cash -= shares * price * (1 + self.transaction_cost)
                trades.append(Trade(date, 'buy', price, shares))
            
            # 卖出信号
            elif signal == -1 and shares > 0:
                cash += shares * price * (1 - self.transaction_cost)
                trades.append(Trade(date, 'sell', price, shares))
                shares = 0
            
            # 止损/止盈
            if shares > 0:
                position_value = shares * price
                entry_price = trades[-1].price if trades else price
                ret = (price - entry_price) / entry_price
                
                if ret <= -self.stop_loss:
                    cash += shares * price * (1 - self.transaction_cost)
                    trades.append(Trade(date, 'stop_loss', price, shares))
                    shares = 0
                elif ret >= self.take_profit:
                    cash += shares * price * (1 - self.transaction_cost)
                    trades.append(Trade(date, 'take_profit', price, shares))
                    shares = 0
            
            # 记录组合价值
            portfolio_value = cash + shares * price
            portfolio_values.append(portfolio_value)
        
        # 平仓
        if shares > 0:
            cash += shares * (prices[-1] if isinstance(prices, np.ndarray) else prices.iloc[-1]) * (1 - self.transaction_cost)
        
        # 计算指标
        final_value = cash
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252)
        
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (peak - portfolio_values) / peak
        max_drawdown = np.max(drawdown)
        
        # 胜率
        wins = sum(1 for t in trades if t.action == 'sell' and 
                   any(trades[i+1].action == 'buy' and 
                       trades[i+1].price > t.price for i in range(len(trades)-1) if trades[i].action == 'sell'))
        win_rate = wins / max(len([t for t in trades if t.action == 'sell']), 1)
        
        return BacktestResult(total_return, sharpe_ratio, max_drawdown, win_rate, trades)

def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """评估预测结果"""
    accuracy = np.mean(y_true == y_pred)
    
    tp = np.sum((y_true == 1) & (y_pred == 1))
    fp = np.sum((y_true == 0) & (y_pred == 1))
    fn = np.sum((y_true == 1) & (y_pred == 0))
    
    precision = tp / (tp + fp + 1e-10)
    recall = tp / (tp + fn + 1e-10)
    f1 = 2 * precision * recall / (precision + recall + 1e-10)
    
    return {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1': f1}
