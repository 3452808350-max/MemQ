#!/usr/bin/env python3
"""
DSS v2.0 第 3 周升级测试脚本
测试新增功能:
1. 概率校准器 (ProbabilityCalibrator)
2. 置信度阈值过滤 (SignalGenerator.generate_with_confidence)
3. LightGBM 模型 (LightGBMModel)
4. 改进止损机制 (Backtester.run_with_risk_management)
"""

import numpy as np
import pandas as pd
import sys

# 导入 DSS 模块
from dss_v2 import (
    ProbabilityCalibrator,
    SignalGenerator,
    LightGBMModel,
    Backtester,
    RiskManager,
    XGBoostModel,
    FeatureEngineer,
    RANDOM_SEED
)

def test_probability_calibrator():
    """测试概率校准器"""
    print("=" * 60)
    print("测试 1: 概率校准器 (ProbabilityCalibrator)")
    print("=" * 60)
    
    # 创建模拟数据
    np.random.seed(RANDOM_SEED)
    n_samples = 100
    
    # 模拟模型预测概率 (0-1 之间)
    y_pred_proba = np.random.rand(n_samples)
    
    # 模拟真实标签 (0 或 1)
    # 让真实标签与预测概率有一定相关性
    y_true = (y_pred_proba + np.random.randn(n_samples) * 0.2 > 0.5).astype(int)
    
    # 创建校准器并训练
    calibrator = ProbabilityCalibrator()
    calibrator.fit(y_pred_proba, y_true)
    
    # 获取校准后的概率
    calibrated_proba = calibrator.predict_proba(y_pred_proba)
    
    print(f"  原始概率范围：[{y_pred_proba.min():.3f}, {y_pred_proba.max():.3f}]")
    print(f"  校准后概率范围：[{calibrated_proba.min():.3f}, {calibrated_proba.max():.3f}]")
    print(f"  原始概率均值：{y_pred_proba.mean():.3f}")
    print(f"  校准后概率均值：{calibrated_proba.mean():.3f}")
    print(f"  真实标签正类比例：{y_true.mean():.3f}")
    
    # 验证校准器是否正常工作
    assert calibrated_proba is not None
    assert len(calibrated_proba) == n_samples
    assert np.all((calibrated_proba >= 0) & (calibrated_proba <= 1))
    
    print("  ✓ 概率校准器测试通过\n")
    return True


def test_confidence_filter():
    """测试置信度阈值过滤"""
    print("=" * 60)
    print("测试 2: 置信度阈值过滤 (SignalGenerator)")
    print("=" * 60)
    
    # 创建信号生成器
    sg = SignalGenerator(
        buy_threshold=0.01,
        sell_threshold=-0.01,
        confidence_threshold=0.65
    )
    
    # 模拟预测值和概率
    predictions = np.array([0.02, 0.015, -0.02, 0.005, -0.015, 0.03])
    probabilities = np.array([0.70, 0.50, 0.80, 0.90, 0.60, 0.75])
    
    # 生成带置信度过滤的信号
    signals = sg.generate_with_confidence(predictions, probabilities)
    
    print(f"  预测值：{predictions}")
    print(f"  置信度：{probabilities}")
    print(f"  生成信号：{signals}")
    
    # 验证结果
    # 索引 0: pred=0.02>0.01, prob=0.70>=0.65 → 买入 (1)
    # 索引 1: pred=0.015>0.01, prob=0.50<0.65 → 持有 (0) [置信度不足]
    # 索引 2: pred=-0.02<-0.01, prob=0.80>=0.65 → 卖出 (-1)
    # 索引 3: pred=0.005 未达阈值 → 持有 (0)
    # 索引 4: pred=-0.015<-0.01, prob=0.60<0.65 → 持有 (0) [置信度不足]
    # 索引 5: pred=0.03>0.01, prob=0.75>=0.65 → 买入 (1)
    
    expected_signals = np.array([1, 0, -1, 0, 0, 1])
    
    print(f"  期望信号：{expected_signals}")
    
    assert np.array_equal(signals, expected_signals), f"信号不匹配：{signals} != {expected_signals}"
    
    print("  ✓ 置信度阈值过滤测试通过\n")
    return True


def test_lightgbm_model():
    """测试 LightGBM 模型"""
    print("=" * 60)
    print("测试 3: LightGBM 模型 (LightGBMModel)")
    print("=" * 60)
    
    # 创建模拟数据
    np.random.seed(RANDOM_SEED)
    n_samples = 200
    n_features = 10
    
    X = np.random.randn(n_samples, n_features)
    y = np.random.randn(n_samples)
    
    # 创建训练集和验证集
    X_train, X_val = X[:150], X[150:]
    y_train, y_val = y[:150], y[150:]
    
    # 创建 LightGBM 模型
    model = LightGBMModel(
        n_estimators=50,
        max_depth=4,
        learning_rate=0.1,
        early_stopping_rounds=10
    )
    
    # 训练模型
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    # 预测
    predictions = model.predict(X_val)
    
    print(f"  训练样本数：{len(X_train)}")
    print(f"  验证样本数：{len(X_val)}")
    print(f"  特征数：{n_features}")
    print(f"  预测值范围：[{predictions.min():.3f}, {predictions.max():.3f}]")
    print(f"  使用 XGBoost 备用：{model.use_xgboost_fallback}")
    
    # 验证模型是否正常工作
    assert predictions is not None
    assert len(predictions) == len(X_val)
    
    print("  ✓ LightGBM 模型测试通过\n")
    return True


