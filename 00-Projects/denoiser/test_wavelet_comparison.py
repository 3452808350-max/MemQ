"""
小波去噪效果对比测试

测试内容:
1. 正弦波+噪声信号
2. 模拟股票数据

对比维度:
- 小波基: db1, db4, haar, sym4
- 阈值模式: soft, hard

评估指标:
- SNR (信噪比)
- MSE (均方误差)
- 平滑度
- MAE (平均绝对误差)
"""
import numpy as np
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from denoiser import Denoiser

# 设置随机种子以便复现
np.random.seed(42)

def generate_sine_wave_with_noise(n=1000, freq=5, noise_level=0.3):
    """生成正弦波+噪声信号"""
    t = np.linspace(0, 4 * np.pi, n)
    clean_signal = np.sin(freq * t) + 0.5 * np.sin(10 * t)
    noise = np.random.normal(0, noise_level, n)
    noisy_signal = clean_signal + noise
    return clean_signal, noisy_signal

def generate_stock_data(n=500, trend=0.0002, volatility=0.02, noise_level=0.5):
    """生成模拟股票数据"""
    # 价格趋势 + 波动 + 噪声
    returns = np.random.normal(trend, volatility, n)
    
    # 添加一些周期性波动
    t = np.arange(n)
    cyclical = 0.1 * np.sin(2 * np.pi * t / 50) + 0.05 * np.sin(2 * np.pi * t / 20)
    
    # 构建价格序列
    price = 100 * np.exp(np.cumsum(returns)) + cyclical * 10
    clean_price = 100 * np.exp(np.cumsum(returns)) + cyclical * 10
    
    # 添加高频噪声
    noise = np.random.normal(0, noise_level, n)
    noisy_price = clean_price + noise
    
    return clean_price, noisy_price

def evaluate_denoising(clean, noisy, denoised):
    """评估去噪效果"""
    # SNR: 信噪比 (越高越好)
    signal_power = np.var(denoised)
    noise_power = np.var(clean - denoised)
    snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
    
    # MSE: 均方误差 (越低越好)
    mse = np.mean((clean - denoised) ** 2)
    
    # MAE: 平均绝对误差 (越低越好)
    mae = np.mean(np.abs(clean - denoised))
    
    # 平滑度: 一阶差分的标准差 (越低越平滑)
    smoothness = np.std(np.diff(denoised))
    
    # 相关系数 (越高越好)
    correlation = np.corrcoef(clean, denoised)[0, 1]
    
    return {
        'SNR(dB)': snr,
        'MSE': mse,
        'MAE': mae,
        'Smoothness': smoothness,
        'Correlation': correlation
    }

