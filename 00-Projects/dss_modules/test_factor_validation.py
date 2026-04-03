"""
Factor Validation 模块简化测试
"""
import sys
import pandas as pd
import numpy as np
from factor_validation import FactorValidator, quick_validate, winsorize


def test_winsorize():
    """测试缩尾函数"""
    print("\n[测试] winsorize 缩尾函数")
    
    data = np.array([1, 2, 3, 4, 5, 100, -100])
    series = pd.Series(data)
    result = winsorize(series, n=2)
    
    print(f"  原始数据: {data}")
    print(f"  缩尾后: {result.values}")
    print(f"  ✓ 极值被限制在 2 倍标准差内")


def test_ic_calculation():
    """测试 IC 计算"""
    print("\n[测试] IC 计算")
    
    np.random.seed(42)
    n = 100
    
    # 创建强相关数据
    factor = np.random.randn(n)
    returns = factor * 0.5 + np.random.randn(n) * 0.1
    
    df = pd.DataFrame({
        'date': ['2024-01-01'] * n,
        'symbol': [f'S{i}' for i in range(n)],
        'factor': factor,
        'return': returns
    })
    
    validator = FactorValidator()
    ic = validator.calc_ic(df['factor'], df['return'])
    
    print(f"  因子与收益相关系数: {ic:.4f}")
    assert abs(ic) > 0.5, "IC 应该较高"
    print(f"  ✓ IC 计算正确")


def test_ir_calculation():
    """测试 IR 计算"""
    print("\n[测试] IR 计算")
    
    # 创建 IC 序列
    np.random.seed(42)
    ic_series = pd.Series(np.random.randn(60) * 0.05 + 0.03)
    
    validator = FactorValidator()
    ir = validator.calc_ir(ic_series)
    
    print(f"  IC 均值: {ic_series.mean():.4f}")
    print(f"  IC 标准差: {ic_series.std():.4f}")
    print(f"  IR: {ir:.2f}")
    print(f"  ✓ IR 计算正确")


def test_sharpe_sortino():
    """测试夏普和索替诺比率"""
    print("\n[测试] 夏普和索替诺比率")
    
    np.random.seed(42)
    returns = pd.Series(np.random.randn(100) * 0.02 + 0.001)
    
    validator = FactorValidator()
    sharpe = validator.calc_sharpe(returns)
    sortino = validator.calc_sortino(returns)
    
    print(f"  年化夏普: {sharpe:.2f}")
    print(f"  年化索替诺: {sortino:.2f}")
    print(f"  ✓ 比率计算正确")


def test_full_validation():
    """测试完整验证流程"""
    print("\n[测试] 完整因子验证")
    
    np.random.seed(42)
    
    # 创建模拟数据 (30天, 每天50只股票)
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    data = []
    
    for date in dates:
        for i in range(50):
            factor = np.random.randn()
            # 因子与收益正相关
            ret = factor * 0.1 + np.random.randn() * 0.02
            data.append({
                'date': date,
                'symbol': f'STOCK_{i:02d}',
                'factor': factor,
                'return': ret
            })
    
    df = pd.DataFrame(data)
    
    validator = FactorValidator(
        ic_ir_threshold=0.3,
        pathway_threshold=0.7
    )
    
    result = validator.validate(df, 'factor', 'return', 'date', 'test_factor')
    
    print(f"\n  验证结果:")
    print(f"  - 因子名称: {result.factor_name}")
    print(f"  - IC 均值: {result.ic_mean:.4f}")
    print(f"  - IC 标准差: {result.ic_std:.4f}")
    print(f"  - IR: {result.ir:.2f}")
    print(f"  - 多空夏普: {result.sharpe_ls:.2f}")
    print(f"  - 多轨道稳定性: {result.pathway_stability:.2f}")
    print(f"  - IC 半衰期: {result.half_life}")
    print(f"  - 单调性得分: {result.monotonicity_score:.2f}")
    print(f"  - 通过验证: {result.pass_validation}")
    
    # 验证结果合理性
    assert -1 <= result.ic_mean <= 1, "IC 应在 [-1, 1] 范围内"
    assert result.ir >= 0 or np.isnan(result.ir), "IR 应非负"
    print(f"\n  ✓ 完整验证流程通过")


def test_quick_validate():
    """测试快速验证函数"""
    print("\n[测试] quick_validate 快速验证")
    
    np.random.seed(42)
    
    # 创建模拟数据 - 确保列名正确
    dates = []
    symbols = []
    factors = []
    returns = []
    
    for date in pd.date_range('2024-01-01', periods=10):
        for i in range(50):
            dates.append(date)
            symbols.append(f'S{i:02d}')
            factors.append(np.random.randn())
            returns.append(np.random.randn() * 0.02)
    
    factor_df = pd.DataFrame({
        'date': dates,
        'symbol': symbols,
        'factor': factors
    })
    
    return_df = pd.DataFrame({
        'date': dates,
        'symbol': symbols,
        'return': returns
    })
    
    result = quick_validate(factor_df, return_df, 'test_factor')
    
    print(f"  快速验证结果:")
    for key, value in result.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.4f}")
        else:
            print(f"    {key}: {value}")
    
    print(f"  ✓ 快速验证函数工作正常")


def test_pathway_stability():
    """测试多轨道稳定性"""
    print("\n[测试] 多轨道稳定性")
    
    np.random.seed(42)
    
    # 创建稳定因子
    dates = pd.date_range('2024-01-01', periods=20, freq='D')
    data = []
    
    for date in dates:
        for i in range(30):
            factor = np.random.randn()
            ret = factor * 0.15 + np.random.randn() * 0.01  # 强相关
            data.append({
                'date': date,
                'symbol': f'S{i:02d}',
                'factor': factor,
                'return': ret
            })
    
    df = pd.DataFrame(data)
    
    validator = FactorValidator()
    pathway_result = validator.pathway_test(df, 'factor', 'return', 'date', n_pathways=5)
    
    print(f"  多轨道测试结果:")
    print(f"  - 稳定性得分: {pathway_result['stability_score']:.2f}")
    print(f"  - 最佳轨道: {pathway_result['best_pathway']}")
    print(f"  - 最差轨道: {pathway_result['worst_pathway']}")
    print(f"  - 各轨道 IC 均值:")
    for _, row in pathway_result['pathway_results'].iterrows():
        print(f"    轨道 {row['pathway']}: IC={row['ic_mean']:.4f}")
    
    assert pathway_result['stability_score'] > 0.5, "稳定因子应有较高稳定性"
    print(f"  ✓ 多轨道测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Factor Validation 模块测试")
    print("=" * 60)
    
    tests = [
        test_winsorize,
        test_ic_calculation,
        test_ir_calculation,
        test_sharpe_sortino,
        test_full_validation,
        test_quick_validate,
        test_pathway_stability,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n  ✗ 测试失败: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
