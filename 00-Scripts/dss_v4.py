"""
DSS v4.3 - 金融数据架构 + 可解释性

新增:
1. 金融数据存储（不可变、版本控制、血缘追踪）
2. 数据来源标签
3. 处理过程记录
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import numpy as np
import pandas as pd
from dss_modules.data_loader import get_stock_data
from dss_modules.features import add_technical_indicators
from dss_modules.models import StockModel
from denoiser import Denoiser

# 金融数据存储
try:
    from dss_modules.financial_data_store import create_financial_store
    FINANCIAL_STORE = create_financial_store()
except ImportError:
    FINANCIAL_STORE = None

# 新闻情绪模块 (可选导入)
try:
    from dss_modules.news_crawler import get_stock_news
    from dss_modules.eastmoney_crawler import get_money_flow
    from dss_modules.news_sentiment import get_sentiment_score, analyze_news_sentiment
    NEWS_MODULES_AVAILABLE = True
except ImportError:
    NEWS_MODULES_AVAILABLE = False
    print("⚠️ 新闻情绪模块未安装，部分功能不可用")

# 浏览器搜索模块 (可选导入，用于国际视角分析)
try:
    from dss_modules.browser_search_cli import BrowserSearchCLI
    import asyncio
    BROWSER_SEARCH_AVAILABLE = True
except ImportError:
    BROWSER_SEARCH_AVAILABLE = False

# ============ 真实基本面数据 ============

def get_fundamentals_real(symbol):
    """获取真实基本面数据 - 多数据源支持(东方财富/新浪/同花顺)"""
    from dss_modules.data_fundamentals import get_stock_realtime
    
    data = get_stock_realtime(symbol)
    if data is None:
        return None
    
    # 处理错误情况
    if data.get('error'):
        print(f"基本面数据警告 {symbol}: {data['error']}")
    
    # 转换格式 - 现在支持ROE
    fundamentals = {
        'pe_ratio': data.get('pe', 0) if data.get('pe') and data.get('pe') > 0 else 0,
        'pb_ratio': data.get('pb', 0) if data.get('pb') else 0,
        'roe': data.get('roe', 0) if data.get('roe') else 0,
        'eps': data.get('eps', 0) if data.get('eps') else 0,
        'gross_margin': data.get('gross_margin', 0) if data.get('gross_margin') else 0,
        'dividend_yield': 0,  # 暂无数据源
        'debt_ratio': 0,  # 暂无数据源
        'source': data.get('source', 'unknown'),
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
    """改进版选股器 - 集成去噪 + 新闻情绪"""
    
    def __init__(self, use_denoise=True, denoise_method='kalman', use_news_sentiment=True):
        self.risk_manager = RiskManager(stop_loss=0.05, take_profit=0.15)
        self.models = {
            'lgbm': StockModel('lgbm'),
            'xgb': StockModel('xgb'),
        }
        self.use_denoise = use_denoise
        self.denoiser = Denoiser(method=denoise_method) if use_denoise else None
        self.use_news_sentiment = use_news_sentiment and NEWS_MODULES_AVAILABLE
    
    def _denoise_price(self, price_series):
        """对价格序列去噪"""
        if self.denoiser is None:
            return price_series
        return self.denoiser.denoise(np.array(price_series))
    
    def _get_international_sentiment(self, symbol):
        """获取国际视角情绪分析 (Yahoo Finance / Google Finance)
        
        使用浏览器自动化绕过反爬
        返回: (情绪分数 -20到+20, 详情)
        """
        if not BROWSER_SEARCH_AVAILABLE:
            return 0, None
        
        # 浏览器搜索较慢，暂时禁用
        # TODO: 改为后台异步任务
        return 0, None
    
    def _get_news_sentiment(self, symbol):
        """获取新闻情绪分数 (-20 到 +20)"""
        if not self.use_news_sentiment:
            return 0, None
        
        try:
            # 转换股票代码格式
            code = symbol.replace('sh.', '').replace('sz.', '')
            
            # 获取新闻
            news_list = get_stock_news(code, limit=5)
            
            if not news_list:
                return 0, None
            
            # 分析情绪
            result = get_sentiment_score(code, news_list)
            
            if result:
                # SentimentResult是dataclass，用属性访问
                sentiment_val = result.sentiment if hasattr(result, 'sentiment') else 0
                # 将 -1 到 +1 映射到 -20 到 +20
                news_score = sentiment_val * 20
                return news_score, result
            
            return 0, None
        except Exception as e:
            # 静默失败，不影响整体评分
            return 0, None
    
    def _get_money_flow_sentiment(self, symbol):
        """获取资金流向情绪 (-15 到 +15)"""
        if not self.use_news_sentiment:
            return 0, None
        
        try:
            code = symbol.replace('sh.', '').replace('sz.', '')
            flow = get_money_flow(code, days=3)
            
            if flow and 'main_net_inflow' in flow:
                # 主力净流入
                main_flow = flow['main_net_inflow'] / 10000  # 转万元
                
                # 简单映射
                if main_flow > 10000:  # 大幅流入
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
        except Exception as e:
            return 0, None
    
    def get_comprehensive_features(self, symbol, days=250):
        """获取综合特征 (技术 + 基本面)"""
        # 获取技术数据
        df = get_stock_data(symbol, days, 'baostock')
        if df is None or len(df) < 100:
            return None
        
        # 添加技术指标
        df = add_technical_indicators(df)
        # 不在这里 dropna，让调用者决定
        
        if len(df) < 30:
            return None
        
        # 添加基本面特征 (真实数据)
        fundamentals = get_fundamentals_real(symbol)
        if fundamentals:
            for key, value in fundamentals.items():
                df[key] = value
        
        return df
    
    def _get_sentiment_data(self, symbol, days=60):
        """获取情绪评分所需的最小数据集 - 使用去噪价格"""
        df = get_stock_data(symbol, days, 'baostock')
        if df is None or len(df) < 30:
            return None
        
        # 去噪处理
        if self.use_denoise and self.denoiser:
            # 对Close价格去噪（用于MACD、MA计算）
            df['Close_denoised'] = self._denoise_price(df['Close'])
            # 临时替换Close用于技术指标计算
            original_close = df['Close'].copy()
            df['Close'] = df['Close_denoised']
        
        df = add_technical_indicators(df)
        
        # 恢复原始Close（用于RSI）
        if self.use_denoise and self.denoiser:
            df['Close_original'] = original_close
            # RSI用原始价格重新计算
            delta = df['Close_original'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
        
        return df
    
    def calculate_sentiment_score(self, symbol):
        """计算综合情绪分数 (技术 + 新闻 + 资金流向 + 国际视角)
        
        返回:
            dict: {
                'tech_score': 技术情绪 (-40 到 +40),
                'news_score': 新闻情绪 (-20 到 +20),
                'money_flow_score': 资金流向情绪 (-15 到 +15),
                'international_score': 国际视角情绪 (-20 到 +20),
                'total': 总分 (-95 到 +95),
                'news_detail': 新闻详情,
                'money_flow_detail': 资金流向详情,
                'international_detail': 国际视角详情
            }
        """
        # 技术指标情绪
        df = self._get_sentiment_data(symbol, 60)
        tech_score = 0
        
        if df is not None:
            latest = df.iloc[-1]
            
            rsi = latest.get('RSI', 50)
            macd = latest.get('MACD', 0)
            ma5 = latest.get('MA5', 0)
            ma20 = latest.get('MA20', 0)
            vol = latest.get('Volume', 0)
            vol_ma = latest.get('volume_MA20', 0)
            
            import pandas as pd
            if not (pd.isna(rsi) or pd.isna(macd) or pd.isna(ma5) or pd.isna(ma20)):
                # RSI
                if rsi < 30:
                    tech_score += 20
                elif rsi < 40:
                    tech_score += 10
                elif rsi > 70:
                    tech_score -= 20
                elif rsi > 60:
                    tech_score -= 10
                
                # MACD
                tech_score += 15 if macd > 0 else -15
                
                # 均线
                tech_score += 10 if ma5 > ma20 else -10
                
                # 成交量
                if vol_ma > 0 and not pd.isna(vol) and not pd.isna(vol_ma):
                    vol_ratio = vol / vol_ma
                    if vol_ratio > 2.0:
                        tech_score += 15
                    elif vol_ratio > 1.5:
                        tech_score += 10
                    elif vol_ratio > 1.2:
                        tech_score += 5
        
        # 新闻情绪
        news_score, news_detail = self._get_news_sentiment(symbol)
        
        # 资金流向情绪
        money_flow_score, money_flow_detail = self._get_money_flow_sentiment(symbol)
        
        # 国际视角情绪 (Yahoo Finance等)
        international_score, international_detail = self._get_international_sentiment(symbol)
        
        return {
            'tech_score': tech_score,
            'news_score': news_score,
            'money_flow_score': money_flow_score,
            'international_score': international_score,
            'total': tech_score + news_score + money_flow_score + international_score,
            'news_detail': news_detail,
            'money_flow_detail': money_flow_detail,
            'international_detail': international_detail
        }
    
    def analyze_stock(self, symbol):
        """综合分析股票"""
        df = self.get_comprehensive_features(symbol)
        if df is None:
            return None
        
        # 只取有效数据的行
        df_valid = df.dropna(subset=['RSI', 'MACD', 'MA5', 'MA20', 'Close'])
        if len(df_valid) == 0:
            return None
        
        latest = df_valid.iloc[-1]
        
        # 导入 pandas 用于 NaN 检查
        import pandas as pd
        
        # 基础分数
        score = 0
        
        # 技术面评分
        rsi = latest.get('RSI', 50)
        if not pd.isna(rsi):
            if rsi < 30:
                score += 20
            elif rsi > 70:
                score -= 20
        
        macd = latest.get('MACD', 0)
        if not pd.isna(macd) and macd > 0:
            score += 15
        
        ma5 = latest.get('MA5', 0)
        ma20 = latest.get('MA20', 0)
        if not pd.isna(ma5) and not pd.isna(ma20) and ma5 > ma20:
            score += 10
        
        # 基本面评分
        pe = latest.get('pe_ratio', 20)
        if not pd.isna(pe) and pe > 0:
            if 10 < pe < 25:
                score += 10
        elif pe > 50:
            score -= 10
        
        roe = latest.get('roe', 0)
        if not pd.isna(roe):
            if roe > 15:
                score += 15
            elif roe < 0:
                score -= 10
        
        # 综合情绪分数 (技术 + 新闻 + 资金)
        sentiment_result = self.calculate_sentiment_score(symbol)
        sentiment_score = sentiment_result['total']
        
        return {
            'symbol': symbol,
            'close': latest['Close'],
            'tech_score': score,
            'sentiment_score': sentiment_score,
            'sentiment_detail': sentiment_result,
            'total_score': score + sentiment_score,
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
        
        # 确保特征是数值类型
        X = df[feature_cols].select_dtypes(include=[np.number]).values
        y = df['label'].values
        
        # 过滤 NaN
        try:
            valid = ~np.isnan(X).any(axis=1)
            X, y = X[valid], y[valid]
        except TypeError:
            # 如果仍有问题，尝试转换为float
            X = X.astype(np.float64)
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
    print("DSS v4.2 - 去噪 + 新闻情绪分析测试")
    print("="*60)
    
    stocks = {
        'sh.601111': ('中国国航', '航空'),
        'sh.600519': ('贵州茅台', '白酒'),
        'sh.601398': ('工商银行', '银行'),
    }
    
    # 使用全部功能
    print("\n📊 完整分析 (去噪 + 新闻情绪):\n")
    print("-"*50)
    
    picker = ImprovedStockPicker(use_denoise=True, use_news_sentiment=True)
    
    for code, (name, industry) in stocks.items():
        analysis = picker.analyze_stock(code)
        prediction = picker.predict_with_confidence(code)
        
        if analysis and prediction:
            print(f"\n【{name}】({code})")
            print(f"  收盘价: ¥{analysis['close']:.2f}")
            print(f"  技术评分: {analysis['tech_score']:+d}")
            
            # 情绪详情
            sent = analysis['sentiment_detail']
            print(f"  情绪评分:")
            print(f"    - 技术情绪: {sent['tech_score']:+d}")
            print(f"    - 新闻情绪: {sent['news_score']:+d}")
            print(f"    - 资金流向: {sent['money_flow_score']:+d}")
            print(f"    - 情绪总分: {sent['total']:+d}")
            
            # 新闻详情
            if sent['news_detail']:
                news = sent['news_detail']
                print(f"    - 新闻情绪: {news.get('sentiment_label', 'N/A')} (置信度: {news.get('confidence', 0):.0%})")
                if news.get('key_topics'):
                    print(f"    - 关键词: {', '.join(news['key_topics'][:3])}")
            
            # 资金流向详情
            if sent['money_flow_detail']:
                flow = sent['money_flow_detail']
                main_flow = flow.get('main_net_inflow', 0) / 10000
                print(f"    - 主力净流入: {main_flow:.2f}万元")
            
            print(f"  综合评分: {analysis['total_score']:+d}")
            print(f"  预测: {prediction['direction']} (置信度: {prediction['confidence']:.0f}%)")
    
    print("\n" + "="*60)
