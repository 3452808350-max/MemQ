"""
Kalman Filter 测试脚本
测试卡尔曼滤波去噪效果、参数优化和趋势检测
"""
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from denoiser.methods.kalman import kalman_denoise, kalman_denoise_adaptive, kalman_smoother
from denoiser.dss_integration import detect_trend_clean
from denoiser import Denoiser

np.random.seed(42)

# ============================================================
# 1. 生成股票价格模拟数据（趋势+噪声）
# ============================================================
print("=" * 60)
print("1. 生成股票价格模拟数据")
print("=" * 60)

n = 250  # 约1年的交易日
t = np.arange(n)

# 生成包含趋势、周期和噪声的价格数据
trend = 100 + 0.15 * t  # 线性上升趋势
seasonality = 10 * np.sin(2 * np.pi * t / 60)  # 60天周期
noise = np.random.normal(0, 3, n)  # 噪声

# 真实信号（无噪声）
true_signal = trend + seasonality

# 观测信号（含噪声）
observed_signal = true_signal + noise

print(f"数据点数: {n}")
print(f"趋势斜率: 0.15 元/天")
print(f"噪声标准差: 3.0")
print(f"真实价格范围: [{true_signal.min():.2f}, {true_signal.max():.2f}]")
print(f"观测价格范围: [{observed_signal.min():.2f}, {observed_signal.max():.2f}]")


# ============================================================
# 2. 测试不同参数组合
# ============================================================
print("\n" + "=" * 60)
print("2. 参数组合测试")
print("=" * 60)

# 参数组合
process_noises = [0.001, 0.01, 0.1]
measurement_noises = [0.5, 1.0, 2.0]

results = []

print("\n测试不同参数组合...")
for Q in process_noises:
    for R in measurement_noises:
        # 使用标准卡尔曼滤波
        denoised, components = kalman_denoise(
            observed_signal, 
            process_noise=Q, 
            measurement_noise=R,
            return_components=True
        )
        
        # 计算评估指标
        # MSE: 相对于真实信号的误差
        mse = np.mean((denoised - true_signal) ** 2)
        mae = np.mean(np.abs(denoised - true_signal))
        
        # 平滑度：一阶差分的标准差（越小越平滑）
        smoothness = np.std(np.diff(denoised))
        
        # 信噪比改善
        original_snr = 10 * np.log10(np.var(true_signal) / np.var(noise))
        denoised_noise = observed_signal - denoised
        denoised_snr = 10 * np.log10(np.var(denoised) / (np.var(denoised_noise) + 1e-10))
        snr_improvement = denoised_snr - original_snr
        
        # 趋势保持度：去噪信号与真实信号趋势的相关性
        trend_corr = np.corrcoef(np.diff(true_signal), np.diff(denoised))[0, 1]
        
        results.append({
            'process_noise': Q,
            'measurement_noise': R,
            'mse': mse,
            'mae': mae,
            'smoothness': smoothness,
            'snr_improvement': snr_improvement,
            'trend_correlation': trend_corr
        })

# 创建结果表格
df_results = pd.DataFrame(results)
print("\n参数组合测试结果:")
print(df_results.to_string(index=False, float_format='%.4f'))

# 找最佳参数组合
best_idx = df_results['mse'].idxmin()
best_params = df_results.loc[best_idx]
print(f"\n最佳参数组合 (最小MSE):")
print(f"  process_noise: {best_params['process_noise']}")
print(f"  measurement_noise: {best_params['measurement_noise']}")
print(f"  MSE: {best_params['mse']:.4f}")
print(f"  MAE: {best_params['mae']:.4f}")
print(f"  SNR改善: {best_params['snr_improvement']:.2f} dB")
print(f"  趋势相关性: {best_params['trend_correlation']:.4f}")


# ============================================================
# 3. 对比三种卡尔曼方法
# ============================================================
print("\n" + "=" * 60)
print("3. 三种卡尔曼方法对比")
print("=" * 60)

# 使用最佳参数
best_Q = best_params['process_noise']
best_R = best_params['measurement_noise']

# 标准卡尔曼滤波
standard_filtered, standard_components = kalman_denoise(
    observed_signal,
    process_noise=best_Q,
    measurement_noise=best_R,
    return_components=True
)

# 自适应卡尔曼滤波
adaptive_filtered, adaptive_components = kalman_denoise_adaptive(
    observed_signal,
    window=20,
    return_components=True
)

# RTS平滑器
smoothed, smoother_components = kalman_smoother(
    observed_signal,
    process_noise=best_Q,
    measurement_noise=best_R,
    return_components=True
)

