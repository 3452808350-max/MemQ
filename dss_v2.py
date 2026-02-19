#!/usr/bin/env python3
"""
DSS 股票分析系统 v2.0 - 论文增强版 (第 2 周改进)
基于：Walk Forward Validation + XGBoost + 特征工程

功能:
1. Walk Forward 滚动验证 (平衡型配置：train=70, val=15, test=15)
2. 技术指标特征生成 (65 个特征，含 12 个特征选择)
   - 波动率指标：ATR, Bollinger Band Width, Keltner Channel
   - 动量指标：RSI Divergence, Stochastic Oscillator, Williams %R
   - 成交量指标：OBV, VWAP, Volume Momentum
   - 趋势指标：ADX, Parabolic SAR
   - 市场结构：Pivot Points (支撑阻力位)
   - 特征交互项：RSI×成交量，动量×波动率，价格位置×ADX
3. 特征选择 (互信息法，从 65 个特征中选 12 个)
4. XGBoost 预测模型 (真实)
5. 多模型对比框架
6. 回测与风险评估
7. 数据缓存机制
8. 风险管理（止损/止盈）

改进历史:
- 第 2 周 (C-002): 添加新技术指标、特征选择、Walk Forward 参数优化、特征交互项
"""

import numpy as np
import pandas as pd
import os
import warnings
warnings.filterwarnings('ignore')

# ==================== 固定随机种子 (P0) ====================
RANDOM_SEED = 42

# 设置所有随机种子，确保结果可复现
np.random.seed(RANDOM_SEED)


# ==================== 第一部分：数据缓存机制 (P0) ====================

class DataCache:
    """本地数据缓存，避免重复 API 请求
    
    使用 Parquet 格式存储股票数据（优先），如果不可用则使用 CSV
    支持：
    - 按股票代码保存/加载数据
    - 检查缓存是否需要更新
    - 自动创建缓存目录
    """
    
    def __init__(self, cache_dir: str = "./data_cache"):
        """初始化缓存
        
        Args:
            cache_dir: 缓存目录路径，默认为 ./data_cache
        """
        self.cache_dir = cache_dir
        self.cache_file = f"{cache_dir}/stock_data.parquet"
        self.cache_file_csv = f"{cache_dir}/stock_data.csv"
        self.use_parquet = True
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 检查是否支持 Parquet
        try:
            import pyarrow
        except ImportError:
            try:
                import fastparquet
            except ImportError:
                self.use_parquet = False
                print(f"    ⚠ 未安装 pyarrow/fastparquet，使用 CSV 缓存")
    
    def _read_cache(self):
        """读取缓存文件"""
        if self.use_parquet and os.path.exists(self.cache_file):
            try:
                return pd.read_parquet(self.cache_file)
            except:
                pass
        if os.path.exists(self.cache_file_csv):
            return pd.read_csv(self.cache_file_csv, index_col=0, parse_dates=True)
        return None
    
    def _write_cache(self, df):
        """写入缓存文件"""
        if self.use_parquet:
            try:
                df.to_parquet(self.cache_file, index=True)
                return
            except:
                pass
        # 备用：使用 CSV
        df.to_csv(self.cache_file_csv, index=True)
    
    def save(self, symbol: str, df: pd.DataFrame):
        """保存数据到缓存
        
        使用 Parquet 格式存储（优先），如果不可用则使用 CSV
        如果文件已存在，则追加或更新该股票的数据
        
        Args:
            symbol: 股票代码，如 '000001.SS'
            df: 要保存的 DataFrame，包含 OHLCV 数据
        """
        # 添加股票代码列以便区分
        df_cached = df.copy()
        df_cached['symbol'] = symbol
        df_cached['cached_at'] = pd.Timestamp.now()
        
        # 如果缓存文件存在，读取并合并
        existing_df = self._read_cache()
        if existing_df is not None:
            try:
                # 移除该股票的旧数据
                existing_df = existing_df[existing_df['symbol'] != symbol]
                # 合并新旧数据
                combined_df = pd.concat([existing_df, df_cached], ignore_index=False)
                self._write_cache(combined_df)
            except Exception as e:
                print(f"    缓存合并失败：{e}，创建新缓存")
                self._write_cache(df_cached)
        else:
            # 创建新缓存文件
            self._write_cache(df_cached)
        
        print(f"    ✓ 数据已缓存：{symbol}")
    
    def load(self, symbol: str) -> pd.DataFrame:
        """从缓存加载数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            DataFrame 包含该股票的历史数据，如果不存在则返回 None
        """
        df = self._read_cache()
        if df is None:
            return None
        
        try:
            # 筛选指定股票的数据
            symbol_data = df[df['symbol'] == symbol].copy()
            
            if len(symbol_data) == 0:
                return None
            
            # 移除辅助列，返回原始格式
            cols_to_drop = ['symbol', 'cached_at']
            cols_to_drop = [c for c in cols_to_drop if c in symbol_data.columns]
            symbol_data = symbol_data.drop(columns=cols_to_drop)
            
            return symbol_data
        except Exception as e:
            print(f"    缓存加载失败：{e}")
            return None
    
    def needs_update(self, symbol: str, max_age_days: int = 1) -> bool:
        """检查缓存是否需要更新
        
        Args:
            symbol: 股票代码
            max_age_days: 最大缓存天数，默认 1 天
            
        Returns:
            bool: True 表示需要更新，False 表示缓存有效
        """
        df = self._read_cache()
        if df is None:
            return True
        
        try:
            symbol_data = df[df['symbol'] == symbol]
            
            if len(symbol_data) == 0:
                return True
            
            # 检查缓存时间
            cached_at = symbol_data['cached_at'].max()
            # 确保 cached_at 是 Timestamp 类型
            if not isinstance(cached_at, pd.Timestamp):
                cached_at = pd.Timestamp(cached_at)
            age = pd.Timestamp.now() - cached_at
            
            return age > pd.Timedelta(days=max_age_days)
        except Exception as e:
            # print(f"    缓存检查失败：{e}")
            return True


# ==================== 第二部分：市场状态识别 (P2) ====================

class MarketRegimeDetector:
    """市场状态识别器
    
    根据价格和波动率识别当前市场状态，帮助调整交易策略
    
    市场状态分类:
    - 'bull' (牛市): 低波动 + 上涨趋势
    - 'bear' (熊市): 高波动 + 下跌趋势
    - 'sideways' (震荡市): 低波动 + 无明显趋势
    - 'volatile' (高波动市): 高波动 + 方向不明
    
    使用指标:
    - 波动率：价格变化的标准差
    - 趋势强度：移动平均线的斜率
    - 价格相对位置：当前价格相对于移动平均线的位置
    """
    
    def __init__(self, volatility_window=20, trend_window=60):
        """初始化市场状态识别器
        
        Args:
            volatility_window: 波动率计算窗口，默认 20 天
            trend_window: 趋势判断窗口，默认 60 天
        """
        self.volatility_window = volatility_window
        self.trend_window = trend_window
        
        # 波动率阈值（年化）
        self.volatility_high = 0.40  # 40% 年化波动率为高波动
        self.volatility_low = 0.15   # 15% 年化波动率为低波动
        
        # 趋势强度阈值
        self.trend_threshold = 0.05  # 5% 的趋势强度
    
    def detect(self, prices, volatility_window=20):
        """识别当前市场状态
        
        使用波动率和趋势强度判断市场状态：
        - 高波动 + 下跌 = volatile/bear
        - 低波动 + 上涨 = bull
        - 低波动 + 震荡 = sideways
        - 高波动 + 无明显方向 = volatile
        
        Args:
            prices: 价格序列（pandas Series 或 array-like）
            volatility_window: 波动率计算窗口，默认 20 天
            
        Returns:
            str: 市场状态 ('bull' | 'bear' | 'sideways' | 'volatile')
            
        Example:
            >>> detector = MarketRegimeDetector()
            >>> regime = detector.detect(df['close'])
            >>> print(f"当前市场状态：{regime}")
        """
        import numpy as np
        import pandas as pd
        
        # 转换为 pandas Series
        if not isinstance(prices, pd.Series):
            prices = pd.Series(prices)
        
        if len(prices) < volatility_window:
            return 'sideways'  # 数据不足，默认震荡
        
        # 计算收益率
        returns = prices.pct_change().dropna()
        
        # 计算波动率（年化）
        volatility = returns.rolling(volatility_window).std().iloc[-1] * np.sqrt(252)
        
        # 计算趋势强度（使用移动平均线斜率）
        ma_short = prices.rolling(20).mean().iloc[-1]
        ma_long = prices.rolling(self.trend_window).mean().iloc[-1] if len(prices) >= self.trend_window else ma_short
        current_price = prices.iloc[-1]
        
        # 趋势强度：短期均线相对于长期均线的位置
        trend_strength = (ma_short - ma_long) / (ma_long + 1e-10)
        
        # 价格相对位置：当前价格相对于短期均线
        price_position = (current_price - ma_short) / (ma_short + 1e-10)
        
        # 综合判断市场状态
        is_high_volatility = volatility > self.volatility_high
        is_low_volatility = volatility < self.volatility_low
        is_uptrend = trend_strength > self.trend_threshold and price_position > 0
        is_downtrend = trend_strength < -self.trend_threshold or price_position < -0.02
        
        # 状态判断逻辑
        if is_high_volatility and is_downtrend:
            return 'bear'  # 高波动 + 下跌 = 熊市
        elif is_low_volatility and is_uptrend:
            return 'bull'  # 低波动 + 上涨 = 牛市
        elif is_low_volatility and not is_uptrend and not is_downtrend:
            return 'sideways'  # 低波动 + 震荡 = 震荡市
        elif is_high_volatility:
            return 'volatile'  # 高波动 + 方向不明 = 高波动市
        else:
            # 中等波动率，根据趋势判断
            if is_uptrend:
                return 'bull'
            elif is_downtrend:
                return 'bear'
            else:
                return 'sideways'
    
    def detect_with_confidence(self, prices, volatility_window=20):
        """识别市场状态并返回置信度
        
        Args:
            prices: 价格序列
            volatility_window: 波动率计算窗口
            
        Returns:
            dict: {'regime': str, 'confidence': float, 'metrics': dict}
                  regime: 市场状态
                  confidence: 置信度 (0-1)
                  metrics: 详细指标
        """
        import numpy as np
        import pandas as pd
        
        if not isinstance(prices, pd.Series):
            prices = pd.Series(prices)
        
        regime = self.detect(prices, volatility_window)
        
        # 计算置信度
        returns = prices.pct_change().dropna()
        volatility = returns.rolling(volatility_window).std().iloc[-1] * np.sqrt(252)
        
        # 置信度基于波动率与阈值的距离
        if volatility > self.volatility_high:
            vol_confidence = min(1.0, (volatility - self.volatility_high) / 0.2 + 0.5)
        elif volatility < self.volatility_low:
            vol_confidence = min(1.0, (self.volatility_low - volatility) / 0.1 + 0.5)
        else:
            vol_confidence = 0.5  # 中等波动率，置信度较低
        
        # 计算趋势指标
        ma_short = prices.rolling(20).mean().iloc[-1]
        ma_long = prices.rolling(self.trend_window).mean().iloc[-1] if len(prices) >= self.trend_window else ma_short
        trend_strength = abs((ma_short - ma_long) / (ma_long + 1e-10))
        trend_confidence = min(1.0, trend_strength / 0.1)
        
        # 综合置信度
        confidence = (vol_confidence + trend_confidence) / 2
        
        metrics = {
            'volatility': volatility,
            'trend_strength': trend_strength,
            'vol_confidence': vol_confidence,
            'trend_confidence': trend_confidence
        }
        
        return {
            'regime': regime,
            'confidence': confidence,
            'metrics': metrics
        }


