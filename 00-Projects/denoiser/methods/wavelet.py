"""
小波去噪 - Wavelet Denoising

数学思想:
- 时频多尺度分解
- 高频=噪声，低频=信号
- 阈值处理高频系数后重构
"""
import numpy as np
from typing import Optional, Tuple


def wavelet_denoise(
    signal: np.ndarray,
    wavelet: str = 'db4',
    level: Optional[int] = None,
    threshold_mode: str = 'soft',
    threshold_rule: str = 'universal',
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    小波去噪
    
    Args:
        signal: 输入信号 (1D array)
        wavelet: 小波基 ('db1'-'db38', 'haar', 'sym', 'coif', 'bior')
        level: 分解层数，None则自动选择
        threshold_mode: 'soft' 或 'hard'
        threshold_rule: 阈值规则
            - 'universal': 通用阈值 (VisuShrink)
            - 'sure': Stein无偏风险估计 (SureShrink)
            - 'minimax': Minimax阈值
        return_components: 是否返回分解成分
        
    Returns:
        去噪后的信号
    """
    try:
        import pywt
    except ImportError:
        raise ImportError("请安装 pywt: pip install PyWavelets")
    
    signal = np.asarray(signal, dtype=np.float64)
    n = len(signal)
    
    # 自动选择分解层数
    if level is None:
        level = pywt.dwt_max_level(n, pywt.Wavelet(wavelet).dec_len)
        level = min(level, 5)  # 限制最大5层
    
    # 小波分解
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    
    # 估计噪声标准差 (使用最高频系数)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    
    # 计算阈值
    if threshold_rule == 'universal':
        threshold = sigma * np.sqrt(2 * np.log(n))
    elif threshold_rule == 'sure':
        # SureShrink - 每层独立阈值
        threshold = _sure_threshold(coeffs[-1], sigma)
    elif threshold_rule == 'minimax':
        threshold = sigma * _minimax_threshold(n)
    else:
        threshold = sigma * np.sqrt(2 * np.log(n))
    
    # 对细节系数进行阈值处理 (保留近似系数)
    denoised_coeffs = [coeffs[0]]  # 保留近似系数
    details = []
    
    for i, c in enumerate(coeffs[1:]):
        if threshold_mode == 'soft':
            denoised_c = pywt.threshold(c, threshold, mode='soft')
        else:
            denoised_c = pywt.threshold(c, threshold, mode='hard')
        denoised_coeffs.append(denoised_c)
        details.append({
            'original': c,
            'denoised': denoised_c,
            'threshold': threshold
        })
    
    # 重构信号
    denoised = pywt.waverec(denoised_coeffs, wavelet)
    
    # 处理边界效应 (可能多一个点)
    denoised = denoised[:n]
    
    if return_components:
        components = {
            'approximation': coeffs[0],
            'details': details,
            'level': level,
            'wavelet': wavelet,
            'threshold': threshold,
            'sigma': sigma
        }
        return denoised, components
    
    return denoised


def _sure_threshold(coeffs: np.ndarray, sigma: float) -> float:
    """Stein无偏风险估计阈值"""
    n = len(coeffs)
    squared = coeffs ** 2
    
    # 排序
    sorted_sq = np.sort(squared)
    
    # 计算风险
    risks = np.zeros(n)
    for i in range(n):
        risks[i] = (n - 2 * (i + 1) + np.sum(sorted_sq[:i+1]) / (sigma ** 2 + 1e-10)) / n
    
    # 最小风险对应的阈值
    min_idx = np.argmin(risks)
    threshold = np.sqrt(sorted_sq[min_idx])
    
    return threshold


def _minimax_threshold(n: int) -> float:
    """Minimax阈值系数"""
    if n <= 32:
        return 0
    elif n <= 256:
        return 1.274
    elif n <= 1024:
        return 1.514
    elif n <= 4096:
        return 1.711
    else:
        return np.sqrt(2 * np.log(n)) * 0.7


# 便捷函数
def wavelet_denoise_auto(signal: np.ndarray, **kwargs) -> np.ndarray:
    """自动小波去噪 (使用默认参数)"""
    return wavelet_denoise(signal, wavelet='db4', threshold_mode='soft', **kwargs)