def test_risk_management():
    """测试改进的止损机制"""
    print("=" * 60)
    print("测试 4: 改进止损机制 (Backtester.run_with_risk_management)")
    print("=" * 60)
    
    # 创建模拟价格序列
    np.random.seed(RANDOM_SEED)
    n_days = 100
    
    # 生成有趋势的价格序列
    base_price = 100
    returns = np.random.randn(n_days) * 0.02 + 0.001  # 轻微上涨趋势
    prices = pd.Series(base_price * np.cumprod(1 + returns))
    
    # 创建交易信号
    signals = np.zeros(n_days)
    signals[10] = 1   # 第 10 天买入
    signals[30] = -1  # 第 30 天卖出
    signals[50] = 1   # 第 50 天买入
    signals[80] = -1  # 第 80 天卖出
    
    # 创建风险管理器
    risk_manager = RiskManager(
        stop_loss=0.05,      # 5% 止损
        take_profit=0.10,    # 10% 止盈
        max_position=0.5     # 最大 50% 仓位
    )
    
    # 创建回测器
    bt = Backtester(
        initial_capital=100000,
        transaction_cost=0.001,
        slippage=0.0005,
        risk_manager=risk_manager
    )
    
    # 运行带风险管理的回测
    results = bt.run_with_risk_management(prices, signals)
    
    print(f"  初始资金：¥{bt.initial_capital:,.2f}")
    print(f"  最终资产：¥{results['final_value']:,.2f}")
    print(f"  总收益：{results['total_return']:.2%}")
    print(f"  夏普比率：{results['sharpe_ratio']:.2f}")
    print(f"  最大回撤：{results['max_drawdown']:.2%}")
    print(f"  交易次数：{results['num_trades']}")
    print(f"  风险事件：{len(results.get('risk_events', []))}")
    
    # 验证回测结果
    assert 'total_return' in results
    assert 'sharpe_ratio' in results
    assert 'max_drawdown' in results
    assert 'final_value' in results
    assert 'risk_events' in results
    
    print("  ✓ 改进止损机制测试通过\n")
    return True


def test_risk_manager():
    """测试风险管理器"""
    print("=" * 60)
    print("测试 5: 风险管理器 (RiskManager)")
    print("=" * 60)
    
    rm = RiskManager(stop_loss=0.05, take_profit=0.10, max_position=0.5)
    
    # 测试止损
    should_close, reason = rm.should_close_position(100, 94, 'long')  # 下跌 6%
    assert should_close and reason == 'stop_loss', "止损测试失败"
    print(f"  ✓ 止损测试：买入价 100, 当前价 94 → {reason}")
    
    # 测试止盈
    should_close, reason = rm.should_close_position(100, 111, 'long')  # 上涨 11%
    assert should_close and reason == 'take_profit', "止盈测试失败"
    print(f"  ✓ 止盈测试：买入价 100, 当前价 111 → {reason}")
    
    # 测试持有
    should_close, reason = rm.should_close_position(100, 103, 'long')  # 上涨 3%
    assert not should_close and reason == 'hold', "持有测试失败"
    print(f"  ✓ 持有测试：买入价 100, 当前价 103 → {reason}")
    
    # 测试仓位计算
    position_size = rm.get_position_size(100000, 50)
    expected_shares = (100000 * 0.5) / 50  # 1000 股
    assert position_size == expected_shares, "仓位计算测试失败"
    print(f"  ✓ 仓位计算：资金 10 万，股价 50 → {position_size:.0f} 股 (最大 50% 仓位)")
    
    # 测试风险收益比
    rr_ratio = rm.calculate_risk_reward_ratio(100, 95, 110)
    expected_ratio = 10 / 5  # 2.0
    assert abs(rr_ratio - expected_ratio) < 0.01, "风险收益比测试失败"
    print(f"  ✓ 风险收益比：止损 95, 止盈 110 → {rr_ratio:.2f}")
    
    print("  ✓ 风险管理器测试通过\n")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("DSS v2.0 第 3 周升级 - 功能测试")
    print("=" * 60 + "\n")
    
    tests = [
        ("概率校准器", test_probability_calibrator),
        ("置信度阈值过滤", test_confidence_filter),
        ("LightGBM 模型", test_lightgbm_model),
        ("改进止损机制", test_risk_management),
        ("风险管理器", test_risk_manager),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"  ✗ {test_name} 测试失败：{e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