# 评估对比
methods_comparison = []
for name, denoised in [
    ('标准卡尔曼', standard_filtered),
    ('自适应卡尔曼', adaptive_filtered),
    ('RTS平滑器', smoothed)
]:
    mse = np.mean((denoised - true_signal) ** 2)
    mae = np.mean(np.abs(denoised - true_signal))
    smoothness = np.std(np.diff(denoised))
    trend_corr = np.corrcoef(np.diff(true_signal), np.diff(denoised))[0, 1]
    
    methods_comparison.append({
        '方法': name,
        'MSE': mse,
        'MAE': mae,
        '平滑度': smoothness,
        '趋势相关性': trend_corr
    })

df_methods = pd.DataFrame(methods_comparison)
print("\n三种方法对比:")
print(df_methods.to_string(index=False, float_format='%.4f'))

# 找最佳方法
best_method_idx = df_methods['MSE'].idxmin()
best_method = df_methods.loc[best_method_idx]
print(f"\n最佳方法 (最小MSE): {best_method['方法']}")
print(f"  MSE: {best_method['MSE']:.4f}")
print(f"  MAE: {best_method['MAE']:.4f}")


# ============================================================
# 4. 测试趋势检测功能
# ============================================================
print("\n" + "=" * 60)
print("4. 趋势检测功能测试")
print("=" * 60)

# 创建 DataFrame 用于趋势检测
df_test = pd.DataFrame({'Close': observed_signal})

# 测试趋势检测
trend_result = detect_trend_clean(df_test, price_col='Close', method='kalman')
print("\n趋势检测结果:")
print(f"  检测方向: {trend_result['trend']}")
print(f"  斜率: {trend_result['slope']:.6f}")
print(f"  稳定性: {trend_result['stability']:.4f}")
print(f"  去噪价格: {trend_result['current_price_denoised']:.2f}")
print(f"  原始价格: {trend_result['original_price']:.2f}")


# ============================================================
# 5. 趋势检测准确率评估
# ============================================================
print("\n" + "=" * 60)
print("5. 趋势检测准确率评估")
print("=" * 60)

# 生成多组测试数据，包含不同的趋势类型
n_tests = 100
correct_detections = 0
trend_types = ['up', 'down', 'sideways']
test_results = []

for i in range(n_tests):
    # 随机选择趋势类型
    true_trend = np.random.choice(trend_types, p=[0.4, 0.4, 0.2])
    
    # 生成对应趋势的数据
    t = np.arange(100)
    
    if true_trend == 'up':
        base = 100 + 0.3 * t + np.random.normal(0, 0.5, 100)  # 明显上升趋势
    elif true_trend == 'down':
        base = 150 - 0.3 * t + np.random.normal(0, 0.5, 100)  # 明显下降趋势
    else:
        base = 120 + np.random.normal(0, 1, 100)  # 横盘
        
    # 加入噪声
    noisy_data = base + np.random.normal(0, 2, 100)
    df_temp = pd.DataFrame({'Close': noisy_data})
    
    # 检测趋势
    result = detect_trend_clean(df_temp, price_col='Close', method='kalman')
    detected_trend = result['trend']
    
    # 判断是否正确
    is_correct = detected_trend == true_trend
    correct_detections += int(is_correct)
    
    test_results.append({
        'test_id': i,
        'true_trend': true_trend,
        'detected_trend': detected_trend,
        'correct': is_correct,
        'slope': result['slope']
    })

# 统计准确率
accuracy = correct_detections / n_tests * 100
print(f"\n趋势检测总测试次数: {n_tests}")
print(f"正确检测次数: {correct_detections}")
print(f"总体准确率: {accuracy:.2f}%")

# 按趋势类型统计
df_test_results = pd.DataFrame(test_results)
for trend in trend_types:
    subset = df_test_results[df_test_results['true_trend'] == trend]
    if len(subset) > 0:
        acc = subset['correct'].mean() * 100
        print(f"  {trend}趋势: {len(subset)}次, 准确率 {acc:.1f}%")


# ============================================================
# 6. 总结
# ============================================================
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)

print(f"""
【最佳参数组合】
  - process_noise: {best_params['process_noise']}
  - measurement_noise: {best_params['measurement_noise']}
  - 对应MSE: {best_params['mse']:.4f}

【最佳卡尔曼方法】
  - {best_method['方法']}
  - MSE: {best_method['MSE']:.4f}, MAE: {best_method['MAE']:.4f}

【趋势检测准确率】
  - 总体准确率: {accuracy:.2f}%
  - 上升趋势检测准确率: {df_test_results[df_test_results['true_trend']=='up']['correct'].mean()*100:.1f}%
  - 下降趋势检测准确率: {df_test_results[df_test_results['true_trend']=='down']['correct'].mean()*100:.1f}%
  - 横盘趋势检测准确率: {df_test_results[df_test_results['true_trend']=='sideways']['correct'].mean()*100:.1f}%

【结论】
  1. 低 process_noise (0.001) 配合适中 measurement_noise (0.5-1.0) 效果最佳
  2. RTS平滑器因双向滤波，通常比单向卡尔曼滤波效果更好
  3. 趋势检测在有明显方向时准确率高，横盘检测相对困难
""")