# ==================== 第三部分：数据质量检查增强 (P2) ====================

class DataQualityChecker:
    """增强的数据质量检查器
    
    对股票数据进行质量检查，确保数据可靠性和完整性
    
    检查项目:
    - 数据缺口：检测非交易日缺失和异常中断
    - 异常值：使用统计方法检测价格异常
    - 连续性：确保数据时间序列连续
    - 数据完整性：检查 OHLCV 数据是否完整
    
    使用场景:
    - 数据获取后的质量验证
    - 模型训练前的数据清洗
    - 定期数据健康检查
    """
    
    def __init__(self, std_threshold=5, gap_threshold_days=7):
        """初始化数据质量检查器
        
        Args:
            std_threshold: 异常值检测的标准差阈值，默认 5 倍标准差
            gap_threshold_days: 数据缺口阈值（天数），默认 7 天
        """
        self.std_threshold = std_threshold
        self.gap_threshold_days = gap_threshold_days
        
        # 检查结果存储
        self.last_check_results = {}
    
    def check_gaps(self, df):
        """检查数据缺口
        
        检测时间序列中的数据缺失，区分正常非交易日和异常中断
        
        Args:
            df: 包含日期索引的 DataFrame
            
        Returns:
            dict: {'has_gaps': bool, 'gaps': list, 'max_gap_days': int}
                  has_gaps: 是否存在异常缺口
                  gaps: 缺口列表 [(start_date, end_date, days), ...]
                  max_gap_days: 最大缺口天数
                  
        Note:
            - 周末和节假日的 1-3 天缺失是正常的
            - 超过 7 天的连续缺失可能是数据问题
        """
        import pandas as pd
        
        if df is None or len(df) == 0:
            return {'has_gaps': True, 'gaps': [], 'max_gap_days': 0, 'error': '空数据'}
        
        # 获取日期索引
        if isinstance(df.index, pd.DatetimeIndex):
            dates = df.index
        else:
            dates = pd.to_datetime(df.index)
        
        dates = dates.sort_values()
        gaps = []
        max_gap = 0
        
        # 计算相邻日期的间隔
        for i in range(1, len(dates)):
            gap_days = (dates[i] - dates[i-1]).days
            
            # 只记录超过阈值的缺口
            if gap_days > self.gap_threshold_days:
                gaps.append({
                    'start': dates[i-1].strftime('%Y-%m-%d'),
                    'end': dates[i].strftime('%Y-%m-%d'),
                    'days': gap_days
                })
                max_gap = max(max_gap, gap_days)
        
        has_gaps = len(gaps) > 0
        
        result = {
            'has_gaps': has_gaps,
            'gaps': gaps,
            'max_gap_days': max_gap,
            'total_trading_days': len(dates),
            'date_range': f"{dates[0].strftime('%Y-%m-%d')} ~ {dates[-1].strftime('%Y-%m-%d')}"
        }
        
        if has_gaps:
            print(f"    ⚠ 检测到 {len(gaps)} 个数据缺口，最大缺口：{max_gap} 天")
        else:
            print(f"    ✓ 数据连续性良好")
        
        return result
    
    def check_outliers(self, df, std_threshold=None):
        """检测异常值
        
        使用标准差方法检测价格、成交量等异常值
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
            std_threshold: 标准差阈值，默认使用初始化时的值
            
        Returns:
            dict: {'has_outliers': bool, 'outliers': dict, 'outlier_count': int}
                  has_outliers: 是否存在异常值
                  outliers: 各列的异常值统计
                  outlier_count: 异常值总数
                  
        Note:
            - 使用滚动窗口计算均值和标准差
            - 超过 N 倍标准差的值标记为异常
            - 分别检查 open, high, low, close, volume
        """
        import numpy as np
        import pandas as pd
        
        if std_threshold is None:
            std_threshold = self.std_threshold
        
        if df is None or len(df) == 0:
            return {'has_outliers': False, 'outliers': {}, 'outlier_count': 0, 'error': '空数据'}
        
        outliers = {}
        total_outliers = 0
        
        # 检查的列
        columns_to_check = ['open', 'high', 'low', 'close', 'volume']
        available_cols = [c for c in columns_to_check if c in df.columns]
        
        for col in available_cols:
            series = df[col]
            
            # 计算滚动均值和标准差（20 天窗口）
            rolling_mean = series.rolling(window=20, min_periods=5).mean()
            rolling_std = series.rolling(window=20, min_periods=5).std()
            
            # 计算 Z-score
            z_scores = np.abs((series - rolling_mean) / (rolling_std + 1e-10))
            
            # 标记异常值
            outlier_mask = z_scores > std_threshold
            outlier_count = outlier_mask.sum()
            
            if outlier_count > 0:
                outliers[col] = {
                    'count': int(outlier_count),
                    'percentage': float(outlier_count / len(series) * 100),
                    'indices': df.index[outlier_mask].strftime('%Y-%m-%d').tolist()[:10]  # 只显示前 10 个
                }
                total_outliers += outlier_count
        
        has_outliers = total_outliers > 0
        
        result = {
            'has_outliers': has_outliers,
            'outliers': outliers,
            'outlier_count': total_outliers,
            'threshold_used': std_threshold
        }
        
        if has_outliers:
            print(f"    ⚠ 检测到 {total_outliers} 个异常值")
            for col, info in outliers.items():
                print(f"       {col}: {info['count']} 个 ({info['percentage']:.2f}%)")
        else:
            print(f"    ✓ 未发现异常值")
        
        return result
    
    def check_continuity(self, df):
        """检查数据连续性
        
        确保数据在时间上是连续的，没有意外的中断
        
        Args:
            df: 包含日期索引的 DataFrame
            
        Returns:
            dict: {'is_continuous': bool, 'continuity_score': float, 'issues': list}
                  is_continuous: 是否连续
                  continuity_score: 连续性得分 (0-1)
                  issues: 发现的问题列表
        """
        import pandas as pd
        
        if df is None or len(df) == 0:
            return {'is_continuous': False, 'continuity_score': 0, 'issues': ['空数据']}
        
        issues = []
        
        # 获取日期索引
        if isinstance(df.index, pd.DatetimeIndex):
            dates = df.index
        else:
            dates = pd.to_datetime(df.index)
        
        dates = dates.sort_values()
        
        # 计算预期交易日数（扣除周末）
        date_range = pd.date_range(start=dates[0], end=dates[-1], freq='B')  # 工作日
        expected_days = len(date_range)
        actual_days = len(dates)
        
        # 连续性得分
        continuity_score = min(1.0, actual_days / (expected_days + 1))
        
        # 检查数据量
        if actual_days < 30:
            issues.append(f"数据量不足：只有 {actual_days} 个交易日")
        
        if continuity_score < 0.8:
            issues.append(f"连续性较差：{continuity_score:.1%} (预期 {expected_days} 天，实际 {actual_days} 天)")
        
        # 检查是否有重复日期
        if dates.duplicated().any():
            dup_count = dates.duplicated().sum()
            issues.append(f"发现 {dup_count} 个重复日期")
            continuity_score *= 0.9
        
        # 检查日期顺序
        if not dates.is_monotonic_increasing:
            issues.append("日期顺序混乱")
            continuity_score *= 0.8
        
        is_continuous = continuity_score > 0.9 and len(issues) == 0
        
        result = {
            'is_continuous': is_continuous,
            'continuity_score': continuity_score,
            'issues': issues,
            'expected_days': expected_days,
            'actual_days': actual_days
        }
        
        if is_continuous:
            print(f"    ✓ 数据连续性良好 (得分：{continuity_score:.1%})")
        else:
            print(f"    ⚠ 数据连续性问题 (得分：{continuity_score:.1%})")
            for issue in issues:
                print(f"       - {issue}")
        
        return result
    
    def full_check(self, df):
        """执行完整的数据质量检查
        
        一次性执行所有检查项目，返回综合报告
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
            
        Returns:
            dict: 包含所有检查结果的完整报告
        """
        print("\n  数据质量检查:")
        
        gap_result = self.check_gaps(df)
        outlier_result = self.check_outliers(df)
        continuity_result = self.check_continuity(df)
        
        # 综合评分
        quality_score = 100
        if gap_result.get('has_gaps'):
            quality_score -= 20
        if outlier_result.get('has_outliers'):
            quality_score -= 15
        if not continuity_result.get('is_continuous'):
            quality_score -= 20
        
        quality_score = max(0, quality_score)
        
        report = {
            'overall_quality': '优秀' if quality_score >= 90 else '良好' if quality_score >= 70 else '需改进',
            'quality_score': quality_score,
            'gap_check': gap_result,
            'outlier_check': outlier_result,
            'continuity_check': continuity_result
        }
        
        print(f"\n  综合质量评分：{quality_score}/100 ({report['overall_quality']})")
        
        self.last_check_results = report
        return report


# ==================== 第四部分：特征工程 ====================

