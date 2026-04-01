"""
卡尔曼滤波去噪 - Kalman Filter Denoising

数学思想:
- 状态空间模型 + 贝叶斯递归估计
- 预测-更新循环
- 动态平衡模型预测与观测
"""
import numpy as np
from typing import Optional, Tuple


def kalman_denoise(
    signal: np.ndarray,
    process_noise: float = 0.01,
    measurement_noise: float = 1.0,
    initial_state: Optional[float] = None,
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    卡尔曼滤波去噪
    
    Args:
        signal: 输入信号
        process_noise: 过程噪声 Q (模型不确定性)
        measurement_noise: 观测噪声 R (数据噪声)
        initial_state: 初始状态估计
        return_components: 是否返回分解成分
        
    Returns:
        去噪后的信号
    """
    signal = np.asarray(signal, dtype=np.float64)
    n = len(signal)
    
    # 状态空间模型
    # x_t = x_{t-1} + w_t  (状态方程: 随机游走)
    # y_t = x_t + v_t      (观测方程)
    
    # 初始化
    if initial_state is None:
        x = signal[0]
    else:
        x = initial_state
    
    P = 1.0  # 状态协方差
    
    Q = process_noise   # 过程噪声
    R = measurement_noise  # 观测噪声
    
    # 存储
    x_filtered = np.zeros(n)
    P_history = np.zeros(n)
    innovations = np.zeros(n)  # 新息 (预测误差)
    
    for t in range(n):
        # 预测步骤
        x_pred = x
        P_pred = P + Q
        
        # 更新步骤
        y = signal[t]
        K = P_pred / (P_pred + R)  # 卡尔曼增益
        innovation = y - x_pred
        x = x_pred + K * innovation
        P = (1 - K) * P_pred
        
        # 存储
        x_filtered[t] = x
        P_history[t] = P
        innovations[t] = innovation
    
    if return_components:
        components = {
            'filtered_states': x_filtered,
            'state_covariance': P_history,
            'innovations': innovations,
            'kalman_gain': P_history / (P_history + R),
            'process_noise': Q,
            'measurement_noise': R
        }
        return x_filtered, components
    
    return x_filtered


def kalman_denoise_adaptive(
    signal: np.ndarray,
    window: int = 20,
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    自适应卡尔曼滤波 - 动态估计噪声参数
    
    Args:
        signal: 输入信号
        window: 噪声估计窗口
        return_components: 是否返回分解成分
        
    Returns:
        去噪后的信号
    """
    signal = np.asarray(signal, dtype=np.float64)
    n = len(signal)
    
    # 初始噪声估计
    R = np.var(np.diff(signal[:window]))
    Q = R * 0.01
    
    x = signal[0]
    P = 1.0
    
    x_filtered = np.zeros(n)
    R_history = np.zeros(n)
    
    for t in range(n):
        # 动态更新R
        if t >= window:
            R = np.var(signal[t-window:t])
        
        R_history[t] = R
        
        # 卡尔曼滤波
        x_pred = x
        P_pred = P + Q
        
        y = signal[t]
        K = P_pred / (P_pred + R)
        x = x_pred + K * (y - x_pred)
        P = (1 - K) * P_pred
        
        x_filtered[t] = x
    
    if return_components:
        components = {
            'filtered_states': x_filtered,
            'adaptive_R': R_history,
            'final_Q': Q
        }
        return x_filtered, components
    
    return x_filtered


def kalman_smoother(
    signal: np.ndarray,
    process_noise: float = 0.01,
    measurement_noise: float = 1.0,
    return_components: bool = False
) -> np.ndarray | Tuple[np.ndarray, dict]:
    """
    卡尔曼平滑器 (RTS平滑)
    
    前向滤波 + 后向平滑，比纯滤波更平滑
    """
    signal = np.asarray(signal, dtype=np.float64)
    n = len(signal)
    
    # 前向滤波
    x_fwd = np.zeros(n)
    P_fwd = np.zeros(n)
    
    x = signal[0]
    P = 1.0
    Q = process_noise
    R = measurement_noise
    
    for t in range(n):
        x_pred = x
        P_pred = P + Q
        K = P_pred / (P_pred + R)
        x = x_pred + K * (signal[t] - x_pred)
        P = (1 - K) * P_pred
        x_fwd[t] = x
        P_fwd[t] = P
    
    # 后向平滑 (RTS)
    x_smooth = np.zeros(n)
    x_smooth[-1] = x_fwd[-1]
    
    for t in range(n-2, -1, -1):
        P_pred = P_fwd[t] + Q
        J = P_fwd[t] / P_pred
        x_smooth[t] = x_fwd[t] + J * (x_smooth[t+1] - x_fwd[t])
    
    if return_components:
        components = {
            'forward_states': x_fwd,
            'smoothed_states': x_smooth,
            'forward_covariance': P_fwd
        }
        return x_smooth, components
    
    return x_smooth