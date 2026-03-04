#!/usr/bin/env python3
"""
DSS 日志系统测试脚本

测试内容：
1. 数据源追踪 - 成功/失败/缓存的数据都记录来源
2. 参数权重日志 - 记录最优解搜索过程
3. 真实数据原则 - 获取不到就不伪造
"""

from dss_logger import get_data_tracker, get_weight_logger
from dss_v2 import fetch_stock_data_multi_source, DataCache

def test_data_source_tracking():
    """测试数据源追踪"""
    print("=" * 70)
    print("测试 1: 数据源追踪")
    print("=" * 70)
    
    tracker = get_data_tracker()
    
    # 测试 1: 缓存数据
    print("\n1.1 测试缓存数据...")
    cache = DataCache()
    cached_data = cache.load('AAPL')
    if cached_data is not None:
        tracker.record_source(
            data_id='AAPL',
            source_type='Cache',
            source_url='N/A',
            source_name='本地缓存 (data_cache/stock_data.csv)',
            data_status='cached',
            metadata={'records': len(cached_data), 'cache_date': '2026-02-27'}
        )
    
    # 测试 2: API 成功
    print("1.2 测试 API 成功场景...")
    tracker.record_source(
        data_id='MSFT',
        source_type='AlphaVantage',
        source_url='https://www.alphavantage.co/query?function=TIME_SERIES_DAILY',
        source_name='Alpha Vantage API',
        data_status='success',
        metadata={'records': 100, 'period': '2y'}
    )
    
    # 测试 3: API 失败（不伪造）
    print("1.3 测试 API 失败场景（不伪造数据）...")
    tracker.record_source(
        data_id='AMZN',
        source_type='AlphaVantage',
        source_url='https://www.alphavantage.co/query?function=TIME_SERIES_DAILY',
        source_name='Alpha Vantage API',
        data_status='failed',
        error_message='API 限制：感谢使用 Alpha Vantage，请考虑付费套餐',
        metadata={'attempted_at': '2026-02-28T18:40:00'}
    )
    
    # 测试 4: 数据不可用（明确标注）
    print("1.4 测试数据不可用场景...")
    tracker.record_source(
        data_id='UNKNOWN',
        source_type='Multiple',
        source_url='N/A',
        source_name='Alpha Vantage / AKShare / Sina (全部失败)',
        data_status='unavailable',
        error_message='所有数据源均无法获取真实数据',
        metadata={'attempted_sources': ['Alpha Vantage', 'AKShare', 'Sina']}
    )
    
    # 生成报告
    print("\n" + tracker.generate_report())


def test_weight_logging():
    """测试参数权重日志"""
    print("\n" + "=" * 70)
    print("测试 2: 参数权重日志")
    print("=" * 70)
    
    logger = get_weight_logger()
    
    # 初始化权重
    print("\n2.1 初始化权重配置...")
    logger.initialize_weights(
        weights={
            'rsi_weight': 0.25,
            'macd_weight': 0.25,
            'volume_weight': 0.20,
            'trend_weight': 0.20,
            'volatility_weight': 0.10
        },
        description="DSS v2.0 - 均衡型配置"
    )
    
    # 模拟参数调整过程
    print("2.2 模拟参数调整（寻找最优解）...")
    
    # 调整 1: 增加 RSI 权重
    logger.adjust_weight(
        param_name='rsi_weight',
        old_value=0.25,
        new_value=0.30,
        reason='RSI 在震荡市场表现更好',
        performance_impact=0.0123
    )
    
    # 调整 2: 减少 MACD 权重
    logger.adjust_weight(
        param_name='macd_weight',
        old_value=0.25,
        new_value=0.20,
        reason='MACD 在低波动市场信号较弱',
        performance_impact=-0.0056
    )
    
    # 调整 3: 增加成交量权重
    logger.adjust_weight(
        param_name='volume_weight',
        old_value=0.20,
        new_value=0.25,
        reason='成交量放大时预测准确率更高',
        performance_impact=0.0089
    )
    
    # 记录评估结果
    print("2.3 记录评估结果...")
    logger.record_evaluation(
        weights=logger.current_weights,
        metrics={
            'accuracy': 0.72,
            'sharpe_ratio': 1.85,
            'max_drawdown': -0.15,
            'win_rate': 0.68
        },
        is_best=True
    )
    
    # 生成报告
    print("\n" + logger.generate_report())


def test_real_data_fetch():
    """测试真实数据获取 + 日志"""
    print("\n" + "=" * 70)
    print("测试 3: 真实数据获取 + 日志")
    print("=" * 70)
    
    tracker = get_data_tracker()
    
    # 测试真实数据获取
    print("\n3.1 获取 AAPL 数据...")
    df = fetch_stock_data_multi_source('AAPL', track_source=True)
    if df is not None:
        print(f"   ✅ 成功获取 {len(df)} 条数据")
    else:
        print(f"   ⚠️ 无法获取数据")
    
    print("\n3.2 获取 NVDA 数据...")
    df = fetch_stock_data_multi_source('NVDA', track_source=True)
    if df is not None:
        print(f"   ✅ 成功获取 {len(df)} 条数据")
    else:
        print(f"   ⚠️ 无法获取数据")
    
    # 生成最终报告
    print("\n" + tracker.generate_report())


if __name__ == "__main__":
    print("🧪 DSS 日志系统测试\n")
    
    test_data_source_tracking()
    test_weight_logging()
    test_real_data_fetch()
    
    print("\n" + "=" * 70)
    print("✅ 所有测试完成！")
    print("=" * 70)
    print("\n日志文件位置:")
    print("  - 数据源日志：./data_logs/sources_*.jsonl")
    print("  - 权重日志：./weight_logs/adjustments_*.jsonl")
    print("\n原则确认:")
    print("  ❌ 不允许伪造数据 - 获取不到就明确标注")
    print("  ✅ 所有数据标注真实来源 URL")
    print("  ✅ 记录所有参数调整和权重变化")
    print("  ✅ 可追溯、可审计、可复现")
