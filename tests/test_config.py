#!/usr/bin/env python3
"""
DSS 配置模块测试
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import unittest
from dss_config import WEIGHTS, TRADING, RISK, MODELS, validate_config, get_config_summary


class TestConfigWeights(unittest.TestCase):
    """测试权重配置"""
    
    def test_weights_sum_to_one(self):
        """权重总和应为 1.0"""
        total = sum(WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=2)
    
    def test_all_weights_positive(self):
        """所有权重应为非负数"""
        for name, weight in WEIGHTS.items():
            self.assertGreaterEqual(weight, 0, f"{name} 权重不能为负")
    
    def test_major_weights_present(self):
        """主要权重应存在"""
        required = ['rsi', 'macd', 'ml_predict']
        for key in required:
            self.assertIn(key, WEIGHTS, f"缺少必要权重：{key}")


class TestTradingConfig(unittest.TestCase):
    """测试交易配置"""
    
    def test_stop_loss_positive(self):
        """止损比例应为正数"""
        self.assertGreater(TRADING['stop_loss'], 0)
    
    def test_take_profit_greater_than_stop_loss(self):
        """止盈应大于止损"""
        self.assertGreater(TRADING['take_profit'], TRADING['stop_loss'])
    
    def test_position_limits(self):
        """仓位限制应合理"""
        self.assertLessEqual(TRADING['position_base'], TRADING['max_position'])
        self.assertLess(TRADING['max_position'], 1.0)


class TestRiskConfig(unittest.TestCase):
    """测试风控配置"""
    
    def test_risk_thresholds_order(self):
        """风险阈值顺序应正确"""
        self.assertLess(RISK['low_risk_threshold'], RISK['medium_risk_threshold'])
    
    def test_rsi_levels_valid(self):
        """RSI 水平应有效"""
        self.assertLess(RISK['rsi_oversold'], RISK['rsi_overbought'])
        self.assertGreater(RISK['rsi_oversold'], 0)
        self.assertLess(RISK['rsi_overbought'], 100)


class TestConfigValidation(unittest.TestCase):
    """测试配置验证函数"""
    
    def test_validate_config_returns_list(self):
        """验证函数应返回列表"""
        errors = validate_config()
        self.assertIsInstance(errors, list)
    
    def test_validate_config_passes(self):
        """默认配置应通过验证"""
        errors = validate_config()
        self.assertEqual(len(errors), 0, f"配置验证失败：{errors}")
    
    def test_get_config_summary_returns_dict(self):
        """摘要函数应返回字典"""
        summary = get_config_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn('weights_total', summary)


class TestModelConfig(unittest.TestCase):
    """测试模型配置"""
    
    def test_lstm_params_present(self):
        """LSTM 参数应存在"""
        self.assertIn('lstm', MODELS)
        self.assertIn('seq_length', MODELS['lstm'])
        self.assertIn('hidden_size', MODELS['lstm'])
    
    def test_ml_params_present(self):
        """ML 参数应存在"""
        self.assertIn('ml', MODELS)
        self.assertIn('n_estimators', MODELS['ml'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
