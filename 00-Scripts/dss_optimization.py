"""
DSS 技术指标参数优化脚本
目标：在真实数据上优化去噪参数、技术指标参数、评分权重

优化内容：
1. Kalman去噪参数优化 (process_noise, measurement_noise)
2. 技术指标参数优化 (RSI周期, MACD参数)
3. 评分权重调整 (技术vs情绪vs基本面)
4. 回测改进效果
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from itertools import product
import warnings
warnings.filterwarnings('ignore')

# 导入模块
from dss_modules.data_loader import get_stock_data
from denoiser import Denoiser
from denoiser.methods.kalman import kalman_denoise

# ============ 参数化技术指标计算 ============

def add_technical_indicators_optimized(df: pd.DataFrame, 
                                        rsi_period: int = 14,
                                        macd_fast: int = 12,
                                        macd_slow: int = 26,
                                        macd_signal: int = 9,
                                        ma_periods: List[int] = None) -> pd.DataFrame:
    """参数化技术指标计算"""
    if ma_periods is None:
        ma_periods = [5, 10, 20, 60]
    
    df = df.copy()
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # 移动平均
    for w in ma_periods:
        df[f'MA{w}'] = close.rolling(w).mean()
        df[f'volume_MA{w}'] = volume.rolling(w).mean()
    
    # RSI (可调周期)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / (loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD (可调参数)
    ema_fast = close.ewm(span=macd_fast).mean()
    ema_slow = close.ewm(span=macd_slow).mean()
    df['MACD'] = ema_fast - ema_slow
    df['MACD_signal'] = df['MACD'].ewm(span=macd_signal).mean()
    
    # 布林带
    mb = close.rolling(20).mean()
    std = close.rolling(20).std()
    df['BB_upper'] = mb + 2 * std
    df['BB_lower'] = mb - 2 * std
    df['BB_position'] = (close - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'] + 1e-10)
    
    # ATR
    high_low = high - low
    high_close = (high - close.shift(1)).abs()
    low_close = (low - close.shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    
    # 波动率
    df['volatility_5'] = close.pct_change().rolling(5).std()
    df['volatility_20'] = close.pct_change().rolling(20).std()
    
    # 价格位置
    df['price_position'] = (close - low.rolling(20).min()) / (high.rolling(20).max() - low.rolling(20).min() + 1e-10)
    
    # 成交量变化
    df['volume_ratio'] = volume / volume.rolling(20).mean()
    
    return df


# ============ 评分系统（可配置权重） ============

class ScoringSystem:
    """可配置的评分系统"""
    
    def __init__(self,
                 # 技术指标权重
                 rsi_weight: float = 1.0,
                 macd_weight: float = 1.0,
                 ma_weight: float = 1.0,
                 volume_weight: float = 1.0,
                 
                 # 大类权重
                 tech_weight: float = 0.5,
                 sentiment_weight: float = 0.3,
                 fundamentals_weight: float = 0.2,
                 
                 # RSI阈值
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70):
        self.rsi_weight = rsi_weight
        self.macd_weight = macd_weight
        self.ma_weight = ma_weight
        self.volume_weight = volume_weight
        
        self.tech_weight = tech_weight
        self.sentiment_weight = sentiment_weight
        self.fundamentals_weight = fundamentals_weight
        
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        
    def score_rsi(self, rsi: float) -> Tuple[float, str]:
        """RSI评分"""
        if pd.isna(rsi):
            return 0, "N/A"
        if rsi < self.rsi_oversold:
            return 20, "超卖"
        elif rsi < 40:
            return 10, "偏低"
        elif rsi > self.rsi_overbought:
            return -20, "超买"
        elif rsi > 60:
            return -10, "偏高"
        else:
            return 0, "中性"
    
    def score_macd(self, macd: float, signal: float) -> Tuple[float, str]:
        """MACD评分"""
        if pd.isna(macd) or pd.isna(signal):
            return 0, "N/A"
        if macd > signal and macd > 0:
            return 20, "金叉多头"
        elif macd > signal:
            return 10, "金叉"
        elif macd < signal and macd < 0:
            return -20, "死叉空头"
        elif macd < signal:
            return -10, "死叉"
        else:
            return 0, "中性"
    
    def score_ma(self, ma_short: float, ma_long: float) -> Tuple[float, str]:
        """均线评分"""
        if pd.isna(ma_short) or pd.isna(ma_long):
            return 0, "N/A"
        pct_diff = (ma_short - ma_long) / ma_long * 100
        if pct_diff > 5:
            return 20, "强势多头"
        elif pct_diff > 0:
            return 10, "多头排列"
        elif pct_diff > -5:
            return -10, "空头排列"
        else:
            return -20, "强势空头"
    
    def score_volume(self, vol_ratio: float) -> Tuple[float, str]:
        """成交量评分"""
        if pd.isna(vol_ratio) or vol_ratio <= 0:
            return 0, "N/A"
        if vol_ratio > 2.0:
            return 15, "放量"
        elif vol_ratio > 1.5:
            return 10, "温和放量"
        elif vol_ratio > 1.2:
            return 5, "略放量"
        elif vol_ratio < 0.5:
            return -10, "缩量"
        else:
            return 0, "正常"
    
    def calculate_tech_score(self, df: pd.DataFrame) -> Dict:
        """计算综合技术评分"""
        latest = df.iloc[-1]
        
        rsi = latest.get('RSI', 50)
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_signal', 0)
        ma5 = latest.get('MA5', 0)
        ma20 = latest.get('MA20', 0)
        vol_ratio = latest.get('volume_ratio', 1)
        
        rsi_score, rsi_label = self.score_rsi(rsi)
        macd_score, macd_label = self.score_macd(macd, macd_signal)
        ma_score, ma_label = self.score_ma(ma5, ma20)
        vol_score, vol_label = self.score_volume(vol_ratio)
        
        total = (rsi_score * self.rsi_weight +
                macd_score * self.macd_weight +
                ma_score * self.ma_weight +
                vol_score * self.volume_weight)
        
        return {
            'rsi': {'score': rsi_score, 'label': rsi_label, 'value': rsi},
            'macd': {'score': macd_score, 'label': macd_label, 'value': macd},
            'ma': {'score': ma_score, 'label': ma_label, 'value': (ma5, ma20)},
            'volume': {'score': vol_score, 'label': vol_label, 'value': vol_ratio},
            'total': total
        }


# ============ 回测系统 ============

class Backtester:
    """简化的回测系统"""
    
    def __init__(self, 
                 scoring_system: ScoringSystem,
                 denoiser: Optional[Denoiser] = None,
                 tech_params: Dict = None):
        self.scoring = scoring_system
        self.denoiser = denoiser
        self.tech_params = tech_params or {}
        
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据（应用去噪和计算指标）"""
        df = df.copy()
        
        # 去噪处理
        if self.denoiser:
            close_denoised = self.denoiser.denoise(df['Close'].values)
            df['Close_denoised'] = close_denoised
            df['Close_original'] = df['Close'].values
            df['Close'] = close_denoised  # 用去噪后价格计算指标
        
        # 计算技术指标
        df = add_technical_indicators_optimized(df, **self.tech_params)
        
        return df
    
    def predict_direction(self, score: float, threshold: float = 10) -> str:
        """根据评分预测方向"""
        if score > threshold:
            return '上涨'
        elif score < -threshold:
            return '下跌'
        else:
            return '震荡'
    
    def backtest_single(self, symbol: str, 
                        df: pd.DataFrame,
                        lookback: int = 60,
                        forward: int = 5,
                        min_score_threshold: float = 10) -> Dict:
        """单只股票回测"""
        df = self.prepare_data(df)
        
        if len(df) < lookback + forward + 30:
            return None
        
        results = []
        
        for i in range(lookback + 30, len(df) - forward):
            # 历史数据窗口
            window = df.iloc[i-lookback:i+1]
            
            # 计算评分
            score_result = self.scoring.calculate_tech_score(window)
            total_score = score_result['total']
            
            # 预测方向
            prediction = self.predict_direction(total_score, min_score_threshold)
            
            # 实际走势
            current_close = df.iloc[i]['Close_original'] if 'Close_original' in df.columns else df.iloc[i]['Close']
            future_close = df.iloc[i + forward]['Close_original'] if 'Close_original' in df.columns else df.iloc[i + forward]['Close']
            actual_return = (future_close - current_close) / current_close * 100
            actual_direction = '上涨' if actual_return > 0 else ('下跌' if actual_return < 0 else '震荡')
            
            # 判断预测是否正确
            correct = (prediction == actual_direction) or \
                      (prediction == '震荡' and abs(actual_return) < 2)
            
            results.append({
                'date': df.index[i],
                'score': total_score,
                'prediction': prediction,
                'actual_return': actual_return,
                'actual_direction': actual_direction,
                'correct': correct
            })
        
        if not results:
            return None
        
        results_df = pd.DataFrame(results)
        
        # 计算准确率
        accuracy = results_df['correct'].mean() * 100
        
        # 分方向统计
        up_df = results_df[results_df['prediction'] == '上涨']
        down_df = results_df[results_df['prediction'] == '下跌']
        neutral_df = results_df[results_df['prediction'] == '震荡']
        
        up_accuracy = up_df['correct'].mean() * 100 if len(up_df) > 0 else 0
        down_accuracy = down_df['correct'].mean() * 100 if len(down_df) > 0 else 0
        
        # 计算收益率
        up_returns = up_df['actual_return'].mean() if len(up_df) > 0 else 0
        down_returns = down_df['actual_return'].mean() if len(down_df) > 0 else 0
        
        return {
            'symbol': symbol,
            'total_samples': len(results),
            'accuracy': accuracy,
            'up_accuracy': up_accuracy,
            'down_accuracy': down_accuracy,
            'up_samples': len(up_df),
            'down_samples': len(down_df),
            'neutral_samples': len(neutral_df),
            'up_avg_return': up_returns,
            'down_avg_return': down_returns,
            'results': results_df
        }