class FeatureEngineer:
    """技术指标特征生成器
    
    生成多种技术分析指标作为机器学习特征：
    - 移动平均线 (MA)
    - RSI 相对强弱指标
    - MACD 移动平均收敛发散
    - 布林带
    - 波动率指标 (ATR, BB Width, Keltner Channel)
    - 成交量特征 (OBV, VWAP, Volume Momentum)
    - 动量指标 (RSI Divergence, Stochastic, Williams %R)
    - 趋势指标 (ADX, Parabolic SAR)
    - 市场结构 (Pivot Points)
    - 特征交互项
    
    注意：所有特征计算都使用 shift(1) 确保只用历史数据，防止数据泄露
    """
    
    def __init__(self):
        self.feature_names = []
    
    def create_all_features(self, df):
        """创建所有技术指标特征
        
        关键：所有指标基于 shift(1) 的数据计算，确保只用历史数据预测未来
        例如：RSI 使用前一天的收盘价，避免使用当天收盘价（数据泄露）
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
            
        Returns:
            DataFrame 包含所有技术指标特征
        """
        df = df.copy()
        features = pd.DataFrame(index=df.index)
        
        # 获取列名 (兼容大小写)
        # 关键修复 (P0): 使用 shift(1) 确保只用历史数据
        close = df['close'] if 'close' in df.columns else df['Close']
        high = df['high'] if 'high' in df.columns else df['High']
        low = df['low'] if 'low' in df.columns else df['Low']
        volume = df['volume'] if 'volume' in df.columns else df.get('Volume', pd.Series([1]*len(df)))
        open_price = df['open'] if 'open' in df.columns else df.get('Open', close)
        
        # 防止数据泄露：所有价格数据使用前一天的值
        close_shifted = close.shift(1)
        high_shifted = high.shift(1)
        low_shifted = low.shift(1)
        open_shifted = open_price.shift(1)
        
        # ===== 移动平均线 =====
        for window in [5, 10, 20, 60]:
            # 使用 shift(1) 后的收盘价计算 MA
            features[f'MA_{window}'] = close_shifted.rolling(window).mean()
            features[f'MA_ratio_{window}'] = close_shifted / features[f'MA_{window}']
            features[f'MA_slope_{window}'] = features[f'MA_{window}'].pct_change(5)
        
        # ===== RSI (使用前一天的收盘价) =====
        delta = close_shifted.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-10)
        features['RSI'] = 100 - (100 / (1 + rs))
        
        # ===== MACD (使用前一天的收盘价) =====
        ema12 = close_shifted.ewm(span=12).mean()
        ema26 = close_shifted.ewm(span=26).mean()
        features['MACD'] = ema12 - ema26
        features['MACD_signal'] = features['MACD'].ewm(span=9).mean()
        features['MACD_hist'] = features['MACD'] - features['MACD_signal']
        
        # ===== 布林带 (使用前一天的收盘价) =====
        ma20 = close_shifted.rolling(20).mean()
        std20 = close_shifted.rolling(20).std()
        features['BB_upper'] = ma20 + 2 * std20
        features['BB_lower'] = ma20 - 2 * std20
        features['BB_width'] = (features['BB_upper'] - features['BB_lower']) / ma20
        features['BB_position'] = (close_shifted - features['BB_lower']) / (features['BB_upper'] - features['BB_lower'] + 1e-10)
        
        # ===== 波动率指标 =====
        # 基础波动率
        returns = close_shifted.pct_change()
        for window in [5, 10, 20]:
            features[f'volatility_{window}'] = returns.rolling(window).std() * np.sqrt(252)
        
        # ATR (Average True Range) - 平均真实波幅，用于动态止损计算
        tr1 = high_shifted - low_shifted
        tr2 = abs(high_shifted - close_shifted.shift(1))
        tr3 = abs(low_shifted - close_shifted.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        features['ATR'] = tr.rolling(14).mean()
        features['ATR_ratio'] = features['ATR'] / (close_shifted + 1)
        
        # Bollinger Band Width - 波动率压缩/扩张指标
        # BB 宽度收窄表示波动率压缩，可能预示突破；扩张表示趋势加速
        features['BB_width_norm'] = (features['BB_upper'] - features['BB_lower']) / features['BB_upper']
        
        # Keltner Channel - 肯特纳通道，用于趋势判断
        # 上轨 = EMA + 2*ATR, 下轨 = EMA - 2*ATR
        ema20 = close_shifted.ewm(span=20).mean()
        atr14 = features['ATR']
        features['KC_upper'] = ema20 + 2 * atr14
        features['KC_lower'] = ema20 - 2 * atr14
        features['KC_position'] = (close_shifted - features['KC_lower']) / (features['KC_upper'] - features['KC_lower'] + 1e-10)
        
        # ===== 动量指标 =====
        # 基础动量
        for period in [5, 10, 20]:
            features[f'momentum_{period}'] = close_shifted.pct_change(period)
            features[f'roc_{period}'] = (close_shifted - close_shifted.shift(period)) / (close_shifted.shift(period) + 1)
        
        # RSI Divergence - RSI 背离检测
        # 计算价格与 RSI 的背离：价格创新高但 RSI 未创新高为顶背离（看跌）
        # 价格创新低但 RSI 未创新低为底背离（看涨）
        rsi = features['RSI']
        # 5 日价格高点/低点
        price_high_5d = close_shifted.rolling(5).max()
        price_low_5d = close_shifted.rolling(5).min()
        # 5 日 RSI 高点/低点
        rsi_high_5d = rsi.rolling(5).max()
        rsi_low_5d = rsi.rolling(5).min()
        # 背离信号：价格创新高但 RSI 未创新高 (顶背离为负)
        features['RSI_divergence_top'] = (close_shifted > price_high_5d.shift(1)).astype(int) - (rsi > rsi_high_5d.shift(1)).astype(int)
        # 价格创新低但 RSI 未创新低 (底背离为正)
        features['RSI_divergence_bottom'] = (rsi < rsi_low_5d.shift(1)).astype(int) - (close_shifted < price_low_5d.shift(1)).astype(int)
        
        # Stochastic Oscillator - 随机振荡器，超买超卖指标
        # %K = (收盘价 - 最低低) / (最高高 - 最低低) * 100
        lowest_low_14 = low_shifted.rolling(14).min()
        highest_high_14 = high_shifted.rolling(14).max()
        features['Stoch_K'] = 100 * (close_shifted - lowest_low_14) / (highest_high_14 - lowest_low_14 + 1e-10)
        features['Stoch_D'] = features['Stoch_K'].rolling(3).mean()  # %D 为%K 的 3 日 SMA
        
        # Williams %R - 威廉指标，超买超卖指标
        # %R = (最高高 - 收盘价) / (最高高 - 最低低) * -100
        # 范围 -100 到 0，-20 以上超买，-80 以下超卖
        highest_high_14_w = high_shifted.rolling(14).max()
        lowest_low_14_w = low_shifted.rolling(14).min()
        features['Williams_R'] = -100 * (highest_high_14_w - close_shifted) / (highest_high_14_w - lowest_low_14_w + 1e-10)
        
        # ===== 成交量指标 =====
        # 基础成交量特征
        volume_shifted = volume.shift(1)
        features['volume_MA5'] = volume_shifted.rolling(5).mean()
        features['volume_ratio'] = volume_shifted / (features['volume_MA5'] + 1)
        features['volume_ma_ratio'] = volume_shifted / (volume_shifted.rolling(20).mean() + 1)
        
        # OBV (On-Balance Volume) - 能量潮，资金流向指标
        # OBV 累积：价格上涨日加成交量，下跌日减成交量
        price_change = close_shifted.diff()
        obv_direction = np.sign(price_change)
        obv = (obv_direction * volume_shifted).cumsum()
        features['OBV'] = obv
        features['OBV_MA10'] = obv.rolling(10).mean()
        features['OBV_ratio'] = obv / (obv.rolling(10).mean() + 1e-10)
        
        # VWAP (Volume Weighted Average Price) - 成交量加权平均价，机构成本参考
        # VWAP = cumsum(typical_price * volume) / cumsum(volume)
        typical_price = (high_shifted + low_shifted + close_shifted) / 3
        features['VWAP'] = (typical_price * volume_shifted).cumsum() / (volume_shifted.cumsum() + 1e-10)
        features['VWAP_position'] = (close_shifted - features['VWAP']) / (features['VWAP'] + 1e-10)
        
        # Volume Momentum - 成交量动量
        features['volume_momentum'] = volume_shifted.pct_change(5)
        features['volume_roc'] = (volume_shifted - volume_shifted.shift(5)) / (volume_shifted.shift(5) + 1)
        
        # ===== 趋势指标 =====
        # ADX (Average Directional Index) - 平均趋向指数，趋势强度指标
        # ADX > 25 表示强趋势，< 20 表示震荡
        plus_dm = high_shifted.diff()
        minus_dm = -low_shifted.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        atr_adx = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).sum() / (atr_adx + 1e-10))
        minus_di = 100 * (minus_dm.rolling(14).sum() / (atr_adx + 1e-10))
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        features['ADX'] = dx.rolling(14).mean()
        features['Plus_DI'] = plus_di
        features['Minus_DI'] = minus_di
        features['DI_diff'] = plus_di - minus_di
        
        # Parabolic SAR - 抛物线转向指标，趋势转折点
        # 简化实现：使用 EMA 和 ATR 模拟 SAR 行为
        ema50 = close_shifted.ewm(span=50).mean()
        features['Parabolic_SAR'] = ema50 - 2 * atr14 * np.sign(close_shifted - ema50)
        features['SAR_position'] = (close_shifted - features['Parabolic_SAR']) / (close_shifted + 1e-10)
        
        # ===== 市场结构 - Pivot Points (枢轴点) =====
        # 计算支撑阻力位：基于前一日的 High, Low, Close
        # Pivot = (High + Low + Close) / 3
        # R1 = 2*Pivot - Low, R2 = Pivot + (High - Low)
        # S1 = 2*Pivot - High, S2 = Pivot - (High - Low)
        prev_high = high_shifted
        prev_low = low_shifted
        prev_close = close_shifted
        
        pivot = (prev_high + prev_low + prev_close) / 3
        features['Pivot'] = pivot
        features['R1'] = 2 * pivot - prev_low  # 第一阻力位
        features['R2'] = pivot + (prev_high - prev_low)  # 第二阻力位
        features['S1'] = 2 * pivot - prev_high  # 第一支撑位
        features['S2'] = pivot - (prev_high - prev_low)  # 第二支撑位
        
        # 价格相对枢轴点位置
        features['price_vs_pivot'] = (close_shifted - pivot) / (pivot + 1e-10)
        
        # ===== 特征交互项 (P2) =====
        # RSI × 成交量变化率 - 动量与资金流向的结合
        features['RSI_volume_interaction'] = features['RSI'] * features['volume_momentum']
        
        # 动量 × 波动率 - 趋势强度与风险的结合
        features['momentum_volatility_interaction'] = features['momentum_10'] * features['volatility_10']
        
        # 价格位置 × ADX - 价格相对位置与趋势强度的结合
        features['price_position_ADX_interaction'] = features['BB_position'] * features['ADX']
        
        # 填充 NaN
        features = features.fillna(0)
        
        self.feature_names = features.columns.tolist()
        return features
    
    def select_features(self, X, y, k=12):
        """使用互信息选择最重要的 k 个特征
        
        通过计算每个特征与目标变量的互信息（Mutual Information），
        选择信息量最大的 k 个特征，减少维度并提高模型泛化能力。
        
        Args:
            X: 特征 DataFrame
            y: 目标变量 Series
            k: 选择的特征数量，默认 12
            
        Returns:
            list: 选中的特征名列表
        """
        from sklearn.feature_selection import mutual_info_classif
        
        # 将连续目标变量离散化用于分类
        # 使用 3 分位数将收益率分为：下跌、持平、上涨
        y_discrete = pd.cut(y, bins=3, labels=[0, 1, 2]).fillna(1).astype(int)
        
        # 计算互信息分数
        mi_scores = mutual_info_classif(X, y_discrete, random_state=RANDOM_SEED)
        
        # 创建特征重要性 DataFrame
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'mi_score': mi_scores
        }).sort_values('mi_score', ascending=False)
        
        # 选择前 k 个特征
        selected_features = feature_importance.head(k)['feature'].tolist()
        
        print(f"    特征选择：从 {len(X.columns)} 个特征中选出 {k} 个最重要特征")
        print(f"    选中的特征：{selected_features}")
        
        return selected_features
    
    def get_feature_names(self):
        """获取特征名称列表"""
        return self.feature_names


