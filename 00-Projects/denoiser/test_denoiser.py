#!/usr/bin/env python3
"""
Denoiser 测试脚本
"""
import numpy as np
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from denoiser import Denoiser

# 生成测试信号: 正弦波 + 噪声
np.random.seed(42)
t = np.linspace(0, 4*np.pi, 500)
clean_signal = np.sin(t) + 0.5 * np.sin(2*t)
noise = np.random.normal(0, 0.3, len(t))
noisy_signal = clean_signal + noise

print("=" * 60)
print("Denoiser 模块测试")
print("=" * 60)

# 测试所有方法
methods = ['wavelet', 'kalman', 'ssa']  # EMD和VMD需要额外依赖

print("\n📊 方法对比:\n")
print(f"{'方法':<12} {'SNR (dB)':<12} {'MSE':<12} {'平滑度':<12}")
print("-" * 50)

for method in methods:
    try:
        denoiser = Denoiser(method=method)
        denoised = denoiser.denoise(noisy_signal)
        metrics = Denoiser.evaluate(noisy_signal, denoised)
        
        print(f"{method:<12} {metrics['snr']:<12.2f} {metrics['mse']:<12.6f} {metrics['smoothness']:<12.4f}")
    except Exception as e:
        print(f"{method:<12} Error: {str(e)[:30]}")

# 测试EMD (如果安装了PyEMD)
try:
    from PyEMD import EMD
    denoiser = Denoiser(method='emd')
    denoised = denoiser.denoise(noisy_signal)
    metrics = Denoiser.evaluate(noisy_signal, denoised)
    print(f"{'emd':<12} {metrics['snr']:<12.2f} {metrics['mse']:<12.6f} {metrics['smoothness']:<12.4f}")
except ImportError:
    print(f"{'emd':<12} 跳过 (需要 PyEMD)")

# 测试VMD (如果安装了vmdpy)
try:
    from vmdpy import VMD
    denoiser = Denoiser(method='vmd')
    denoised = denoiser.denoise(noisy_signal)
    metrics = Denoiser.evaluate(noisy_signal, denoised)
    print(f"{'vmd':<12} {metrics['snr']:<12.2f} {metrics['mse']:<12.6f} {metrics['smoothness']:<12.4f}")
except ImportError:
    print(f"{'vmd':<12} 跳过 (需要 vmdpy)")

print("\n" + "=" * 60)

# 测试返回成分
print("\n📦 测试返回分解成分:")
denoiser = Denoiser(method='wavelet', wavelet='db4')
denoised, components = denoiser.denoise(noisy_signal, return_components=True)
print(f"  分解层数: {components['level']}")
print(f"  小波基: {components['wavelet']}")
print(f"  阈值: {components['threshold']:.4f}")
print(f"  噪声标准差估计: {components['sigma']:.4f}")

print("\n✅ 测试完成!")