"""
EMD去噪 - Empirical Mode Decomposition

数学思想:
- 自适应筛选，把信号分解成多个IMF
- 高频IMF通常包含噪声
- 去掉前几个IMF或对IMF阈值处理后重构
"""
import numpy as np
from typing import Optional, Tuple, List


def emd_denoise(
    signal: np.ndarray,
    n_imfs_remove: int = 1,
    imf_threshold: Optional[float] = None,
    mode: str = 'partial',
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    EMD去噪
    
    Args:
        signal: 输入信号
        n_imfs_remove: 去掉的IMF数量 (mode='remove'时使用)
        imf_threshold: IMF系数阈值 (mode='threshold'时使用)
        mode: 去噪模式
            - 'remove': 直接去掉前n个高频IMF
            - 'partial': 部分去除 (保留部分高频成分)
            - 'threshold': 对IMF进行阈值处理
        return_components: 是否返回分解成分
        
    Returns:
        去噪后的信号
    """
    try:
        from PyEMD import EMD
    except ImportError:
        raise ImportError("请安装 PyEMD: pip install PyEMD")
    
    signal = np.asarray(signal, dtype=np.float64)
    n = len(signal)
    
    # EMD分解
    emd = EMD()
    imfs = emd.emd(signal)
    
    # 确保是2D数组
    if imfs.ndim == 1:
        imfs = imfs.reshape(1, -1)
    
    n_imfs = imfs.shape[0]
    
    # 去噪处理
    if mode == 'remove':
        # 直接去掉前n个IMF
        denoised = np.sum(imfs[n_imfs_remove:], axis=0)
        removed_imfs = list(range(n_imfs_remove))
    
    elif mode == 'partial':
        # 部分去除：对第一个IMF降权
        weights = np.ones(n_imfs)
        weights[0] = 0.3  # 第一个IMF降权到30%
        denoised = np.sum(weights[:, np.newaxis] * imfs, axis=0)
        removed_imfs = []
    
    elif mode == 'threshold':
        # 对每个IMF进行阈值处理
        if imf_threshold is None:
            # 自动估计阈值
            imf_threshold = np.std(imfs[0]) * 0.5
        
        denoised_imfs = []
        for i, imf in enumerate(imfs):
            if i < 2:  # 前2个IMF进行阈值处理
                denoised_imf = _threshold_imf(imf, imf_threshold)
            else:
                denoised_imf = imf
            denoised_imfs.append(denoised_imf)
        
        denoised = np.sum(denoised_imfs, axis=0)
        removed_imfs = []
    
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    # 添加残差 (如果有的话)
    residual = signal - np.sum(imfs, axis=0)
    if np.abs(residual).mean() > 1e-10:
        denoised += residual
    
    if return_components:
        components = {
            'imfs': imfs,
            'n_imfs': n_imfs,
            'removed_imfs': removed_imfs,
            'mode': mode,
            'residual': residual
        }
        return denoised, components
    
    return denoised


def _threshold_imf(imf: np.ndarray, threshold: float) -> np.ndarray:
    """对IMF进行软阈值处理"""
    result = np.zeros_like(imf)
    
    # 找到极值点
    for i in range(1, len(imf) - 1):
        if (imf[i] > imf[i-1] and imf[i] > imf[i+1]) or \
           (imf[i] < imf[i-1] and imf[i] < imf[i+1]):
            # 极值点
            if np.abs(imf[i]) > threshold:
                result[i] = imf[i] - np.sign(imf[i]) * threshold
    
    # 线性插值
    mask = result != 0
    if mask.sum() > 1:
        indices = np.where(mask)[0]
        result = np.interp(np.arange(len(imf)), indices, result[indices])
    
    return result


def ceemdan_denoise(
    signal: np.ndarray,
    n_imfs_remove: int = 1,
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    CEEMDAN去噪 (更稳定的EMD变体)
    
    需要安装: pip install PyEMD
    """
    try:
        from PyEMD import CEEMDAN
    except ImportError:
        raise ImportError("请安装 PyEMD: pip install PyEMD")
    
    signal = np.asarray(signal, dtype=np.float64)
    
    # CEEMDAN分解
    ceemdan = CEEMDAN()
    imfs = ceemdan.ceemdan(signal)
    
    if imfs.ndim == 1:
        imfs = imfs.reshape(1, -1)
    
    # 去掉前n个高频IMF
    denoised = np.sum(imfs[n_imfs_remove:], axis=0)
    
    if return_components:
        return denoised, {'imfs': imfs, 'n_imfs': imfs.shape[0]}
    
    return denoised