"""
VMD去噪 - Variational Mode Decomposition

数学思想:
- 变分优化问题，最小化各模态的带宽
- 解决EMD的模态混叠问题
- 分解更稳定、可重现
"""
import numpy as np
from typing import Optional, Tuple


def vmd_denoise(
    signal: np.ndarray,
    n_modes: int = 4,
    alpha: float = 2000,
    tau: float = 0,
    dc: bool = False,
    tol: float = 1e-7,
    n_modes_remove: int = 1,
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    VMD去噪
    
    Args:
        signal: 输入信号
        n_modes: 模态数量 K
        alpha: 带宽约束参数 (越大带宽越窄)
        tau: 噪声容忍参数 (0表示无噪声)
        dc: 是否包含直流分量
        tol: 收敛容差
        n_modes_remove: 去掉的高频模态数量
        return_components: 是否返回分解成分
        
    Returns:
        去噪后的信号
    """
    try:
        from vmdpy import VMD
    except ImportError:
        # 如果没有vmdpy，使用自定义实现
        return _vmd_denoise_custom(signal, n_modes, alpha, tau, dc, tol, 
                                    n_modes_remove, return_components)
    
    signal = np.asarray(signal, dtype=np.float64)
    
    # VMD分解
    u, u_hat, omega = VMD(signal, alpha, tau, n_modes, dc, tol, 500)
    
    # u.shape = (n_modes, signal_length)
    # omega 是各模态的中心频率
    
    # 按频率排序模态 (从高到低)
    freq_order = np.argsort(omega[:, -1])[::-1]
    u_sorted = u[freq_order]
    
    # 去掉高频模态
    denoised = np.sum(u_sorted[n_modes_remove:], axis=0)
    
    if return_components:
        components = {
            'modes': u_sorted,
            'center_frequencies': omega,
            'n_modes': n_modes,
            'removed_modes': list(freq_order[:n_modes_remove])
        }
        return denoised, components
    
    return denoised


def _vmd_denoise_custom(
    signal: np.ndarray,
    K: int,
    alpha: float,
    tau: float,
    dc: bool,
    tol: float,
    n_modes_remove: int,
    return_components: bool
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    自定义VMD实现 (简化版)
    
    基于: Dragomiretskiy & Zosso (2014)
    "Variational Mode Decomposition"
    """
    T = len(signal)
    fs = 1.0  # 采样频率
    
    # 镜像扩展
    f = np.concatenate([signal[:T//2][::-1], signal, signal[T//2:][::-1]])
    T_extended = len(f)
    
    # 频率离散化
    freqs = np.fft.fftfreq(T_extended) * T_extended
    
    # 初始化
    u_hat = np.zeros((K, T_extended), dtype=complex)
    omega = np.zeros(K)
    
    # 初始频率均匀分布
    if not dc:
        omega = np.linspace(0.5, 1.5, K) * np.pi / 2
    
    # 信号的FFT
    f_hat = np.fft.fft(f)
    
    # ADMM迭代
    n_iter = 100
    u_hat_prev = np.zeros_like(u_hat)
    
    for _ in range(n_iter):
        # 更新每个模态
        for k in range(K):
            # 其他模态的和
            sum_uk = np.sum(u_hat, axis=0) - u_hat[k]
            
            # 更新模态 (频域)
            u_hat[k] = (f_hat - sum_uk) / (1 + alpha * (freqs - omega[k]) ** 2)
            
            # 更新中心频率
            if k > 0 or not dc:
                numerator = np.sum(freqs * np.abs(u_hat[k]) ** 2)
                denominator = np.sum(np.abs(u_hat[k]) ** 2) + 1e-10
                omega[k] = numerator / denominator
        
        # 收敛检查
        if np.sum(np.abs(u_hat - u_hat_prev) ** 2) < tol:
            break
        u_hat_prev = u_hat.copy()
    
    # 转换回时域
    u = np.zeros((K, T_extended))
    for k in range(K):
        u[k] = np.real(np.fft.ifft(u_hat[k]))
    
    # 去掉镜像部分
    u = u[:, T//2:T//2+T]
    
    # 按频率排序
    omega_final = omega.copy()
    freq_order = np.argsort(omega_final)
    u_sorted = u[freq_order]
    
    # 去掉高频模态 (通常高频对应噪声)
    denoised = np.sum(u_sorted[:K-n_modes_remove], axis=0)
    
    if return_components:
        components = {
            'modes': u_sorted,
            'center_frequencies': omega_final,
            'n_modes': K,
            'custom_implementation': True
        }
        return denoised, components
    
    return denoised


def vmd_denoise_auto(signal: np.ndarray, **kwargs) -> np.ndarray:
    """自动VMD去噪"""
    return vmd_denoise(signal, n_modes=4, alpha=2000, n_modes_remove=1, **kwargs)