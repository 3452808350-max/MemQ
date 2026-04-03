"""
Factor Validation 使用示例
展示如何在 DSS 中集成 quant 的因子验证方法
"""
import pandas as pd
import numpy as np
from factor_validation import FactorValidator, quick_validate, winsorize


def example_basic_usage():
    """基础用法示例"""
    print("=" * 60)
    print("基础用法示例")
    print("=" * 60)
    
    # 创建模拟数据
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
    
    data = []
    for date in dates:
        # 每天 100 只股票
        for i in range(100):
            factor = np.random.randn()  # 因子值
            # 因子与收益有正相关
            ret = factor * 0.1 + np.random.randn() * 0.5
            data.append({
                'date': date,
                'symbol': f'STOCK_{i:03d}',
                'factor': factor,
                'return': ret / 100  # 转换为收益率
            })
    
    df = pd.DataFrame(data)
    
    # 方法 1: 使用验证器类
    validator = FactorValidator()
    result = validator.validate(df, 'factor', 'return', 'date', 'momentum_factor')
    
    print(f"\n因子名称: {result.factor_name}")
    print(f"IC 均值: {result.ic_mean:.4f}")
    print(f"IC 标准差: {result.ic_std:.4f}")
    print(f"IR: {result.ir:.2f}")
    print(f"多空夏普: {result.sharpe_ls:.2f}")
    print(f"多轨道稳定性: {result.pathway_stability:.2f}")
    print(f"是否通过验证: {result.pass_validation}")
    
    # 方法 2: 快速验证 (一行代码)
    factor_df = df[['date', 'symbol', 'factor']].copy()
    factor_df.rename(columns={'factor': 'factor'}, inplace=True)
    return_df = df[['date', 'symbol', 'return']].copy()
    
    quick_result = quick_validate(factor_df, return_df, 'momentum_factor')
    print(f"\n快速验证结果:")
    print(f"  IR: {quick_result['ir']}")
    print(f"  通过验证: {quick_result['pass_validation']}")


def example_dss_integration():
    """DSS 集成示例"""
    print("\n" + "=" * 60)
    print("DSS 集成示例")
    print("=" * 60)
    
    # 模拟 DSS 的特征和预测结果
    np.random.seed(42)
    
    # 假设我们有 5 个因子
    factors = ['momentum_20', 'volatility_20', 'rsi', 'macd', 'volume_ratio']
    
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
    symbols = [f'STOCK_{i:03d}' for i in range(50)]
    
    # 构建模拟数据
    all_data = []
    for date in dates:
        for symbol in symbols:
            row = {'date': date, 'symbol': symbol}
            
            # 生成 5 个因子值
            for factor in factors:
                row[factor] = np.random.randn()
            
            # 生成下期收益 (与 momentum_20 正相关)
            row['return'] = row['momentum_20'] * 0.15 + np.random.randn() * 0.02
            
            all_data.append(row)
    
    df = pd.DataFrame(all_data)
    
    # 验证每个因子
    validator = FactorValidator(
        ic_ir_threshold=0.3,  # DSS 可适当降低阈值
        pathway_threshold=0.7
    )
    
    results = []
    for factor in factors:
        result = validator.validate(df, factor, 'return', 'date', factor)
        results.append(result.to_dict())
        
        status = "✓ 通过" if result.pass_validation else "✗ 未通过"
        print(f"\n{factor}: {status}")
        print(f"  IC={result.ic_mean:.4f}, IR={result.ir:.2f}, "
              f"稳定性={result.pathway_stability:.2f}")
    
    # 筛选有效因子
    valid_factors = [r for r in results if r['pass_validation']]
    print(f"\n通过验证的因子: {len(valid_factors)}/{len(factors)}")
    for vf in valid_factors:
        print(f"  - {vf['factor_name']}")


