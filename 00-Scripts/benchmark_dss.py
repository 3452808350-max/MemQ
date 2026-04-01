#!/usr/bin/env python3
"""
DSS 性能基准测试
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import time
import numpy as np
import pandas as pd

def generate_test_data(days=500):
    """生成测试数据"""
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq='D')
    prices = 100 + np.cumsum(np.random.randn(days) * 2)
    volume = np.random.randint(1000, 10000, days)
    
    df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'volume': volume
    })
    df = df.set_index('date')
    return df

def benchmark_function(name, func, *args, iterations=10):
    """基准测试单个函数"""
    times = []
    for _ in range(iterations):
        start = time.time()
        func(*args)
        end = time.time()
        times.append(end - start)
    
    avg_time = np.mean(times)
    std_time = np.std(times)
    return avg_time, std_time

def main():
    print("="*60)
    print("DSS 性能基准测试")
    print("="*60)
    
    # 准备测试数据
    print("\n准备测试数据...")
    df = generate_test_data(500)
    prices = df['close']
    volume = df['volume']
    print(f"数据：{len(df)}天，价格范围：{prices.min():.2f} - {prices.max():.2f}")
    
    results = []
    
    # 测试 1: 市场状态检测
    print("\n[1/6] 市场状态检测...")
    from dss_adaptive_indicators import detect_market_regime
    avg, std = benchmark_function(
        "detect_market_regime",
        detect_market_regime,
        prices,
        iterations=100
    )
    print(f"  平均：{avg*1000:.2f}ms ± {std*1000:.2f}ms")
    results.append(("市场状态检测", avg, std))
    
    # 测试 2: 自适应 RSI
    print("\n[2/6] 自适应 RSI...")
    from dss_adaptive_indicators import adaptive_rsi
    avg, std = benchmark_function(
        "adaptive_rsi",
        adaptive_rsi,
        prices,
        iterations=50
    )
    print(f"  平均：{avg*1000:.2f}ms ± {std*1000:.2f}ms")
    results.append(("自适应 RSI", avg, std))
    
    # 测试 3: 自适应 MACD
    print("\n[3/6] 自适应 MACD...")
    from dss_adaptive_indicators import adaptive_macd
    avg, std = benchmark_function(
        "adaptive_macd",
        adaptive_macd,
        prices,
        iterations=50
    )
    print(f"  平均：{avg*1000:.2f}ms ± {std*1000:.2f}ms")
    results.append(("自适应 MACD", avg, std))
    
    # 测试 4: ML 预测
    print("\n[4/6] ML 预测...")
    from dss_ml_predict import get_ml_score
    avg, std = benchmark_function(
        "get_ml_score",
        get_ml_score,
        df,
        iterations=10
    )
    print(f"  平均：{avg*1000:.2f}ms ± {std*1000:.2f}ms")
    results.append(("ML 预测", avg, std))
    
    # 测试 5: 风险评分
    print("\n[5/6] 风险评分...")
    from dss_risk import calculate_risk_score
    avg, std = benchmark_function(
        "calculate_risk_score",
        calculate_risk_score,
        df,
        iterations=50
    )
    print(f"  平均：{avg*1000:.2f}ms ± {std*1000:.2f}ms")
    results.append(("风险评分", avg, std))
    
    # 测试 6: 完整分析流程
    print("\n[6/6] 完整分析流程...")
    def full_analysis(df):
        from dss_adaptive_indicators import adaptive_rsi, adaptive_macd
        from dss_ml_predict import get_ml_score
        from dss_risk import calculate_risk_score
        
        prices = df['close']
        rsi, _ = adaptive_rsi(prices)
        macd, _, _, _ = adaptive_macd(prices)
        ml_score, _ = get_ml_score(df)
        risk, _, _ = calculate_risk_score(df)
        return rsi, macd, ml_score, risk
    
    avg, std = benchmark_function(
        "full_analysis",
        full_analysis,
        df,
        iterations=10
    )
    print(f"  平均：{avg*1000:.2f}ms ± {std*1000:.2f}ms")
    results.append(("完整分析", avg, std))
    
    # 汇总
    print("\n" + "="*60)
    print("性能汇总")
    print("="*60)
    print(f"{'测试项':<20} {'平均时间':>12} {'标准差':>12}")
    print("-"*60)
    for name, avg, std in results:
        print(f"{name:<20} {avg*1000:>10.2f}ms {std*1000:>10.2f}ms")
    print("="*60)
    
    # 估算批量分析时间
    single_analysis_time = [r[1] for r in results if r[0] == "完整分析"][0]
    estimated_20_stocks = single_analysis_time * 20
    print(f"\n预估 20 只股票批量分析时间：{estimated_20_stocks:.2f}s")
    
    return results

if __name__ == "__main__":
    main()