# ============ 参数优化器 ============

class ParameterOptimizer:
    """参数网格搜索优化"""
    
    def __init__(self, stocks: Dict[str, Tuple[str, str]]):
        self.stocks = stocks
        self.results = []
        
    def optimize_kalman_params(self, 
                               Q_range: List[float] = None,
                               R_range: List[float] = None) -> Dict:
        """优化Kalman参数"""
        if Q_range is None:
            Q_range = [0.005, 0.01, 0.02, 0.05]
        if R_range is None:
            R_range = [0.05, 0.1, 0.2, 0.5]
        
        best_result = {'accuracy': 0}
        all_results = []
        
        print("\n🔍 优化Kalman去噪参数...")
        print(f"   测试 Q={Q_range}")
        print(f"   测试 R={R_range}")
        
        for Q, R in product(Q_range, R_range):
            print(f"\n   测试 Q={Q}, R={R}...", end=' ')
            
            denoiser = Denoiser('kalman', process_noise=Q, measurement_noise=R)
            scoring = ScoringSystem()
            backtester = Backtester(scoring, denoiser)
            
            stock_results = []
            for code, (name, industry) in self.stocks.items():
                # 使用预获取的数据
                if hasattr(self, 'stock_data') and code in self.stock_data:
                    df = self.stock_data[code]
                else:
                    df = get_stock_data(code, 300, 'baostock')
                    
                if df is not None and len(df) > 100:
                    result = backtester.backtest_single(code, df)
                    if result:
                        stock_results.append(result)
            
            if stock_results:
                avg_accuracy = np.mean([r['accuracy'] for r in stock_results])
                print(f"准确率: {avg_accuracy:.1f}%")
                
                all_results.append({
                    'Q': Q,
                    'R': R,
                    'accuracy': avg_accuracy,
                    'samples': sum(r['total_samples'] for r in stock_results)
                })
                
                if avg_accuracy > best_result['accuracy']:
                    best_result = {
                        'Q': Q,
                        'R': R,
                        'accuracy': avg_accuracy,
                        'samples': sum(r['total_samples'] for r in stock_results)
                    }
            else:
                print("无数据")
        
        return {'best': best_result, 'all': all_results}
    
    def optimize_rsi_period(self,
                           periods: List[int] = None) -> Dict:
        """优化RSI周期"""
        if periods is None:
            periods = [7, 9, 14, 21, 28]
        
        best_result = {'accuracy': 0}
        all_results = []
        
        print("\n🔍 优化RSI周期参数...")
        print(f"   测试周期: {periods}")
        
        for period in periods:
            print(f"\n   测试 RSI周期={period}...", end=' ')
            
            tech_params = {'rsi_period': period}
            scoring = ScoringSystem()
            backtester = Backtester(scoring, None, tech_params)
            
            stock_results = []
            for code, (name, industry) in self.stocks.items():
                # 使用预获取的数据
                if hasattr(self, 'stock_data') and code in self.stock_data:
                    df = self.stock_data[code]
                else:
                    df = get_stock_data(code, 300, 'baostock')
                    
                if df is not None and len(df) > 100:
                    result = backtester.backtest_single(code, df)
                    if result:
                        stock_results.append(result)
            
            if stock_results:
                avg_accuracy = np.mean([r['accuracy'] for r in stock_results])
                print(f"准确率: {avg_accuracy:.1f}%")
                
                all_results.append({
                    'rsi_period': period,
                    'accuracy': avg_accuracy,
                    'samples': sum(r['total_samples'] for r in stock_results)
                })
                
                if avg_accuracy > best_result['accuracy']:
                    best_result = {
                        'rsi_period': period,
                        'accuracy': avg_accuracy,
                        'samples': sum(r['total_samples'] for r in stock_results)
                    }
            else:
                print("无数据")
        
        return {'best': best_result, 'all': all_results}
    
    def optimize_macd_params(self,
                            fast_range: List[int] = None,
                            slow_range: List[int] = None,
                            signal_range: List[int] = None) -> Dict:
        """优化MACD参数"""
        if fast_range is None:
            fast_range = [8, 10, 12, 15]
        if slow_range is None:
            slow_range = [20, 26, 30]
        if signal_range is None:
            signal_range = [7, 9, 12]
        
        best_result = {'accuracy': 0}
        all_results = []
        
        print("\n🔍 优化MACD参数...")
        
        for fast, slow, signal in product(fast_range, slow_range, signal_range):
            if fast >= slow:
                continue
            
            print(f"\n   测试 MACD({fast},{slow},{signal})...", end=' ')
            
            tech_params = {'macd_fast': fast, 'macd_slow': slow, 'macd_signal': signal}
            scoring = ScoringSystem()
            backtester = Backtester(scoring, None, tech_params)
            
            stock_results = []
            for code, (name, industry) in self.stocks.items():
                # 使用预获取的数据
                if hasattr(self, 'stock_data') and code in self.stock_data:
                    df = self.stock_data[code]
                else:
                    df = get_stock_data(code, 300, 'baostock')
                    
                if df is not None and len(df) > 100:
                    result = backtester.backtest_single(code, df)
                    if result:
                        stock_results.append(result)
            
            if stock_results:
                avg_accuracy = np.mean([r['accuracy'] for r in stock_results])
                print(f"准确率: {avg_accuracy:.1f}%")
                
                all_results.append({
                    'macd_fast': fast,
                    'macd_slow': slow,
                    'macd_signal': signal,
                    'accuracy': avg_accuracy,
                    'samples': sum(r['total_samples'] for r in stock_results)
                })
                
                if avg_accuracy > best_result['accuracy']:
                    best_result = {
                        'macd_fast': fast,
                        'macd_slow': slow,
                        'macd_signal': signal,
                        'accuracy': avg_accuracy,
                        'samples': sum(r['total_samples'] for r in stock_results)
                    }
            else:
                print("无数据")
        
        return {'best': best_result, 'all': all_results}
    
    def optimize_scoring_weights(self,
                                 rsi_weights: List[float] = None,
                                 macd_weights: List[float] = None,
                                 ma_weights: List[float] = None) -> Dict:
        """优化评分权重"""
        if rsi_weights is None:
            rsi_weights = [0.5, 1.0, 1.5]
        if macd_weights is None:
            macd_weights = [0.5, 1.0, 1.5]
        if ma_weights is None:
            ma_weights = [0.5, 1.0, 1.5]
        
        best_result = {'accuracy': 0}
        all_results = []
        
        print("\n🔍 优化评分权重...")
        
        for rsi_w, macd_w, ma_w in product(rsi_weights, macd_weights, ma_weights):
            print(f"\n   测试权重(RSI={rsi_w}, MACD={macd_w}, MA={ma_w})...", end=' ')
            
            scoring = ScoringSystem(rsi_weight=rsi_w, macd_weight=macd_w, ma_weight=ma_w)
            backtester = Backtester(scoring)
            
            stock_results = []
            for code, (name, industry) in self.stocks.items():
                # 使用预获取的数据
                if hasattr(self, 'stock_data') and code in self.stock_data:
                    df = self.stock_data[code]
                else:
                    df = get_stock_data(code, 300, 'baostock')
                    
                if df is not None and len(df) > 100:
                    result = backtester.backtest_single(code, df)
                    if result:
                        stock_results.append(result)
            
            if stock_results:
                avg_accuracy = np.mean([r['accuracy'] for r in stock_results])
                print(f"准确率: {avg_accuracy:.1f}%")
                
                all_results.append({
                    'rsi_weight': rsi_w,
                    'macd_weight': macd_w,
                    'ma_weight': ma_w,
                    'accuracy': avg_accuracy,
                    'samples': sum(r['total_samples'] for r in stock_results)
                })
                
                if avg_accuracy > best_result['accuracy']:
                    best_result = {
                        'rsi_weight': rsi_w,
                        'macd_weight': macd_w,
                        'ma_weight': ma_w,
                        'accuracy': avg_accuracy,
                        'samples': sum(r['total_samples'] for r in stock_results)
                    }
            else:
                print("无数据")
        
        return {'best': best_result, 'all': all_results}