# ==================== 第三部分：Walk Forward 验证 ====================

class WalkForwardValidator:
    """Walk Forward 滚动验证
    
    实现时间序列的滚动交叉验证：
    - 训练集：train_days 天
    - 验证集：val_days 天（用于早停）
    - 测试集：test_days 天（用于评估）
    
    每次滚动 test_days 天，模拟真实的滚动训练过程
    
    平衡型配置 (P1 改进)：
    - train_days=70: 约 3 个月交易日，足够学习市场模式
    - val_days=15: 约 3 周，用于早停和超参调整
    - test_days=15: 约 3 周，充分评估模型性能
    """
    
    def __init__(self, train_days=70, val_days=15, test_days=15):
        """初始化验证器
        
        Args:
            train_days: 训练集天数，默认 70（约 3 个月交易日，平衡型配置）
            val_days: 验证集天数，默认 15（约 3 周，用于早停）
            test_days: 测试集天数，默认 15（约 3 周，充分评估）
        """
        self.train_days = train_days
        self.val_days = val_days
        self.test_days = test_days
    
    def rolling_validate(self, features, target, model_class, model_params=None):
        """执行 Walk Forward 滚动验证
        
        Args:
            features: 特征 DataFrame
            target: 目标变量 Series
            model_class: 模型类
            model_params: 模型参数字典
            
        Returns:
            dict 包含预测结果、实际值和评估指标
        """
        predictions = []
        actuals = []
        
        total_samples = len(features)
        step = self.test_days
        
        for start in range(0, total_samples - self.train_days - self.val_days - self.test_days, step):
            train_end = start + self.train_days
            val_end = train_end + self.val_days
            test_end = val_end + self.test_days
            
            if test_end > total_samples:
                break
            
            X_train = features.iloc[start:train_end]
            y_train = target.iloc[start:train_end]
            
            X_val = features.iloc[train_end:val_end]
            y_val = target.iloc[train_end:val_end]
            
            X_test = features.iloc[val_end:test_end]
            y_test = target.iloc[val_end:test_end]
            
            # 训练模型
            model = model_class(**(model_params or {}))
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
            
            pred = model.predict(X_test)
            
            predictions.extend(pred)
            actuals.extend(y_test.values)
        
        metrics = self.calculate_metrics(np.array(predictions), np.array(actuals))
        
        return {
            'predictions': predictions,
            'actuals': actuals,
            'metrics': metrics
        }
    
    def calculate_metrics(self, predictions, actuals):
        """计算评估指标
        
        Args:
            predictions: 预测值数组
            actuals: 实际值数组
            
        Returns:
            dict 包含方向准确率、MSE、MAE、RMSE 等指标
        """
        pred_direction = np.sign(predictions)
        actual_direction = np.sign(actuals)
        direction_acc = np.mean(pred_direction == actual_direction)
        
        mse = np.mean((predictions - actuals) ** 2)
        mae = np.mean(np.abs(predictions - actuals))
        rmse = np.sqrt(mse)
        
        correct_direction = np.sum((predictions > 0) == (actuals > 0))
        direction_pct = correct_direction / len(predictions) if len(predictions) > 0 else 0
        
        return {
            'direction_accuracy': direction_acc,
            'direction_accuracy_pct': direction_pct,
            'mse': mse,
            'mae': mae,
            'rmse': rmse,
            'num_predictions': len(predictions)
        }


# ==================== 第四部分：XGBoost 模型 (真实) ====================

class XGBoostModel:
    """真实 XGBoost 模型
    
    使用 XGBoost 回归器进行股票收益率预测
    固定 random_state=42 确保结果可复现
    """
    
    def __init__(self, n_estimators=100, max_depth=5, learning_rate=0.1, early_stopping_rounds=10):
        """初始化 XGBoost 模型
        
        Args:
            n_estimators: 树的数量
            max_depth: 树的最大深度
            learning_rate: 学习率
            early_stopping_rounds: 早停轮数
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.early_stopping_rounds = early_stopping_rounds
        self.model = None
        self.feature_importances_ = None
    
    def fit(self, X, y, eval_set=None, verbose=True):
        """训练 XGBoost 模型
        
        Args:
            X: 特征数据
            y: 目标变量
            eval_set: 验证集 [(X_val, y_val)]
            verbose: 是否打印训练日志
            
        Returns:
            self
        """
        import xgboost as xgb
        
        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            early_stopping_rounds=self.early_stopping_rounds,
            random_state=RANDOM_SEED,  # 固定随机种子 (P0)
            verbosity=0,
            n_jobs=-1
        )
        
        if eval_set is not None:
            self.model.fit(X, y, eval_set=eval_set, verbose=False)
        else:
            self.model.fit(X, y)
        
        self.feature_importances_ = self.model.feature_importances_
        return self
    
    def predict(self, X):
        """预测"""
        return self.model.predict(X)


class LSTMModel:
    """LSTM 模型 (使用 sklearn 的简单实现)
    
    使用 GradientBoosting 作为 LSTM 的替代实现
    固定 random_state=42 确保结果可复现
    """
    
    def __init__(self, window=10):
        """初始化 LSTM 模型
        
        Args:
            window: 时间窗口大小
        """
        self.window = window
        self.model = None
        self.scaler = None
    
    def fit(self, X, y, eval_set=None, verbose=True):
        """训练模型"""
        from sklearn.ensemble import GradientBoostingRegressor
        
        # 准备序列数据
        X_seq = []
        y_seq = []
        
        if hasattr(X, 'values'):
            X_arr = X.values
        else:
            X_arr = np.array(X)
        
        if hasattr(y, 'values'):
            y_arr = y.values
        else:
            y_arr = np.array(y)
        
        for i in range(self.window, len(X_arr)):
            X_seq.append(X_arr[i-self.window:i].flatten())
            y_seq.append(y_arr[i])
        
        X_seq = np.array(X_seq)
        y_seq = np.array(y_seq)
        
        # 使用 GradientBoosting 作为 LSTM 的替代
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=RANDOM_SEED  # 固定随机种子 (P0)
        )
        self.model.fit(X_seq, y_seq)
        
        return self
    
    def predict(self, X):
        """预测"""
        X_seq = []
        
        if hasattr(X, 'values'):
            X_arr = X.values
        else:
            X_arr = np.array(X)
        
        for i in range(len(X_arr)):
            X_seq.append(X_arr[i-self.window:i].flatten())
        
        X_seq = np.array(X_seq)
        
        return self.model.predict(X_seq)


class RandomForestModel:
    """随机森林模型
    
    固定 random_state=42 确保结果可复现
    """
    
    def __init__(self, n_estimators=100, max_depth=10):
        """初始化随机森林模型
        
        Args:
            n_estimators: 树的数量
            max_depth: 树的最大深度
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.model = None
    
    def fit(self, X, y, eval_set=None, verbose=True):
        """训练随机森林模型"""
        from sklearn.ensemble import RandomForestRegressor
        
        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=RANDOM_SEED,  # 固定随机种子 (P0)
            n_jobs=-1
        )
        self.model.fit(X, y)
        return self
    
    def predict(self, X):
        """预测"""
        return self.model.predict(X)


# ==================== 新增：概率校准器 (P1) ====================

class ProbabilityCalibrator:
    """概率校准器 - 使用 Platt Scaling
    
    用于校准模型输出的概率，使其更接近真实概率
    Platt Scaling 是一种常用的概率校准方法，特别适用于不平衡数据集
    
    使用场景:
    - 模型输出的概率需要更准确地反映真实发生概率
    - 需要基于概率阈值做决策（如置信度过滤）
    """
    
    def __init__(self):
        """初始化校准器"""
        self.scaler = None
        self.is_fitted = False
    
    def fit(self, y_pred_proba, y_true):
        """训练校准器 - 使用 Platt Scaling
        
        Args:
            y_pred_proba: 模型预测的概率 (n_samples,) 或 (n_samples, n_classes)
            y_true: 真实标签 (n_samples,)
            
        注意:
        - 如果输入是二维数组（多分类），会对每个类别分别校准
        - 使用 CalibratedClassifierCV 实现 Platt Scaling (sigmoid 校准)
        """
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.naive_bayes import GaussianNB
        import numpy as np
        
        # 确保输入是二维数组
        y_pred_proba = np.array(y_pred_proba)
        y_true = np.array(y_true)
        
        if y_pred_proba.ndim == 1:
            # 二分类：转换为二维 (n_samples, 2)
            y_pred_proba_2d = np.column_stack([1 - y_pred_proba, y_pred_proba])
        else:
            y_pred_proba_2d = y_pred_proba
        
        # 创建虚拟预测器，使用校准器直接校准概率
        # CalibratedClassifierCV 需要 estimator，但我们只关心校准
        # 这里使用一个简单的方法：拟合 sigmoid 函数
        from sklearn.linear_model import LogisticRegression
        
        self.scaler = LogisticRegression()
        self.scaler.fit(y_pred_proba_2d, y_true)
        self.is_fitted = True
        
        print(f"    ✓ 概率校准器训练完成 (Platt Scaling)")
    
    def predict_proba(self, y_pred_proba):
        """返回校准后的概率
        
        Args:
            y_pred_proba: 模型预测的原始概率
            
        Returns:
            np.array: 校准后的概率
        """
        if not self.is_fitted:
            print("    ⚠ 校准器未训练，返回原始概率")
            return y_pred_proba
        
        y_pred_proba = np.array(y_pred_proba)
        
        if y_pred_proba.ndim == 1:
            y_pred_proba_2d = np.column_stack([1 - y_pred_proba, y_pred_proba])
        else:
            y_pred_proba_2d = y_pred_proba
        
        calibrated = self.scaler.predict_proba(y_pred_proba_2d)
        
        # 返回正类的概率
        if calibrated.ndim == 2:
            return calibrated[:, 1]
        return calibrated


# ==================== 新增：LightGBM 模型 (P2) ====================