def run_comparison():
    """运行所有对比测试"""
    # 生成测试信号
    print("=" * 70)
    print("生成测试信号...")
    
    sine_clean, sine_noisy = generate_sine_wave_with_noise(n=1024, freq=5, noise_level=0.3)
    stock_clean, stock_noisy = generate_stock_data(n=500, noise_level=0.5)
    
    print(f"正弦波信号: {len(sine_clean)} 点")
    print(f"股票模拟数据: {len(stock_clean)} 点")
    
    # 测试配置
    wavelets = ['db1', 'db4', 'haar', 'sym4']
    threshold_modes = ['soft', 'hard']
    
    # 存储结果
    results = {
        'sine': {},
        'stock': {}
    }
    
    # 存储最佳结果
    best_results = {
        'sine': {'score': -np.inf, 'config': None, 'metrics': None},
        'stock': {'score': -np.inf, 'config': None, 'metrics': None}
    }
    
    # 计算原始信号的指标作为基准
    print("\n" + "=" * 70)
    print("基准指标 (未去噪):")
    print("-" * 70)
    
    sine_baseline = evaluate_denoising(sine_clean, sine_noisy, sine_noisy)
    stock_baseline = evaluate_denoising(stock_clean, stock_noisy, stock_noisy)
    
    print(f"正弦波 - SNR: {sine_baseline['SNR(dB)']:.2f}dB, MSE: {sine_baseline['MSE']:.4f}, Smoothness: {sine_baseline['Smoothness']:.4f}")
    print(f"股票数据 - SNR: {stock_baseline['SNR(dB)']:.2f}dB, MSE: {stock_baseline['MSE']:.4f}, Smoothness: {stock_baseline['Smoothness']:.4f}")
    
    print("\n" + "=" * 70)
    print("开始测试不同小波基和阈值模式...")
    print("=" * 70)
    
    # 测试所有组合
    for signal_type, (clean, noisy) in [('sine', (sine_clean, sine_noisy)), ('stock', (stock_clean, stock_noisy))]:
        print(f"\n{'='*70}")
        print(f"测试信号类型: {'正弦波+噪声' if signal_type == 'sine' else '模拟股票数据'}")
        print("=" * 70)
        
        for wavelet in wavelets:
            for mode in threshold_modes:
                config_name = f"{wavelet}_{mode}"
                
                try:
                    denoiser = Denoiser(method='wavelet', wavelet=wavelet, threshold_mode=mode)
                    denoised = denoiser.denoise(noisy)
                    
                    metrics = evaluate_denoising(clean, noisy, denoised)
                    results[signal_type][config_name] = metrics
                    
                    # 计算综合得分 (SNR高好，MSE低好，MAE低好，Correlation高好)
                    # 归一化并组合
                    score = metrics['SNR(dB)'] * 10 - metrics['MSE'] * 1000 - metrics['MAE'] * 100 + metrics['Correlation'] * 10
                    
                    if score > best_results[signal_type]['score']:
                        best_results[signal_type] = {
                            'score': score,
                            'config': config_name,
                            'metrics': metrics
                        }
                    
                    print(f"  {config_name:15} | SNR: {metrics['SNR(dB)']:7.2f}dB | MSE: {metrics['MSE']:.6f} | MAE: {metrics['MAE']:.4f} | Smooth: {metrics['Smoothness']:.4f} | Corr: {metrics['Correlation']:.4f}")
                    
                except Exception as e:
                    print(f"  {config_name:15} | 错误: {e}")
                    results[signal_type][config_name] = {'error': str(e)}
    
    # 输出对比表
    print("\n" + "=" * 70)
    print("完整对比表")
    print("=" * 70)
    
    for signal_type in ['sine', 'stock']:
        signal_name = '正弦波+噪声' if signal_type == 'sine' else '模拟股票数据'
        print(f"\n{signal_name}:")
        print("-" * 70)
        print(f"{'配置':15} | {'SNR(dB)':>10} | {'MSE':>10} | {'MAE':>8} | {'Smoothness':>10} | {'Correlation':>10}")
        print("-" * 70)
        
        # 按SNR排序
        sorted_configs = sorted(
            [(k, v) for k, v in results[signal_type].items() if 'error' not in v],
            key=lambda x: x[1]['SNR(dB)'],
            reverse=True
        )
        
        for config, metrics in sorted_configs:
            print(f"{config:15} | {metrics['SNR(dB)']:10.2f} | {metrics['MSE']:10.6f} | {metrics['MAE']:8.4f} | {metrics['Smoothness']:10.4f} | {metrics['Correlation']:10.4f}")
    
    # 按指标分析最佳组合
    print("\n" + "=" * 70)
    print("按指标分析")
    print("=" * 70)
    
    for signal_type in ['sine', 'stock']:
        signal_name = '正弦波+噪声' if signal_type == 'sine' else '模拟股票数据'
        print(f"\n{signal_name}:")
        
        valid_results = {k: v for k, v in results[signal_type].items() if 'error' not in v}
        
        # 找各指标最佳
        best_snr = max(valid_results.items(), key=lambda x: x[1]['SNR(dB)'])
        best_mse = min(valid_results.items(), key=lambda x: x[1]['MSE'])
        best_smooth = min(valid_results.items(), key=lambda x: x[1]['Smoothness'])
        best_corr = max(valid_results.items(), key=lambda x: x[1]['Correlation'])
        
        print(f"  最高SNR:  {best_snr[0]} ({best_snr[1]['SNR(dB)']:.2f}dB)")
        print(f"  最低MSE:  {best_mse[0]} ({best_mse[1]['MSE']:.6f})")
        print(f"  最平滑:   {best_smooth[0]} ({best_smooth[1]['Smoothness']:.4f})")
        print(f"  最高相关: {best_corr[0]} ({best_corr[1]['Correlation']:.4f})")
    
    # 最终推荐
    print("\n" + "=" * 70)
    print("最终推荐")
    print("=" * 70)
    
    for signal_type in ['sine', 'stock']:
        signal_name = '正弦波+噪声' if signal_type == 'sine' else '模拟股票数据'
        best = best_results[signal_type]
        print(f"\n{signal_name} 最佳组合: {best['config']}")
        print(f"  SNR: {best['metrics']['SNR(dB)']:.2f}dB")
        print(f"  MSE: {best['metrics']['MSE']:.6f}")
        print(f"  MAE: {best['metrics']['MAE']:.4f}")
        print(f"  平滑度: {best['metrics']['Smoothness']:.4f}")
        print(f"  相关系数: {best['metrics']['Correlation']:.4f}")
    
    # 小波基分析
    print("\n" + "=" * 70)
    print("小波基特性分析")
    print("=" * 70)
    print("""
db1 (Haar小波):
  - 最简单的小波，不连续
  - 适合突变信号，计算速度快
  - 但对平滑信号可能产生方块效应

db4 (Daubechies 4):
  - 较平滑的紧支撑小波
  - 平衡了平滑性和紧支撑性
  - 金融数据常用选择

haar:
  - 与db1相同，是最简单的小波
  - 快速但对平滑信号效果一般

sym4 (Symlet 4):
  - 近似对称的Daubechies小波
  - 对称性更好，相位失真小
  - 适合需要保持信号形态的应用
    """)
    
    # 阈值模式分析
    print("=" * 70)
    print("阈值模式分析")
    print("=" * 70)
    print("""
soft (软阈值):
  - 将系数收缩到阈值范围内
  - 产生更平滑的结果
  - 但可能过度平滑，丢失细节

hard (硬阈值):
  - 直接截断小于阈值的系数
  - 保留更多细节
  - 但可能产生不连续点
    """)
    
    # 综合推荐
    print("=" * 70)
    print("综合推荐")
    print("=" * 70)
    
    # 统计各组合在两种信号上的表现
    combined_scores = {}
    for config in results['sine'].keys():
        if 'error' in results['sine'].get(config, {}):
            continue
        if 'error' in results['stock'].get(config, {}):
            continue
        
        # 综合两种信号的得分
        sine_score = results['sine'][config]['SNR(dB)'] + results['sine'][config]['Correlation'] * 10
        stock_score = results['stock'][config]['SNR(dB)'] + results['stock'][config]['Correlation'] * 10
        combined_scores[config] = sine_score + stock_score
    
    if combined_scores:
        best_overall = max(combined_scores.items(), key=lambda x: x[1])
        print(f"\n综合两种信号，最佳组合: {best_overall[0]}")
        print(f"综合得分: {best_overall[1]:.2f}")
        
        wavelet, mode = best_overall[0].rsplit('_', 1)
        print(f"\n推荐配置:")
        print(f"  小波基: {wavelet}")
        print(f"  阈值模式: {mode}")
        print(f"\n理由:")
        print(f"  - 在两种信号类型上都表现良好")
        print(f"  - SNR和相关性得分最高")
        if mode == 'soft':
            print(f"  - 软阈值提供了更平滑的输出，适合金融数据")
        else:
            print(f"  - 硬阈值保留了更多信号细节")
    
    return results, best_results

if __name__ == '__main__':
    results, best = run_comparison()