def example_realtime_monitoring():
    """实时监控示例 - DSS 生产环境"""
    print("\n" + "=" * 60)
    print("实时监控示例")
    print("=" * 60)
    
    # 模拟每日滚动计算 IC
    validator = FactorValidator()
    
    # 假设我们有最近 60 天的数据
    np.random.seed(42)
    dates = pd.date_range('2024-11-01', '2024-12-31', freq='D')
    
    data = []
    for date in dates:
        for i in range(100):
            data.append({
                'date': date,
                'symbol': f'STOCK_{i:03d}',
                'factor': np.random.randn(),
                'return': np.random.randn() * 0.02
            })
    
    df = pd.DataFrame(data)
    
    # 滚动计算 20 日 IC
    ic_series = validator.calc_ic_series(df, 'date', 'factor', 'return')
    
    # 最近 20 日 IC
    recent_ic = ic_series.tail(20)
    print(f"\n最近 20 日 IC 监控:")
    print(f"  均值: {recent_ic.mean():.4f}")
    print(f"  标准差: {recent_ic.std():.4f}")
    print(f"  最新值: {recent_ic.iloc[-1]:.4f}")
    
    # 预警逻辑
    if abs(recent_ic.mean()) < 0.02:
        print("  ⚠️ 警告: IC 均值过低，因子可能失效")
    if recent_ic.std() > 0.15:
        print("  ⚠️ 警告: IC 波动过大，因子不稳定")


def example_pathway_test():
    """多轨道测试示例"""
    print("\n" + "=" * 60)
    print("多轨道稳健性测试示例")
    print("=" * 60)
    
    np.random.seed(42)
    
    # 创建一个"好"因子 (稳定有效)
    dates = pd.date_range('2024-01-01', '2024-06-30', freq='D')
    good_data = []
    for date in dates:
        for i in range(100):
            factor = np.random.randn()
            ret = factor * 0.1 + np.random.randn() * 0.3  # 强相关
            good_data.append({
                'date': date, 'symbol': f'S_{i:03d}',
                'factor': factor, 'return': ret / 100
            })
    
    # 创建一个"坏"因子 (依赖特定日期)
    bad_data = []
    for date in dates:
        for i in range(100):
            factor = np.random.randn()
            # 只在特定日期有效
            if date.day == 1:
                ret = factor * 0.5 + np.random.randn() * 0.1
            else:
                ret = np.random.randn() * 0.5
            bad_data.append({
                'date': date, 'symbol': f'S_{i:03d}',
                'factor': factor, 'return': ret / 100
            })
    
    good_df = pd.DataFrame(good_data)
    bad_df = pd.DataFrame(bad_data)
    
    validator = FactorValidator()
    
    # 测试好因子
    print("\n好因子 (稳定有效):")
    good_result = validator.pathway_test(good_df, 'factor', 'return', 'date', n_pathways=10)
    print(f"  稳定性得分: {good_result['stability_score']:.2f}")
    print(f"  最佳轨道 IC: {good_result['pathway_results']['ic_mean'].max():.4f}")
    print(f"  最差轨道 IC: {good_result['pathway_results']['ic_mean'].min():.4f}")
    
    # 测试坏因子
    print("\n坏因子 (依赖特定日期):")
    bad_result = validator.pathway_test(bad_df, 'factor', 'return', 'date', n_pathways=10)
    print(f"  稳定性得分: {bad_result['stability_score']:.2f}")
    print(f"  最佳轨道 IC: {bad_result['pathway_results']['ic_mean'].max():.4f}")
    print(f"  最差轨道 IC: {bad_result['pathway_results']['ic_mean'].min():.4f}")
    print(f"  ⚠️ 稳定性低，可能是过拟合或依赖特定日期")


def example_integration_with_backtest():
    """与现有回测模块集成"""
    print("\n" + "=" * 60)
    print("与回测模块集成示例")
    print("=" * 60)
    
    from backtest import Backtester
    
    # 生成模拟价格数据
    np.random.seed(42)
    n_days = 252
    prices = 100 * (1 + np.random.randn(n_days) * 0.01).cumprod()
    
    # 生成因子信号
    factor = np.random.randn(n_days)
    # 因子与价格变动正相关
    signals = np.where(factor > 0.5, 1, np.where(factor < -0.5, -1, 0))
    
    # 运行回测
    backtester = Backtester(
        initial_capital=100000,
        transaction_cost=0.001
    )
    result = backtester.run(prices, signals)
    
    print(f"\n回测结果:")
    print(f"  总收益: {result.total_return:.2%}")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  最大回撤: {result.max_drawdown:.2%}")
    
    # 使用 factor_validation 进行更详细的分析
    print(f"\n因子验证补充:")
    # 可以进一步分析信号的质量...


if __name__ == '__main__':
    # 运行所有示例
    example_basic_usage()
    example_dss_integration()
    example_realtime_monitoring()
    example_pathway_test()
    example_integration_with_backtest()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成")
    print("=" * 60)