class LightGBMModel:
    """LightGBM 模型 - XGBoost 的轻量替代
    
    LightGBM 特点:
    - 更快的训练速度
    - 更低的内存占用
    - 支持大规模数据
    - 基于直方图的算法
    
    如果 lightgbm 未安装，自动回退到 XGBoost
    """
    
    def __init__(self, n_estimators=100, max_depth=5, learning_rate=0.1, early_stopping_rounds=10):
        """初始化 LightGBM 模型
        
        Args:
            n_estimators: 树的数量，默认 100
            max_depth: 树的最大深度，默认 5
            learning_rate: 学习率，默认 0.1
            early_stopping_rounds: 早停轮数，默认 10
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.early_stopping_rounds = early_stopping_rounds
        self.model = None
        self.feature_importances_ = None
        self.use_xgboost_fallback = False
    
    def fit(self, X, y, eval_set=None, verbose=True):
        """训练 LightGBM 模型
        
        Args:
            X: 特征数据
            y: 目标变量
            eval_set: 验证集 [(X_val, y_val)]
            verbose: 是否打印训练日志
            
        Returns:
            self
        """
        try:
            import lightgbm as lgb
            
            # 准备训练数据
            train_data = lgb.Dataset(X, label=y)
            
            # 准备验证数据
            valid_data = None
            if eval_set is not None:
                X_val, y_val = eval_set[0]
                valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            
            # 模型参数
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'num_leaves': 2 ** self.max_depth,  # LightGBM 使用 num_leaves 而非 max_depth
                'learning_rate': self.learning_rate,
                'feature_fraction': 0.8,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'seed': RANDOM_SEED,
                'n_jobs': -1
            }
            
            # 训练模型
            # 注意：LightGBM 的 train() 函数使用 callbacks 进行早停
            callbacks = []
            if valid_data is not None and self.early_stopping_rounds is not None:
                callbacks.append(lgb.early_stopping(stopping_rounds=self.early_stopping_rounds, verbose=False))
            
            if valid_data is not None:
                self.model = lgb.train(
                    params,
                    train_data,
                    num_boost_round=self.n_estimators,
                    valid_sets=[valid_data],
                    callbacks=callbacks if callbacks else None
                )
            else:
                self.model = lgb.train(
                    params,
                    train_data,
                    num_boost_round=self.n_estimators
                )
            
            # 获取特征重要性
            self.feature_importances_ = self.model.feature_importance(importance_type='gain')
            
            print(f"    ✓ LightGBM 训练完成 (使用 {self.model.num_trees()} 棵树)")
            
        except ImportError:
            # LightGBM 未安装，使用 XGBoost 作为备用
            print(f"    ⚠ LightGBM 未安装，使用 XGBoost 作为备用")
            self.use_xgboost_fallback = True
            self._fit_xgboost_fallback(X, y, eval_set, verbose)
        except Exception as e:
            print(f"    ⚠ LightGBM 训练失败：{e}，使用 XGBoost 作为备用")
            self.use_xgboost_fallback = True
            self._fit_xgboost_fallback(X, y, eval_set, verbose)
        
        return self
    
    def _fit_xgboost_fallback(self, X, y, eval_set=None, verbose=True):
        """XGBoost 备用实现"""
        import xgboost as xgb
        
        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            early_stopping_rounds=self.early_stopping_rounds,
            random_state=RANDOM_SEED,
            verbosity=0,
            n_jobs=-1
        )
        
        if eval_set is not None:
            self.model.fit(X, y, eval_set=eval_set, verbose=False)
        else:
            self.model.fit(X, y)
        
        self.feature_importances_ = self.model.feature_importances_
    
    def predict(self, X):
        """预测"""
        if self.use_xgboost_fallback:
            return self.model.predict(X)
        return self.model.predict(X)


# ==================== 第五部分：风险管理 (P1) ====================

class RiskManager:
    """风险管理器
    
    实现交易风险控制机制：
    - 止损：当亏损达到阈值时自动平仓
    - 止盈：当盈利达到阈值时自动平仓
    - 仓位控制：限制最大持仓比例
    
    参数:
        stop_loss: 止损比例，默认 5%
        take_profit: 止盈比例，默认 10%
        max_position: 最大仓位比例，默认 50%
    """
    
    def __init__(self, 
                 stop_loss=0.05,      # 5% 止损
                 take_profit=0.10,    # 10% 止盈
                 max_position=0.5):   # 最大仓位 50%
        """初始化风险管理器
        
        Args:
            stop_loss: 止损阈值（小数），默认 0.05 表示 5%
            take_profit: 止盈阈值（小数），默认 0.10 表示 10%
            max_position: 最大仓位比例，默认 0.5 表示 50%
        """
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.max_position = max_position
    
    def should_close_position(self, entry_price, current_price, position_type):
        """判断是否应该平仓
        
        根据止损和止盈阈值判断是否应该关闭当前持仓
        
        Args:
            entry_price: 开仓价格
            current_price: 当前价格
            position_type: 持仓类型，'long' 做多 或 'short' 做空
            
        Returns:
            tuple: (should_close: bool, reason: str)
                   should_close 表示是否应该平仓
                   reason 说明平仓原因（止损/止盈/持有）
        """
        if position_type == 'long':
            # 做多：价格下跌止损，价格上涨止盈
            pct_change = (current_price - entry_price) / entry_price
            
            if pct_change <= -self.stop_loss:
                return True, 'stop_loss'  # 触发止损
            elif pct_change >= self.take_profit:
                return True, 'take_profit'  # 触发止盈
            else:
                return False, 'hold'  # 继续持有
        
        elif position_type == 'short':
            # 做空：价格上涨止损，价格下跌止盈
            pct_change = (entry_price - current_price) / entry_price
            
            if pct_change <= -self.stop_loss:
                return True, 'stop_loss'  # 触发止损
            elif pct_change >= self.take_profit:
                return True, 'take_profit'  # 触发止盈
            else:
                return False, 'hold'  # 继续持有
        
        else:
            return False, 'invalid_position'
    
    def get_position_size(self, capital, price):
        """计算建议仓位大小
        
        Args:
            capital: 总资金
            price: 当前价格
            
        Returns:
            float: 建议购买的股数
        """
        max_capital = capital * self.max_position
        shares = max_capital / price
        return shares
    
    def calculate_risk_reward_ratio(self, entry_price, stop_loss_price, take_profit_price):
        """计算风险收益比
        
        Args:
            entry_price: 开仓价格
            stop_loss_price: 止损价格
            take_profit_price: 止盈价格
            
        Returns:
            float: 风险收益比（收益/风险）
        """
        risk = abs(entry_price - stop_loss_price)
        reward = abs(take_profit_price - entry_price)
        
        if risk == 0:
            return 0
        
        return reward / risk


# ==================== 第六部分：信号生成与回测 ====================

class SignalGenerator:
    """交易信号生成器
    
    根据模型预测生成交易信号：
    - 1: 买入信号
    - -1: 卖出信号
    - 0: 持有/观望
    
    支持置信度阈值过滤：仅在模型置信度高于阈值时生成交易信号
    """
    
    def __init__(self, 
                 buy_threshold=0.005, 
                 sell_threshold=-0.005,
                 confidence_threshold=0.65):  # 新增：仅在 65% 以上置信度时交易
        """初始化信号生成器
        
        Args:
            buy_threshold: 买入阈值，预测值超过此值生成买入信号
            sell_threshold: 卖出阈值，预测值低于此值生成卖出信号
            confidence_threshold: 置信度阈值 (0-1)，默认 0.65
                                  仅当预测概率 >= 此值时才交易，否则持有
        """
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.confidence_threshold = confidence_threshold
    
    def generate(self, predictions):
        """生成交易信号（基础版本，不使用置信度）
        
        Args:
            predictions: 模型预测值数组
            
        Returns:
            np.array: 交易信号数组 (1=买入，-1=卖出，0=持有)
        """
        signals = np.zeros(len(predictions))
        
        for i, pred in enumerate(predictions):
            if pred > self.buy_threshold:
                signals[i] = 1
            elif pred < self.sell_threshold:
                signals[i] = -1
            else:
                signals[i] = 0
        
        return signals
    
    def generate_with_confidence(self, predictions, probabilities):
        """仅在高置信度时生成信号
        
        结合预测值和置信度概率生成交易信号：
        - 如果预测值 > buy_threshold 且 概率 >= confidence_threshold → 买入
        - 如果预测值 < sell_threshold 且 概率 >= confidence_threshold → 卖出
        - 否则 → 持有（不交易）
        
        Args:
            predictions: 模型预测值数组（收益率预测）
            probabilities: 模型预测概率数组（置信度，0-1 之间）
            
        Returns:
            np.array: 交易信号数组 (1=买入，-1=卖出，0=持有)
            
        示例:
            >>> sg = SignalGenerator(confidence_threshold=0.65)
            >>> predictions = [0.01, 0.02, -0.01, 0.005]
            >>> probabilities = [0.70, 0.50, 0.80, 0.90]
            >>> signals = sg.generate_with_confidence(predictions, probabilities)
            >>> # 结果：[1, 0, -1, 0] 
            >>> # 解释：第 1 个预测置信度高且为买入信号 → 买入
            >>> #       第 2 个预测置信度低 → 持有（即使预测值为正）
            >>> #       第 3 个预测置信度高且为卖出信号 → 卖出
            >>> #       第 4 个预测值未达阈值 → 持有
        """
        signals = np.zeros(len(predictions))
        probabilities = np.array(probabilities)
        
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            # 检查置信度是否达到阈值
            if prob < self.confidence_threshold:
                # 置信度不足，不交易（持有）
                signals[i] = 0
            else:
                # 置信度足够，根据预测值生成信号
                if pred > self.buy_threshold:
                    signals[i] = 1  # 买入
                elif pred < self.sell_threshold:
                    signals[i] = -1  # 卖出
                else:
                    signals[i] = 0  # 预测值未达阈值，持有
        
        # 统计信号分布
        num_buy = np.sum(signals == 1)
        num_sell = np.sum(signals == -1)
        num_hold = np.sum(signals == 0)
        high_conf_count = np.sum(probabilities >= self.confidence_threshold)
        
        print(f"    信号生成 (置信度阈值={self.confidence_threshold:.2f}):")
        print(f"      高置信度样本：{high_conf_count}/{len(probabilities)} ({high_conf_count/len(probabilities)*100:.1f}%)")
        print(f"      买入信号：{num_buy}, 卖出信号：{num_sell}, 持有：{num_hold}")
        
        return signals


class Backtester:
    """回测系统
    
    模拟真实交易环境，考虑：
    - 交易成本（佣金、印花税等）
    - 滑点（买卖价差）
    - 止损/止盈机制
    - 仓位控制
    
    参数:
        initial_capital: 初始资金
        transaction_cost: 交易成本比例，默认 0.1%
        slippage: 滑点比例，默认 0.05%
        risk_manager: 风险管理器（可选）
    """
    
    def __init__(self, 
                 initial_capital=100000, 
                 transaction_cost=0.001,  # 0.1% 交易成本
                 slippage=0.0005,         # 0.05% 滑点
                 risk_manager=None):      # 风险管理器
        """初始化回测系统
        
        Args:
            initial_capital: 初始资金，默认 100000
            transaction_cost: 交易成本比例，默认 0.001（0.1%）
            slippage: 滑点比例，默认 0.0005（0.05%）
            risk_manager: 风险管理器实例（可选）
                          如果提供，将在回测中应用止损/止盈/仓位控制
        """
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.risk_manager = risk_manager
        
        # 如果没有提供风险管理器，创建一个默认的
        if risk_manager is None:
            self.risk_manager = RiskManager(
                stop_loss=0.05,      # 5% 止损
                take_profit=0.10,    # 10% 止盈
                max_position=0.5     # 最大 50% 仓位
            )
    
    def calculate_returns(self, signals, prices):
        """计算扣除交易成本后的收益
        
        考虑交易成本和滑点对收益的影响
        
        Args:
            signals: 交易信号数组
            prices: 价格数组
            
        Returns:
            np.array: 扣除成本后的收益率数组
        """
        returns = []
        position = 0
        
        for i in range(1, len(signals)):
            # 计算原始收益率
            price_return = (prices[i] - prices[i-1]) / prices[i-1]
            
            # 检测交易发生
            if signals[i] != signals[i-1]:
                # 有交易发生，扣除交易成本和滑点
                if signals[i] != 0 or signals[i-1] != 0:
                    # 扣除双向成本（开仓 + 平仓）
                    cost = self.transaction_cost * 2 + self.slippage * 2
                    adjusted_return = price_return - cost
                else:
                    adjusted_return = price_return
            else:
                adjusted_return = price_return
            
            returns.append(adjusted_return)
        
        return np.array(returns)
    
    def run(self, prices, signals, risk_manager=None):
        """运行回测
        
        Args:
            prices: 价格序列
            signals: 交易信号序列
            risk_manager: 风险管理器（可选）
            
        Returns:
            dict: 回测结果，包含总收益、夏普比率、最大回撤等
        """
        capital = self.initial_capital
        position = 0
        cash = capital
        
        portfolio_values = []
        trades = []
        entry_price = 0  # 记录开仓价格
        
        for i in range(len(signals)):
            current_price = prices.iloc[i] if hasattr(prices, 'iloc') else prices[i]
            signal = signals[i]
            
            # 应用滑点到成交价格
            if signal == 1:  # 买入
                exec_price = current_price * (1 + self.slippage)
            elif signal == -1:  # 卖出
                exec_price = current_price * (1 - self.slippage)
            else:
                exec_price = current_price
            
            # 检查风险管理（止损/止盈）
            should_close = False
            if risk_manager and position > 0:
                should_close, reason = risk_manager.should_close_position(
                    entry_price, exec_price, 'long'
                )
                if should_close:
                    signal = -1  # 强制平仓
                    trades.append((f'FORCE_SELL_{reason}', i, exec_price))
            
            # 执行交易
            if signal == 1 and position == 0 and cash > 0:
                # 买入：扣除交易成本
                shares = (cash * (1 - self.transaction_cost)) / exec_price
                position = shares
                entry_price = exec_price  # 记录开仓价格
                cash = 0
                trades.append(('BUY', i, exec_price))
            
            elif signal == -1 and position > 0:
                # 卖出：扣除交易成本
                proceeds = position * exec_price * (1 - self.transaction_cost)
                cash = proceeds
                trades.append(('SELL', i, exec_price))
                position = 0
                entry_price = 0
            
            # 计算组合价值
            portfolio_value = cash + position * current_price
            portfolio_values.append(portfolio_value)
        
        portfolio_values = np.array(portfolio_values)
        
        # 计算收益率（考虑交易成本）
        if len(portfolio_values) > 1:
            returns = np.diff(portfolio_values) / portfolio_values[:-1]
        else:
            returns = np.array([])
        
        # 计算夏普比率
        sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252) if len(returns) > 0 else 0
        
        # 计算最大回撤
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        # 计算总收益
        total_return = (portfolio_values[-1] - self.initial_capital) / self.initial_capital if len(portfolio_values) > 0 else 0
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'num_trades': len(trades),
            'final_value': portfolio_values[-1] if len(portfolio_values) > 0 else self.initial_capital,
            'portfolio_values': portfolio_values.tolist(),
            'trades': trades
        }
    
    def run_with_risk_management(self, prices, signals, predictions=None, probabilities=None):
        """带风险管理的回测
        
        在基础回测功能上增加：
        - 实时止损/止盈检查
        - 仓位控制
        - 可选的置信度过滤（如果提供 probabilities）
        
        Args:
            prices: 价格序列（DataFrame 或 array）
            signals: 交易信号序列（1=买入，-1=卖出，0=持有）
            predictions: 模型预测值（可选，用于日志记录）
            probabilities: 预测概率/置信度（可选，如果提供则应用置信度过滤）
            
        Returns:
            dict: 回测结果，包含：
                - total_return: 总收益率
                - sharpe_ratio: 夏普比率
                - max_drawdown: 最大回撤
                - num_trades: 交易次数
                - final_value: 最终资产值
                - portfolio_values: 组合价值序列
                - trades: 交易记录列表
                - risk_events: 风险事件记录（止损/止盈触发）
        """
        capital = self.initial_capital
        position = 0
        cash = capital
        
        portfolio_values = []
        trades = []
        risk_events = []  # 记录止损/止盈事件
        entry_price = 0  # 记录开仓价格
        entry_day = 0  # 记录开仓日期索引
        
        # 如果提供了概率，使用置信度过滤的信号
        if probabilities is not None and hasattr(self, 'signal_generator'):
            # 使用带置信度的信号生成
            pass  # 信号已经过过滤
        
        for i in range(len(signals)):
            current_price = prices.iloc[i] if hasattr(prices, 'iloc') else prices[i]
            signal = signals[i]
            
            # 应用滑点到成交价格
            if signal == 1:  # 买入
                exec_price = current_price * (1 + self.slippage)
            elif signal == -1:  # 卖出
                exec_price = current_price * (1 - self.slippage)
            else:
                exec_price = current_price
            
            # ========== 风险管理检查（止损/止盈）==========
            should_close = False
            close_reason = 'normal'
            
            if self.risk_manager and position > 0:
                # 检查是否触发止损或止盈
                should_close, reason = self.risk_manager.should_close_position(
                    entry_price, exec_price, 'long'
                )
                if should_close:
                    signal = -1  # 强制平仓
                    close_reason = reason
                    risk_events.append({
                        'type': reason,
                        'day': i,
                        'entry_price': entry_price,
                        'exit_price': exec_price,
                        'pct_change': (exec_price - entry_price) / entry_price
                    })
                    trades.append((f'FORCE_SELL_{reason}', i, exec_price))
            
            # ========== 仓位控制 ==========
            # 检查是否超过最大仓位
            if signal == 1 and position == 0:
                max_allowed_capital = capital * self.risk_manager.max_position
                if cash > max_allowed_capital:
                    # 限制仓位
                    cash_to_use = max_allowed_capital
                else:
                    cash_to_use = cash
                
                # 买入：扣除交易成本
                shares = (cash_to_use * (1 - self.transaction_cost)) / exec_price
                position = shares
                entry_price = exec_price
                entry_day = i
                cash = cash - cash_to_use  # 更新剩余现金
                trades.append(('BUY', i, exec_price))
            
            elif signal == -1 and position > 0:
                # 卖出：扣除交易成本
                proceeds = position * exec_price * (1 - self.transaction_cost)
                cash = cash + proceeds
                trades.append(('SELL', i, exec_price))
                position = 0
                entry_price = 0
            
            # 计算组合价值
            portfolio_value = cash + position * current_price
            portfolio_values.append(portfolio_value)
        
        portfolio_values = np.array(portfolio_values)
        
        # 计算收益率（考虑交易成本）
        if len(portfolio_values) > 1:
            returns = np.diff(portfolio_values) / portfolio_values[:-1]
        else:
            returns = np.array([])
        
        # 计算夏普比率
        sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252) if len(returns) > 0 else 0
        
        # 计算最大回撤
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        max_drawdown = np.min(drawdown) if len(drawdown) > 0 else 0
        
        # 计算总收益
        total_return = (portfolio_values[-1] - self.initial_capital) / self.initial_capital if len(portfolio_values) > 0 else 0
        
        # 统计风险事件
        stop_loss_count = sum(1 for e in risk_events if e['type'] == 'stop_loss')
        take_profit_count = sum(1 for e in risk_events if e['type'] == 'take_profit')
        
        if risk_events:
            print(f"    风险事件统计:")
            print(f"      止损触发：{stop_loss_count} 次")
            print(f"      止盈触发：{take_profit_count} 次")
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'num_trades': len(trades),
            'final_value': portfolio_values[-1] if len(portfolio_values) > 0 else self.initial_capital,
            'portfolio_values': portfolio_values.tolist(),
            'trades': trades,
            'risk_events': risk_events
        }


# ==================== 主程序入口 ====================

# Alpha Vantage API Key
ALPHA_VANTAGE_API_KEY = "MXAYBEBGFHR6PHYW"

# ==================== 第七部分：多数据源支持 (P1) ====================

def fetch_from_tushare(symbol):
    """从 Tushare 获取 A 股数据
    
    Tushare 是一个免费/付费的金融数据接口，主要覆盖 A 股市场
    需要安装 tushare 库：pip install tushare
    
    Args:
        symbol: 股票代码，如 '000001.SS' 或 '300750.SZ'
        
    Returns:
        DataFrame: 包含 OHLCV 数据的 DataFrame，获取失败返回 None
        
    Note:
        - 需要 Tushare token（可在 tushare.pro 注册获取）
        - 免费用户有积分限制，部分数据需要付费
        - 如果未安装 tushare 或无 token，返回 None
    """
    try:
        import tushare as ts
        import pandas as pd
        
        # Tushare token（用户需要自行设置）
        # 可以通过环境变量或配置文件设置，这里使用占位符
        import os
        tushare_token = os.getenv('TUSHARE_TOKEN', '')
        
        if not tushare_token:
            print(f"    ⚠ Tushare: 未设置 TUSHARE_TOKEN 环境变量")
            return None
        
        # 初始化 Tushare
        ts.set_token(tushare_token)
        pro = ts.pro_api()
        
        # 转换股票代码格式（去掉 .SS/.SZ 后缀）
        clean_symbol = symbol.replace('.SS', '').replace('.SZ', '').replace('.', '')
        
        # 获取日线数据
        # Tushare 的 ts_code 格式：000001.SZ（平安银行）
        df = pro.daily(ts_code=clean_symbol, start_date='20200101')
        
        if df is not None and len(df) > 0:
            # 重命名列以匹配系统格式
            df = df.rename(columns={
                'trade_date': 'Date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume'  # Tushare 使用 vol 表示成交量
            })
            
            # 设置日期索引
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
            df = df.sort_index()
            
            # 选择需要的列
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            print(f"    ✓ Tushare 获取 {len(df)} 条数据")
            return df
        
        return None
        
    except ImportError:
        print(f"    ⚠ Tushare: 未安装 tushare 库 (pip install tushare)")
        return None
    except Exception as e:
        print(f"    ⚠ Tushare: 获取失败 - {str(e)[:50]}")
        return None


def fetch_from_akshare(symbol):
    """从 AKShare 获取数据
    
    AKShare 是一个完全免费的开源财经数据接口库
    支持 A 股、港股、美股、期货、期权等多种数据
    
    Args:
        symbol: 股票代码，如 '000001.SS', '0700.HK', 'AAPL'
        
    Returns:
        DataFrame: 包含 OHLCV 数据的 DataFrame，获取失败返回 None
        
    Note:
        - 完全免费，无需 token
        - 需要安装 akshare 库：pip install akshare
        - 数据源来自新浪财经、东方财富等公开数据
    """
    try:
        import akshare as ak
        import pandas as pd
        
        # 转换股票代码格式
        clean_symbol = symbol.replace('.SS', '').replace('.SZ', '').replace('.HK', '')
        
        # 根据股票代码类型选择不同的 AKShare 接口
        try:
            if symbol.endswith('.SS') or symbol.endswith('.SZ'):
                # A 股数据 - 使用 stock_zh_a_hist
                df = ak.stock_zh_a_hist(
                    symbol=clean_symbol,
                    period="daily",
                    start_date="20200101",
                    adjust="qfq"  # 前复权
                )
            elif symbol.endswith('.HK'):
                # 港股数据 - 使用 stock_hk_daily
                df = ak.stock_hk_daily(symbol=clean_symbol, adjust="qfq")
            else:
                # 美股数据 - 使用 stock_us_hist
                df = ak.stock_us_hist(
                    symbol=clean_symbol,
                    period="daily",
                    start_date="20200101",
                    adjust="qfq"
                )
            
            if df is not None and len(df) > 0:
                # 重命名列以匹配系统格式
                # AKShare 返回的列名可能是中文，需要转换
                column_mapping = {
                    '日期': 'Date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount'
                }
                
                # 尝试中文列名映射
                for cn, en in column_mapping.items():
                    if cn in df.columns:
                        df = df.rename(columns={cn: en})
                
                # 如果已经有英文列名，直接使用
                if 'Date' not in df.columns and 'date' in df.columns:
                    df = df.rename(columns={'date': 'Date'})
                if 'open' not in df.columns and 'Open' in df.columns:
                    df = df.rename(columns={'Open': 'open'})
                if 'close' not in df.columns and 'Close' in df.columns:
                    df = df.rename(columns={'Close': 'close'})
                if 'high' not in df.columns and 'High' in df.columns:
                    df = df.rename(columns={'High': 'high'})
                if 'low' not in df.columns and 'Low' in df.columns:
                    df = df.rename(columns={'Low': 'low'})
                if 'volume' not in df.columns and 'Volume' in df.columns:
                    df = df.rename(columns={'Volume': 'volume'})
                
                # 设置日期索引
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.set_index('Date')
                    df = df.sort_index()
                
                # 选择需要的列
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                available_cols = [c for c in required_cols if c in df.columns]
                
                if len(available_cols) >= 4:  # 至少有 OHLC
                    df = df[available_cols]
                    # 如果缺少成交量，填充为 1
                    if 'volume' not in df.columns:
                        df['volume'] = 1
                    
                    print(f"    ✓ AKShare 获取 {len(df)} 条数据")
                    return df
        
        except Exception as inner_e:
            print(f"    ⚠ AKShare: 特定接口失败 - {str(inner_e)[:50]}")
            return None
        
        return None
        
    except ImportError:
        print(f"    ⚠ AKShare: 未安装 akshare 库 (pip install akshare)")
        return None
    except Exception as e:
        print(f"    ⚠ AKShare: 获取失败 - {str(e)[:50]}")
        return None


def fetch_stock_data_multi_source(symbol):
    """多数据源获取股票数据
    
    按优先级尝试多个数据源：
    1. 本地缓存（最快，避免重复请求）
    2. Alpha Vantage API（美股数据质量好）
    3. Tushare（A 股数据，需要 token）
    4. AKShare（免费，支持多市场）
    5. 新浪 API（备用）
    6. 模拟数据（最后备用）
    
    Args:
        symbol: 股票代码，如 'AAPL', '000001.SS', '0700.HK'
        
    Returns:
        DataFrame: 包含 OHLCV 数据的历史数据
        
    Note:
        - 所有数据源都是可选的，未安装库不报错
        - 优先使用缓存，减少 API 请求
        - 自动降级到备用数据源
    """
    # 初始化缓存
    cache = DataCache()
    
    # Step 1: 检查缓存
    cached_data = cache.load(symbol)
    if cached_data is not None and not cache.needs_update(symbol, max_age_days=1):
        print(f"    ✓ 从缓存加载数据：{symbol} ({len(cached_data)} 条)")
        return cached_data
    
    print(f"    多数据源获取：{symbol}")
    
    # Step 2: 尝试 Alpha Vantage（优先美股）
    try:
        print(f"    → 尝试 Alpha Vantage API...")
        import requests
        
        clean_symbol = symbol.replace('.SS', '').replace('.SZ', '').replace('.HK', '')
        
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': clean_symbol,
            'outputsize': 'compact',
            'apikey': ALPHA_VANTAGE_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        if 'Time Series (Daily)' in data:
            ts = data['Time Series (Daily)']
            if ts:
                dates = sorted(ts.keys(), reverse=True)
                df_data = []
                for d in dates:
                    day = ts[d]
                    df_data.append({
                        'open': float(day['1. open']),
                        'high': float(day['2. high']),
                        'low': float(day['3. low']),
                        'close': float(day['4. close']),
                        'volume': int(day['5. volume'])
                    })
                
                df = pd.DataFrame(df_data, index=pd.to_datetime(dates))
                df.index.name = 'Date'
                df = df.sort_index()
                df.columns = [c.lower() for c in df.columns]
                
                print(f"    ✓ Alpha Vantage 获取 {len(df)} 条数据")
                cache.save(symbol, df)
                return df
                    
        if 'Note' in data:
            print(f"    ⚠ API 限制：{data['Note'][:50]}")
        elif 'Information' in data:
            print(f"    ⚠ API 信息：{data['Information'][:50]}")
            
    except Exception as e:
        print(f"    ⚠ Alpha Vantage 失败：{str(e)[:50]}")
    
    # Step 3: 尝试 Tushare（A 股专用）
    if symbol.endswith('.SS') or symbol.endswith('.SZ'):
        print(f"    → 尝试 Tushare (A 股)...")
        df = fetch_from_tushare(symbol)
        if df is not None:
            cache.save(symbol, df)
            return df
    
    # Step 4: 尝试 AKShare（免费多市场）
    print(f"    → 尝试 AKShare...")
    df = fetch_from_akshare(symbol)
    if df is not None:
        cache.save(symbol, df)
        return df
    
    # Step 5: 尝试新浪 API（备用）
    print(f"    → 尝试新浪 API...")
    df = fetch_from_sina(symbol)
    if df is not None and len(df) > 0:
        cache.save(symbol, df)
        return df
    
    # Step 6: 使用模拟数据（最后备用）
    print(f"    → 使用模拟数据...")
    df = generate_simulated_data(100, symbol)
    cache.save(symbol, df)
    
    return df


def fetch_stock_data(symbol, period='2y'):
    """获取股票数据 - 使用多数据源策略（向后兼容）
    
    这是旧版本的接口，现在内部调用 fetch_stock_data_multi_source
    保持向后兼容，确保现有代码不报错
    
    Args:
        symbol: 股票代码
        period: 数据周期（保留参数，暂未使用）
        
    Returns:
        DataFrame: 股票历史数据
    """
    # 调用新的多数据源函数
    return fetch_stock_data_multi_source(symbol)


def fetch_from_sina(symbol):
    """从新浪 API 获取数据"""
    import requests
    
    # 转换股票代码格式
    if symbol.endswith('.SS'):
        code = 'sh' + symbol.replace('.SS', '')
    elif symbol.endswith('.SZ'):
        code = 'sz' + symbol.replace('.SZ', '')
    elif symbol.endswith('.HK'):
        code = 'hk' + symbol.replace('.HK', '')
    else:
        # 假设是美股
        code = symbol
    
    try:
        url = f"http://hq.sinajs.cn/list={code}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            content = response.text
            if 'var hq_str' in content:
                # 解析数据
                parts = content.split('=')[1].split(',')
                if len(parts) > 5:
                    # 生成模拟历史数据
                    close_price = float(parts[1])
                    return generate_simulated_data(close_price, symbol)
    except:
        pass
    
    # 没有真实数据可用，返回None
    print(f"    → 无法获取 {symbol} 的真实数据")
    return None


def generate_simulated_data(base_price, symbol, n_days=500):
    """已废弃 - 不再使用模拟数据
    如需测试，请使用真实数据源"""
    print(f"警告: generate_simulated_data 已废弃，请使用真实数据")
    return None


def run_dss_analysis(symbols=None, 
                     use_probability_calibration=True,
                     use_confidence_filter=True,
                     test_lightgbm=True):
    """运行完整的 DSS 分析流程（v2.0 第 4 周增强版）
    
    第 4 周新增功能:
    - 多数据源支持 (Tushare, AKShare, Alpha Vantage)
    - 市场状态识别 (MarketRegimeDetector)
    - 数据质量检查增强 (DataQualityChecker)
    - 扩展测试股票池 (美股/A 股/港股)
    
    第 3 周功能:
    - 概率校准 (Platt Scaling)
    - 置信度阈值过滤 (65% 置信度)
    - LightGBM 模型支持
    - 改进的风险管理
    
    Args:
        symbols: 股票代码列表，默认使用 DEFAULT_SYMBOLS 的前 6 只
        use_probability_calibration: 是否使用概率校准
        use_confidence_filter: 是否使用置信度过滤
        test_lightgbm: 是否测试 LightGBM 模型
    """
    if symbols is None:
        symbols = DEFAULT_SYMBOLS[:6]
    
    print("=" * 70)
    print("DSS 股票分析系统 v2.0 - 第 4 周增强版")
    print("=" * 70)
    print(f"分析股票池：{len(symbols)} 只股票")
    print(f"功能配置:")
    print(f"  - 多数据源支持：启用 (Alpha Vantage / Tushare / AKShare)")
    print(f"  - 市场状态识别：启用")
    print(f"  - 数据质量检查：启用")
    print(f"  - 概率校准：{'启用' if use_probability_calibration else '禁用'}")
    print(f"  - 置信度过滤：{'启用' if use_confidence_filter else '禁用'} (阈值=0.65)")
    print(f"  - LightGBM 模型：{'启用' if test_lightgbm else '禁用'}")
    print("=" * 70)
    
    results_summary = {}
    
    for symbol in symbols:
        print(f"\n{'='*70}")
        print(f"分析：{symbol}")
        print("=" * 70)
        
        # Step 1: 获取数据（多数据源）
        print("\n[1/8] 获取股票数据（多数据源）...")
        df = fetch_stock_data_multi_source(symbol)
        
        if df is None or len(df) == 0:
            print(f"  ⚠️ 跳过 {symbol} - 无法获取数据")
            continue
        
        # 统一列名为小写
        df.columns = [c.lower() for c in df.columns]
        
        print(f"    数据量：{len(df)} 条")
        print(f"    时间范围：{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
        
        # Step 2: 数据质量检查
        print("\n[2/8] 数据质量检查...")
        quality_checker = DataQualityChecker(std_threshold=5, gap_threshold_days=7)
        quality_report = quality_checker.full_check(df)
        
        # 如果质量太差，发出警告但继续
        if quality_report['quality_score'] < 60:
            print(f"    ⚠ 数据质量较低，结果仅供参考")
        
        # Step 3: 市场状态识别
        print("\n[3/8] 市场状态识别...")
        regime_detector = MarketRegimeDetector(volatility_window=20, trend_window=60)
        regime_result = regime_detector.detect_with_confidence(df['close'])
        
        regime = regime_result['regime']
        confidence = regime_result['confidence']
        metrics = regime_result['metrics']
        
        regime_names = {
            'bull': '🐂 牛市',
            'bear': '🐻 熊市',
            'sideways': '➡️ 震荡市',
            'volatile': '📊 高波动市'
        }
        
        print(f"    当前市场状态：{regime_names.get(regime, regime)}")
        print(f"    置信度：{confidence:.1%}")
        print(f"    波动率：{metrics['volatility']:.1%} (年化)")
        print(f"    趋势强度：{metrics['trend_strength']:.2%}")
        
        # Step 4: 特征工程
        print("\n[4/8] 生成技术指标特征...")
        fe = FeatureEngineer()
        features = fe.create_all_features(df)
        print(f"    生成特征数：{len(features.columns)}")
        
        # Step 4: 创建目标变量
        # 目标变量：预测下一天的收益率
        target = df['close'].pct_change().shift(-1)
        
        # 清理数据
        valid_idx = ~(features.isna().any(axis=1) | target.isna())
        features = features[valid_idx]
        target = target[valid_idx]
        prices = df['close'][valid_idx]
        
        # 创建二分类目标（用于概率校准）
        # 1 表示上涨，0 表示下跌或持平
        target_binary = (target > 0).astype(int)
        
        print(f"    有效样本：{len(features)}")
        
        # Step 5: Walk Forward 验证 - 多模型对比（包含 LightGBM）
        print("\n[5/8] 执行 Walk Forward 滚动验证...")
        
        models = {
            'XGBoost': (XGBoostModel, {'n_estimators': 100, 'max_depth': 5, 'learning_rate': 0.1}),
            'RandomForest': (RandomForestModel, {'n_estimators': 100, 'max_depth': 10}),
            'LSTM': (LSTMModel, {'window': 10})
        }
        
        # 添加 LightGBM 模型
        if test_lightgbm:
            models['LightGBM'] = (LightGBMModel, {'n_estimators': 100, 'max_depth': 5, 'learning_rate': 0.1})
        
        model_results = {}
        
        for model_name, (model_class, model_params) in models.items():
            print(f"\n    模型：{model_name}")
            
            # 根据数据量自适应调整 Walk Forward 参数
            n_samples = len(features)
            if n_samples < 300:
                # 小数据集：使用更小的训练窗口
                train_days = min(150, n_samples // 2)
                val_days = min(20, n_samples // 6)
                test_days = 5
            else:
                train_days = 252
                val_days = 21
                test_days = 5
            
            wf = WalkForwardValidator(train_days=train_days, val_days=val_days, test_days=test_days)
            
            try:
                result = wf.rolling_validate(features, target, model_class, model_params)
                model_results[model_name] = result
                
                print(f"      预测样本：{result['metrics']['num_predictions']}")
                print(f"      方向准确率：{result['metrics']['direction_accuracy_pct']:.2%}")
                print(f"      MAE: {result['metrics']['mae']:.6f}")
                
            except Exception as e:
                print(f"      错误：{e}")
                import traceback
                traceback.print_exc()
        
        # Step 6: 概率校准与信号生成
        print("\n[6/8] 概率校准与信号生成...")
        
        # 找到最佳模型
        best_model = max(model_results.items(), key=lambda x: x[1]['metrics']['direction_accuracy_pct'])
        best_model_name = best_model[0]
        best_result = best_model[1]
        
        print(f"    最佳模型：{best_model_name} (方向准确率：{best_result['metrics']['direction_accuracy_pct']:.2%})")
        
        # 使用概率校准器
        predictions = np.array(best_result['predictions'])
        probabilities = None
        
        if use_probability_calibration:
            print("    应用概率校准 (Platt Scaling)...")
            calibrator = ProbabilityCalibrator()
            
            # 使用二分类目标训练校准器
            # 将预测值转换为二分类概率（简单方法：基于预测值的符号和幅度）
            pred_proba_raw = 1 / (1 + np.exp(-predictions * 100))  # Sigmoid 转换
            
            # 获取对应的真实标签
            actuals = np.array(best_result['actuals'])
            y_true_binary = (actuals > 0).astype(int)
            
            # 训练校准器
            calibrator.fit(pred_proba_raw, y_true_binary)
            
            # 获取校准后的概率
            probabilities = calibrator.predict_proba(pred_proba_raw)
            print(f"    校准后平均置信度：{np.mean(probabilities):.2%}")
        
        # 生成交易信号
        if use_confidence_filter and probabilities is not None:
            print("    应用置信度阈值过滤...")
            sg = SignalGenerator(
                buy_threshold=0.01, 
                sell_threshold=-0.01,
                confidence_threshold=0.65  # 仅 65% 以上置信度时交易
            )
            signals = sg.generate_with_confidence(predictions, probabilities)
        else:
            sg = SignalGenerator(buy_threshold=0.01, sell_threshold=-0.01)
            signals = sg.generate(predictions)
            print(f"    买入信号：{np.sum(signals == 1)}")
            print(f"    卖出信号：{np.sum(signals == -1)}")
        
        # Step 7: 运行回测（带风险管理）
        print("\n[7/8] 运行回测（带风险管理）...")
        
        # 初始化风险管理器
        risk_manager = RiskManager(
            stop_loss=0.05,      # 5% 止损
            take_profit=0.10,    # 10% 止盈
            max_position=0.5     # 最大 50% 仓位
        )
        
        # 运行带风险管理的回测
        bt = Backtester(
            initial_capital=100000, 
            transaction_cost=0.001, 
            slippage=0.0005,
            risk_manager=risk_manager
        )
        
        # 使用新的 run_with_risk_management 方法
        backtest_results = bt.run_with_risk_management(
            prices.iloc[-len(signals):], 
            signals,
            predictions=predictions,
            probabilities=probabilities
        )
        
        print(f"\n    回测结果:")
        print(f"    总收益：{backtest_results['total_return']:.2%}")
        print(f"    夏普比率：{backtest_results['sharpe_ratio']:.2f}")
        print(f"    最大回撤：{backtest_results['max_drawdown']:.2%}")
        print(f"    最终资产：¥{backtest_results['final_value']:,.2f}")
        print(f"    交易次数：{backtest_results['num_trades']}")
        
        results_summary[symbol] = {
            'best_model': best_model_name,
            'metrics': best_result['metrics'],
            'backtest': backtest_results,
            'config': {
                'probability_calibration': use_probability_calibration,
                'confidence_filter': use_confidence_filter,
                'lightgbm_tested': test_lightgbm
            }
        }
    
    # Step 8: 打印汇总
    print("\n[8/8] 生成分析报告...")
    print("\n" + "=" * 70)
    print("📊 多股票分析汇总 (第 4 周增强版)")
    print("=" * 70)
    
    for symbol, result in results_summary.items():
        print(f"\n{symbol}:")
        print(f"  最佳模型：{result['best_model']}")
        print(f"  方向准确率：{result['metrics']['direction_accuracy_pct']:.2%}")
        print(f"  总收益：{result['backtest']['total_return']:.2%}")
        print(f"  夏普比率：{result['backtest']['sharpe_ratio']:.2f}")
        print(f"  最大回撤：{result['backtest']['max_drawdown']:.2%}")
        config = result.get('config', {})
        if config.get('probability_calibration'):
            print(f"  ✓ 使用概率校准")
        if config.get('confidence_filter'):
            print(f"  ✓ 使用置信度过滤 (65%)")
        if config.get('lightgbm_tested'):
            print(f"  ✓ 测试 LightGBM 模型")
    
    print("\n" + "=" * 70)
    print("✅ 分析完成! (第 4 周增强版)")
    print("=" * 70)
    
    return results_summary


# ==================== 扩展测试股票池 (P2) ====================

# 默认测试股票列表 - 覆盖美股、A 股、港股
DEFAULT_SYMBOLS = [
    # 美股 (US Stocks)
    'AAPL',       # 苹果公司
    'GOOGL',      # 谷歌
    'MSFT',       # 微软
    'AMZN',       # 亚马逊
    'TSLA',       # 特斯拉
    'NVDA',       # 英伟达
    
    # A 股指数 (A-Share Indices)
    '000001.SS',  # 上证指数
    '399001.SZ',  # 深证成指
    '399006.SZ',  # 创业板指
    
    # A 股个股 (A-Share Stocks) - 代表性股票
    '600519.SS',  # 贵州茅台
    '000858.SZ',  # 五粮液
    '601318.SS',  # 中国平安
    
    # 港股 (HK Stocks)
    '0700.HK',    # 腾讯控股
    '9988.HK',    # 阿里巴巴
    '3690.HK',    # 美团
    '1024.HK',    # 快手
]


# 如果直接运行此文件
if __name__ == '__main__':
    import sys
    
    # 默认分析股票列表 - 使用扩展后的股票池
    default_symbols = DEFAULT_SYMBOLS[:6]  # 默认使用前 6 只股票（避免过多）
    
    # 解析命令行选项
    use_calibration = True
    use_confidence = True
    test_lgbm = True
    
    # 提取股票代码和选项
    symbols = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--no-calibration':
            use_calibration = False
        elif arg == '--no-confidence':
            use_confidence = False
        elif arg == '--no-lightgbm':
            test_lgbm = False
        elif not arg.startswith('-'):
            symbols.append(arg)
        i += 1
    
    if not symbols:
        symbols = default_symbols
    
    print(f"将分析以下股票：{symbols}")
    print(f"功能选项:")
    print(f"  - 概率校准：{'启用' if use_calibration else '禁用'}")
    print(f"  - 置信度过滤：{'启用' if use_confidence else '禁用'}")
    print(f"  - LightGBM: {'启用' if test_lgbm else '禁用'}")
    print()
    
    # 运行分析
    run_dss_analysis(
        symbols=symbols,
        use_probability_calibration=use_calibration,
        use_confidence_filter=use_confidence,
        test_lightgbm=test_lgbm
    )