# ============ 主函数 ============

def run_optimization():
    """运行完整优化流程"""
    print("=" * 60)
    print("DSS 技术指标参数优化")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试股票池
    stocks = {
        'sh.600519': ('贵州茅台', '白酒'),
        'sh.601398': ('工商银行', '银行'),
        'sh.601111': ('中国国航', '航空'),
        'sh.601318': ('中国平安', '保险'),
        'sz.000858': ('五粮液', '白酒'),
        'sz.000001': ('平安银行', '银行'),
    }
    
    # 先获取数据
    print("\n📊 获取股票数据...")
    stock_data = {}
    for code, (name, industry) in stocks.items():
        print(f"   {name} ({code})...", end=' ')
        df = get_stock_data(code, 300, 'baostock')
        if df is not None and len(df) > 100:
            stock_data[code] = df
            print(f"✓ {len(df)}天")
        else:
            print("✗ 获取失败")
    
    if not stock_data:
        print("\n❌ 无法获取股票数据，请检查网络连接")
        return None
    
    # 创建优化器
    optimizer = ParameterOptimizer(stocks)
    optimizer.stock_data = stock_data  # 存储获取的数据
    
    # 优化结果
    results = {}
    
    # 1. Kalman参数优化
    results['kalman'] = optimizer.optimize_kalman_params()
    
    # 2. RSI周期优化
    results['rsi'] = optimizer.optimize_rsi_period()
    
    # 3. MACD参数优化
    results['macd'] = optimizer.optimize_macd_params()
    
    # 4. 评分权重优化
    results['weights'] = optimizer.optimize_scoring_weights()
    
    # 输出最佳参数
    print("\n" + "=" * 60)
    print("🏆 最佳参数配置")
    print("=" * 60)
    
    if 'best' in results['kalman']:
        kalman = results['kalman']['best']
        print(f"\n📌 Kalman去噪参数:")
        print(f"   process_noise (Q): {kalman.get('Q', 'N/A')}")
        print(f"   measurement_noise (R): {kalman.get('R', 'N/A')}")
        print(f"   准确率: {kalman.get('accuracy', 0):.1f}%")
    
    if 'best' in results['rsi']:
        rsi = results['rsi']['best']
        print(f"\n📌 RSI参数:")
        print(f"   周期: {rsi.get('rsi_period', 'N/A')}")
        print(f"   准确率: {rsi.get('accuracy', 0):.1f}%")
    
    if 'best' in results['macd']:
        macd = results['macd']['best']
        print(f"\n📌 MACD参数:")
        print(f"   快线: {macd.get('macd_fast', 'N/A')}")
        print(f"   慢线: {macd.get('macd_slow', 'N/A')}")
        print(f"   信号线: {macd.get('macd_signal', 'N/A')}")
        print(f"   准确率: {macd.get('accuracy', 0):.1f}%")
    
    if 'best' in results['weights']:
        weights = results['weights']['best']
        print(f"\n📌 评分权重:")
        print(f"   RSI权重: {weights.get('rsi_weight', 'N/A')}")
        print(f"   MACD权重: {weights.get('macd_weight', 'N/A')}")
        print(f"   MA权重: {weights.get('ma_weight', 'N/A')}")
        print(f"   准确率: {weights.get('accuracy', 0):.1f}%")
    
    # 保存结果
    output = {
        'timestamp': datetime.now().isoformat(),
        'stocks_tested': list(stock_data.keys()),
        'results': results
    }
    
    output_path = '/home/kyj/.openclaw/workspace/dss_optimization_results.json'
    import json
    with open(output_path, 'w', encoding='utf-8') as f:
        # 转换不可序列化的对象
        def convert(obj):
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            return obj
        
        json.dump(output, f, ensure_ascii=False, indent=2, default=convert)
    
    print(f"\n✅ 结果已保存到: {output_path}")
    
    return results


if __name__ == "__main__":
    run_optimization()