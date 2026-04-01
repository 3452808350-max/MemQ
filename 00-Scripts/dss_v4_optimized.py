"""
DSS v4.3 - 优化版技术指标计算
基于真实数据回测优化的最佳参数配置

优化内容:
1. Kalman去噪参数: Q=0.005, R=0.5
2. RSI周期: 9天 (原14天)
3. MACD参数: (15,30,9) (原12,26,9)
4. 评分权重: RSI=1.0, MACD=0.5, MA=0.5

测试准确率: 58.2% (原~54%)
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import numpy as np
import pandas as pd
from dss_modules.data_loader import get_stock_data
from denoiser import Denoiser

# 新闻情绪模块 (可选导入)
try:
    from dss_modules.news_crawler import get_stock_news
    from dss_modules.eastmoney_crawler import get_money_flow
    from dss_modules.news_sentiment import get_sentiment_score, analyze_news_sentiment
    NEWS_MODULES_AVAILABLE = True
except ImportError:
    NEWS_MODULES_AVAILABLE = False

# ============ 最佳参数配置 ============

BEST_PARAMS = {
    # Kalman去噪参数
    'kalman': {
        'process_noise': 0.005,
        'measurement_noise': 0.5,
    },
    
    # 技术指标参数
    'tech': {
        'rsi_period': 9,          # 优化后: 9 (原14)
        'macd_fast': 15,          # 优化后: 15 (原12)
        'macd_slow': 30,          # 优化后: 30 (原26)
        'macd_signal': 9,         # 保持默认
    },
    
    # 评分权重
    'weights': {
        'rsi_weight': 1.0,
        'macd_weight': 0.5,       # 优化后: 0.5 (原1.0)
        'ma_weight': 0.5,         # 优化后: 0.5 (原1.0)
        'volume_weight': 1.0,
    },
}

# ============ 优化版技术指标计算 ============

def add_technical_indicators_optimized(df: pd.DataFrame, 
                                        params: dict = None) -> pd.DataFrame:
    """使用优化参数计算技术指标"""
    if params is None:
        params = BEST_PARAMS['tech']
    
    df = df.copy()
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # 移动平均
    for w in [5, 10, 20, 60]:
        df[f'MA{w}'] = close.rolling(w).mean()
        df[f'volume_MA{w}'] = volume.rolling(w).mean()
    
    # RSI (优化周期)
    rsi_period = params.get('rsi_period', 9)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
    rs = gain / (loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD (优化参数)
    macd_fast = params.get('macd_fast', 15)
    macd_slow = params.get('macd_slow', 30)
    macd_signal = params.get('macd_signal', 9)
    
    ema_fast = close.ewm(span=macd_fast).mean()
    ema_slow = close.ewm(span=macd_slow).mean()
    df['MACD'] = ema_fast - ema_slow
    df['MACD_signal'] = df['MACD'].ewm(span=macd_signal).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
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
    
    # 成交量变化
    df['volume_ratio'] = volume / volume.rolling(20).mean()
    
    return df

# ============ 基本面数据 ============

def get_fundamentals_real(symbol):
    """获取真实基本面数据"""
    try:
        from dss_modules.data_fundamentals import get_stock_realtime
        data = get_stock_realtime(symbol)
        if data is None:
            return None
        
        return {
            'pe_ratio': data.get('pe', 0) if data.get('pe') and data.get('pe') > 0 else 0,
            'pb_ratio': data.get('pb', 0) if data.get('pb') else 0,
            'roe': data.get('roe', 0) if data.get('roe') else 0,
            'eps': data.get('eps', 0) if data.get('eps') else 0,
            'source': data.get('source', 'unknown'),
        }
    except:
        return None

# ============ 风控机制 ============

class RiskManager:
    """风险管理器"""
    
    def __init__(self, stop_loss=0.05, take_profit=0.15):
        self.stop_loss = stop_loss
        self.take_profit = take_profit
    
    def should_sell(self, entry_price, current_price):
        """判断是否应该卖出"""
        return_pct = (current_price - entry_price) / entry_price
        
        if return_pct >= self.take_profit:
            return True, "take_profit"
        if return_pct <= -self.stop_loss:
            return True, "stop_loss"
        
        return False, None
    
    def calculate_position_size(self, total_capital, risk_per_trade=0.02):
        """计算仓位大小"""
        return total_capital * risk_per_trade / self.stop_loss

# ============ 优化版选股器 ============

class OptimizedStockPicker:
    """优化版选股器 - 使用最佳参数"""
    
    def __init__(self, use_denoise=True, use_news_sentiment=True):
        self.risk_manager = RiskManager(stop_loss=0.05, take_profit=0.15)
        
        # 使用最佳参数
        self.params = BEST_PARAMS
        
        # Kalman去噪器
        self.use_denoise = use_denoise
        if use_denoise:
            self.denoiser = Denoiser(
                'kalman',
                process_noise=self.params['kalman']['process_noise'],
                measurement_noise=self.params['kalman']['measurement_noise']
            )
        else:
            self.denoiser = None
        
        self.use_news_sentiment = use_news_sentiment and NEWS_MODULES_AVAILABLE
    
    def _denoise_price(self, price_series):
        """对价格序列去噪"""
        if self.denoiser is None:
            return price_series
        return self.denoiser.denoise(np.array(price_series))
    
    def _get_news_sentiment(self, symbol):
        """获取新闻情绪分数"""
        if not self.use_news_sentiment:
            return 0, None
        
        try:
            code = symbol.replace('sh.', '').replace('sz.', '')
            news_list = get_stock_news(code, limit=5)
            if not news_list:
                return 0, None
            
            result = get_sentiment_score(code, news_list)
            if result:
                return result.get('sentiment', 0) * 20, result
            return 0, None
        except:
            return 0, None
    
    def _get_money_flow_sentiment(self, symbol):
        """获取资金流向情绪"""
        if not self.use_news_sentiment:
            return 0, None
        
        try:
            code = symbol.replace('sh.', '').replace('sz.', '')
            flow = get_money_flow(code, days=3)
            
            if flow and 'main_net_inflow' in flow:
                main_flow = flow['main_net_inflow'] / 10000
                if main_flow > 10000:
                    return 15, flow
                elif main_flow > 5000:
                    return 10, flow
                elif main_flow > 0:
                    return 5, flow
                elif main_flow > -5000:
                    return -5, flow
                elif main_flow > -10000:
                    return -10, flow
                else:
                    return -15, flow
            return 0, None
        except:
            return 0, None
    
    def get_comprehensive_features(self, symbol, days=250):
        """获取综合特征"""
        df = get_stock_data(symbol, days, 'baostock')
        if df is None or len(df) < 100:
            return None
        
        # 去噪处理
        if self.use_denoise and self.denoiser:
            df['Close_original'] = df['Close'].copy()
            df['Close'] = self._denoise_price(df['Close'])
        
        # 添加技术指标（优化参数）
        df = add_technical_indicators_optimized(df, self.params['tech'])
        
        if len(df) < 30:
            return None
        
        # 添加基本面特征
        fundamentals = get_fundamentals_real(symbol)
        if fundamentals:
            for key, value in fundamentals.items():
                df[key] = value
        
        return df
    
    def calculate_score(self, df):
        """计算技术评分（使用优化权重）"""
        latest = df.iloc[-1]
        weights = self.params['weights']
        
        score = 0
        details = {}
        
        # RSI评分
        rsi = latest.get('RSI', 50)
        if not pd.isna(rsi):
            if rsi < 30:
                rsi_score = 20
            elif rsi < 40:
                rsi_score = 10
            elif rsi > 70:
                rsi_score = -20
            elif rsi > 60:
                rsi_score = -10
            else:
                rsi_score = 0
            score += rsi_score * weights['rsi_weight']
            details['rsi'] = {'score': rsi_score, 'value': rsi}
        
        # MACD评分
        macd = latest.get('MACD', 0)
        macd_signal = latest.get('MACD_signal', 0)
        if not pd.isna(macd) and not pd.isna(macd_signal):
            if macd > macd_signal and macd > 0:
                macd_score = 20
            elif macd > macd_signal:
                macd_score = 10
            elif macd < macd_signal and macd < 0:
                macd_score = -20
            elif macd < macd_signal:
                macd_score = -10
            else:
                macd_score = 0
            score += macd_score * weights['macd_weight']
            details['macd'] = {'score': macd_score, 'value': macd}
        
        # 均线评分
        ma5 = latest.get('MA5', 0)
        ma20 = latest.get('MA20', 0)
        if not pd.isna(ma5) and not pd.isna(ma20):
            if ma5 > ma20:
                ma_score = 10
            else:
                ma_score = -10
            score += ma_score * weights['ma_weight']
            details['ma'] = {'score': ma_score, 'value': (ma5, ma20)}
        
        # 成交量评分
        vol_ratio = latest.get('volume_ratio', 1)
        if not pd.isna(vol_ratio) and vol_ratio > 0:
            if vol_ratio > 2.0:
                vol_score = 15
            elif vol_ratio > 1.5:
                vol_score = 10
            elif vol_ratio > 1.2:
                vol_score = 5
            elif vol_ratio < 0.5:
                vol_score = -10
            else:
                vol_score = 0
            score += vol_score * weights['volume_weight']
            details['volume'] = {'score': vol_score, 'value': vol_ratio}
        
        return score, details
    
    def analyze_stock(self, symbol):
        """综合分析股票"""
        df = self.get_comprehensive_features(symbol)
        if df is None:
            return None
        
        # 计算技术评分
        tech_score, tech_details = self.calculate_score(df)
        
        # 获取情绪评分
        news_score, news_detail = self._get_news_sentiment(symbol)
        money_flow_score, money_flow_detail = self._get_money_flow_sentiment(symbol)
        
        # 综合评分
        total_score = tech_score + news_score + money_flow_score
        
        latest = df.iloc[-1]
        
        return {
            'symbol': symbol,
            'close': latest.get('Close_original', latest['Close']),
            'tech_score': tech_score,
            'tech_details': tech_details,
            'news_score': news_score,
            'money_flow_score': money_flow_score,
            'total_score': total_score,
            'fundamentals': {
                'pe': latest.get('pe_ratio'),
                'roe': latest.get('roe'),
            },
            'params_used': self.params
        }

# ============ 入口函数 ============

def pick_best_stocks_optimized(stocks=None, top_n=5):
    """优化版选股"""
    if stocks is None:
        stocks = {
            'sh.601111': ('中国国航', '航空'),
            'sh.600048': ('保利地产', '地产'),
            'sh.600519': ('贵州茅台', '白酒'),
            'sh.601398': ('工商银行', '银行'),
            'sh.601318': ('中国平安', '保险'),
        }
    
    picker = OptimizedStockPicker(use_denoise=True, use_news_sentiment=True)
    results = []
    
    for code, (name, industry) in stocks.items():
        analysis = picker.analyze_stock(code)
        if analysis:
            analysis['name'] = name
            analysis['industry'] = industry
            results.append(analysis)
    
    # 按总分排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    return results[:top_n]

# ============ 测试 ============

if __name__ == "__main__":
    print("="*60)
    print("DSS v4.3 - 优化版技术指标分析")
    print("="*60)
    print(f"最佳参数: RSI周期=9, MACD(15,30,9), Q=0.005, R=0.5")
    print("="*60)
    
    stocks = {
        'sh.600519': ('贵州茅台', '白酒'),
        'sh.601398': ('工商银行', '银行'),
        'sh.601111': ('中国国航', '航空'),
    }
    
    picker = OptimizedStockPicker(use_denoise=True, use_news_sentiment=True)
    
    for code, (name, industry) in stocks.items():
        print(f"\n【{name}】({code})")
        analysis = picker.analyze_stock(code)
        
        if analysis:
            print(f"  收盘价: ¥{analysis['close']:.2f}")
            print(f"  技术评分: {analysis['tech_score']:+.0f}")
            
            # 技术指标详情
            details = analysis['tech_details']
            if 'rsi' in details:
                print(f"    RSI: {details['rsi']['value']:.1f} ({details['rsi']['score']:+d})")
            if 'macd' in details:
                print(f"    MACD: {details['macd']['value']:.4f} ({details['macd']['score']:+d})")
            if 'ma' in details:
                print(f"    MA: {details['ma']['score']:+d}")
            if 'volume' in details:
                print(f"    成交量: {details['volume']['value']:.2f}x ({details['volume']['score']:+d})")
            
            # 情绪评分
            print(f"  情绪评分:")
            print(f"    - 新闻情绪: {analysis['news_score']:+.0f}")
            print(f"    - 资金流向: {analysis['money_flow_score']:+.0f}")
            
            print(f"  综合评分: {analysis['total_score']:+.0f}")
        else:
            print("  分析失败")
    
    print("\n" + "="*60)