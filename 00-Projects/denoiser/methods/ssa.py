"""
SSA去噪 - Singular Spectrum Analysis

数学思想:
- 时间序列 → 轨迹矩阵 → SVD → 分组 → 重构
- 大奇异值 = 信号成分，小奇异值 = 噪声
- 类似PCA的时序版本
"""
import numpy as np
from typing import Optional, Tuple


def ssa_denoise(
    signal: np.ndarray,
    window_length: Optional[int] = None,
    n_components: Optional[int] = None,
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    SSA去噪
    
    Args:
        signal: 输入信号
        window_length: 窗口长度 L (嵌入维度)
        n_components: 保留的主成分数量
        return_components: 是否返回分解成分
        
    Returns:
        去噪后的信号
    """
    signal = np.asarray(signal, dtype=np.float64)
    n = len(signal)
    
    # 默认窗口长度
    if window_length is None:
        window_length = min(n // 2, 50)
    
    L = window_length
    K = n - L + 1  # 轨迹矩阵的列数
    
    # Step 1: 嵌入 - 构造轨迹矩阵
    X = np.zeros((L, K))
    for i in range(L):
        X[i] = signal[i:i+K]
    
    # Step 2: SVD
    U, s, Vh = np.linalg.svd(X, full_matrices=False)
    
    # 确定保留的成分数量
    if n_components is None:
        # 自动选择：保留解释95%方差的成分
        total_var = np.sum(s ** 2)
        cumsum = np.cumsum(s ** 2)
        n_components = np.searchsorted(cumsum / total_var, 0.95) + 1
        n_components = min(n_components, len(s) // 2)  # 最多保留一半
    
    # Step 3: 分组 - 选择主成分
    selected = list(range(n_components))
    
    # Step 4: 对角平均 - 重构时间序列
    X_reconstructed = U[:, selected] @ np.diag(s[selected]) @ Vh[selected, :]
    denoised = _diagonal_averaging(X_reconstructed)
    
    if return_components:
        components = {
            'singular_values': s,
            'eigen_vectors': U,
            'n_components': n_components,
            'window_length': L,
            'explained_variance': s[:n_components] ** 2 / np.sum(s ** 2),
            'trajectory_matrix': X
        }
        return denoised, components
    
    return denoised


def _diagonal_averaging(X: np.ndarray) -> np.ndarray:
    """
    对角平均 - 矩阵转时间序列
    
    将Hankel矩阵通过反对角线平均还原为时间序列
    """
    L, K = X.shape
    n = L + K - 1
    
    result = np.zeros(n)
    
    for k in range(n):
        if k < L:
            # 上三角区域
            count = k + 1
            total = 0
            for i in range(count):
                j = k - i
                if i < L and j < K:
                    total += X[i, j]
            result[k] = total / count
        elif k < K:
            # 中间区域
            count = L
            total = 0
            for i in range(L):
                j = k - i
                if j >= 0 and j < K:
                    total += X[i, j]
            result[k] = total / count
        else:
            # 下三角区域
            count = n - k
            total = 0
            for i in range(count):
                j = k - (L - 1 - i)
                if j >= 0 and j < K:
                    total += X[L - 1 - i, j]
            result[k] = total / count
    
    return result


def ssa_decompose(
    signal: np.ndarray,
    window_length: Optional[int] = None
) -> Tuple[np.ndarray, dict]:
    """
    SSA分解 - 返回所有成分
    
    Returns:
        components: 各主成分重构的信号
        info: 分解信息
    """
    signal = np.asarray(signal, dtype=np.float64)
    n = len(signal)
    
    if window_length is None:
        window_length = min(n // 2, 50)
    
    L = window_length
    K = n - L + 1
    
    # 轨迹矩阵
    X = np.zeros((L, K))
    for i in range(L):
        X[i] = signal[i:i+K]
    
    # SVD
    U, s, Vh = np.linalg.svd(X, full_matrices=False)
    
    # 每个成分重构
    components = []
    for i in range(min(L, K)):
        Xi = s[i] * np.outer(U[:, i], Vh[i, :])
        comp = _diagonal_averaging(Xi)
        components.append(comp)
    
    info = {
        'singular_values': s,
        'window_length': L,
        'n_components': len(components)
    }
    
    return np.array(components), info


def ssa_separate_trend_seasonal(
    signal: np.ndarray,
    window_length: Optional[int] = None,
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    SSA分离趋势和季节性成分
    
    Returns:
        trend: 趋势成分
        seasonal: 季节性成分
        noise: 噪声成分
    """
    components, info = ssa_decompose(signal, window_length)
    s = info['singular_values']
    
    # 第一个成分通常是趋势
    trend = components[0]
    
    # 中间成分可能是季节性
    # 通过周期性检测确定
    seasonal = np.zeros_like(signal)
    for i in range(1, min(5, len(components))):
        comp = components[i]
        # 简单判断：如果有明显周期性
        seasonal += comp
    
    # 剩余为噪声
    noise = signal - trend - seasonal
    
    if return_components:
        components_dict = {
            'trend': trend,
            'seasonal': seasonal,
            'noise': noise,
            'singular_values': s
        }
        return trend + seasonal, components_dict
    
    return trend + seasonal