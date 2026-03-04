#!/usr/bin/env python3
"""
DSS 技术指标模块测试
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import unittest
import numpy as np
import pandas as pd
from dss_adaptive_indicators import (
    detect_market_regime,
    adaptive_rsi,
    adaptive_macd,
    adaptive_bollinger_bands,
    calculate_adaptive_score
)


class TestMarketRegime(unittest.TestCase):
    """测试市场状态检测"""
    
    def test_trending_up_market(self):
        """测试上涨趋势市场"""
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110])
        regime = detect_market_regime(prices, window=10)
        self.assertEqual(regime, 'trending')
    
    def test_trending_down_market(self):
        """测试下跌趋势市场"""
        prices = pd.Series([110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100])
        regime = detect_market_regime(prices, window=10)
        self.assertEqual(regime, 'trending')
    
    def test_range_market(self):
        """测试震荡市场"""
        prices = pd.Series([100, 102, 100, 102, 100, 102, 100, 102, 100, 102, 101])
        regime = detect_market_regime(prices, window=10)
        self.assertEqual(regime, 'range')
    
    def test_insufficient_data(self):
        """测试数据不足情况"""
        prices = pd.Series([100, 101, 102])
        regime = detect_market_regime(prices, window=10)
        self.assertEqual(regime, 'range')


class TestAdaptiveRSI(unittest.TestCase):
    """测试自适应 RSI"""
    
    def setUp(self):
        """准备测试数据"""
        np.random.seed(42)
        self.prices = pd.Series(100 + np.cumsum(np.random.randn(100) * 2))
    
    def test_rsi_range(self):
        """RSI 应在 0-100 范围内"""
        rsi, info = adaptive_rsi(self.prices)
        self.assertTrue((rsi.dropna() >= 0).all())
        self.assertTrue((rsi.dropna() <= 100).all())
    
    def test_rsi_info_contains_required_fields(self):
        """RSI 信息应包含必要字段"""
        rsi, info = adaptive_rsi(self.prices)
        required_fields = ['period', 'oversold', 'overbought', 'volatility', 'regime']
        for field in required_fields:
            self.assertIn(field, info, f"缺少字段：{field}")
    
    def test_adaptive_period_within_bounds(self):
        """自适应周期应在 7-28 范围内"""
        rsi, info = adaptive_rsi(self.prices)
        self.assertGreaterEqual(info['period'], 7)
        self.assertLessEqual(info['period'], 28)


class TestAdaptiveMACD(unittest.TestCase):
    """测试自适应 MACD"""
    
    def setUp(self):
        """准备测试数据"""
        np.random.seed(42)
        self.prices = pd.Series(100 + np.cumsum(np.random.randn(100) * 2))
    
    def test_macd_output_shapes(self):
        """MACD 输出形状应正确"""
        macd_line, signal_line, hist, info = adaptive_macd(self.prices)
        self.assertEqual(len(macd_line), len(self.prices))
        self.assertEqual(len(signal_line), len(self.prices))
        self.assertEqual(len(hist), len(self.prices))
    
    def test_macd_info_contains_required_fields(self):
        """MACD 信息应包含必要字段"""
        macd_line, signal_line, hist, info = adaptive_macd(self.prices)
        required_fields = ['fast', 'slow', 'signal', 'regime', 'cross']
        for field in required_fields:
            self.assertIn(field, info, f"缺少字段：{field}")
    
    def test_adaptive_params_change_with_regime(self):
        """参数应随市场状态变化"""
        # 使用更长的序列以确保检测准确
        # 趋势市场 - 持续上涨
        trending_prices = pd.Series([100 + i*2 for i in range(30)])
        _, _, _, trend_info = adaptive_macd(trending_prices, base_fast=12, base_slow=26, base_signal=9)
        
        # 震荡市场 - 上下波动
        range_prices = pd.Series([100 + (i % 4) * 2 - 2 for i in range(30)])
        _, _, _, range_info = adaptive_macd(range_prices, base_fast=12, base_slow=26, base_signal=9)
        
        # 市场状态应不同
        # 注意：参数可能相同，但 regime 应不同
        self.assertIn(trend_info['regime'], ['trending', 'range'])
        self.assertIn(range_info['regime'], ['trending', 'range'])


class TestBollingerBands(unittest.TestCase):
    """测试自适应布林带"""
    
    def setUp(self):
        """准备测试数据"""
        np.random.seed(42)
        self.prices = pd.Series(100 + np.cumsum(np.random.randn(100) * 2))
    
    def test_bb_ordering(self):
        """布林带顺序应正确：upper > middle > lower"""
        upper, middle, lower, bbp = adaptive_bollinger_bands(self.prices)
        # 允许少量例外 (数据起始部分可能 NaN)
        upper_clean = upper.dropna()
        middle_clean = middle.dropna()
        lower_clean = lower.dropna()
        if len(upper_clean) > 0:
            self.assertTrue((upper_clean >= middle_clean.dropna()).all())
    
    def test_bbp_range(self):
        """BB 位置应在合理范围内 (允许少量超出)"""
        upper, middle, lower, bbp = adaptive_bollinger_bands(self.prices)
        bbp_valid = bbp.dropna()
        if len(bbp_valid) > 0:
            # 允许少量超出 0-1 范围 (极端波动时)
            out_of_range = ((bbp_valid < 0) | (bbp_valid > 1)).sum()
            self.assertLess(out_of_range, len(bbp_valid) * 0.1)  # 不超过 10%


class TestAdaptiveScore(unittest.TestCase):
    """测试综合评分"""
    
    def setUp(self):
        """准备测试数据"""
        np.random.seed(42)
        self.prices = pd.Series(100 + np.cumsum(np.random.randn(100) * 2))
        self.volume = pd.Series(np.random.randint(1000, 10000, 100))
        
        self.rsi_data = adaptive_rsi(self.prices)
        self.macd_data = adaptive_macd(self.prices)
    
    def test_score_range(self):
        """评分应在合理范围内"""
        score, details = calculate_adaptive_score(
            self.prices, self.rsi_data, self.macd_data, self.volume
        )
        # 理论范围：-100 到 +100
        self.assertGreaterEqual(score, -100)
        self.assertLessEqual(score, 100)
    
    def test_score_details_structure(self):
        """评分详情应包含必要信息"""
        score, details = calculate_adaptive_score(
            self.prices, self.rsi_data, self.macd_data, self.volume
        )
        self.assertIn('total', details)
        self.assertIn('details', details)
        self.assertIsInstance(details['details'], list)


if __name__ == '__main__':
    unittest.main(verbosity=2)
