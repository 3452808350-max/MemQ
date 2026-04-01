"""
去噪模块 - Kalman滤波器实现
用于平滑价格数据，消除市场噪音
"""
import numpy as np
from typing import Tuple, Optional

class KalmanFilter:
    """一维卡尔曼滤波器"""
    
    def __init__(self, process_noise: float = 0.01, measurement_noise: float = 0.1):
        """
        初始化卡尔曼滤波器
        
        Args:
            process_noise: 过程噪声Q，控制平滑程度
                           较小值 = 更平滑，但响应慢
                           较大值 = 响应快，但噪音多
            measurement_noise: 测量噪声R，反映数据可信度
                               较小值 = 更信任观测值
                               较大值 = 更信任预测值
        """
        self.Q = process_noise      # 过程噪声协方差
        self.R = measurement_noise  # 测量噪声协方差
        self.P = 1.0                # 估计误差协方差
        self.x = None               # 状态估计
        
    def update(self, measurement: float) -> float:
        """更新滤波器状态并返回滤波后的值"""
        if self.x is None:
            self.x = measurement
            return measurement
        
        # 预测步骤
        P_pred = self.P + self.Q
        
        # 更新步骤
        K = P_pred / (P_pred + self.R)  # 卡尔曼增益
        self.x = self.x + K * (measurement - self.x)
        self.P = (1 - K) * P_pred
        
        return self.x
    
    def reset(self):
        """重置滤波器状态"""
        self.P = 1.0
        self.x = None


class Denoiser:
    """价格去噪器 - 支持多种方法"""
    
    def __init__(self, method: str = 'kalman', 
                 process_noise: float = 0.01,
                 measurement_noise: float = 0.1):
        """
        初始化去噪器
        
        Args:
            method: 去噪方法 ('kalman', 'ema', 'sma')
            process_noise: Kalman过程噪声Q
            measurement_noise: Kalman测量噪声R
        """
        self.method = method
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        
    def denoise(self, data: np.ndarray) -> np.ndarray:
        """对数据序列进行去噪
        
        Args:
            data: 原始数据序列
            
        Returns:
            去噪后的数据序列
        """
        if len(data) == 0:
            return data
            
        if self.method == 'kalman':
            return self._kalman_denoise(data)
        elif self.method == 'ema':
            return self._ema_denoise(data)
        elif self.method == 'sma':
            return self._sma_denoise(data)
        else:
            return data
    
    def _kalman_denoise(self, data: np.ndarray) -> np.ndarray:
        """Kalman滤波去噪"""
        kf = KalmanFilter(
            process_noise=self.process_noise,
            measurement_noise=self.measurement_noise
        )
        
        result = np.zeros_like(data, dtype=float)
        for i, val in enumerate(data):
            result[i] = kf.update(val)
            
        return result
    
    def _ema_denoise(self, data: np.ndarray, span: int = 5) -> np.ndarray:
        """EMA去噪"""
        alpha = 2.0 / (span + 1)
        result = np.zeros_like(data, dtype=float)
        result[0] = data[0]
        
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
            
        return result
    
    def _sma_denoise(self, data: np.ndarray, window: int = 5) -> np.ndarray:
        """简单移动平均去噪"""
        result = np.zeros_like(data, dtype=float)
        
        for i in range(len(data)):
            start = max(0, i - window + 1)
            result[i] = np.mean(data[start:i+1])
            
        return result


class AdaptiveDenoiser:
    """自适应去噪器 - 根据市场波动自动调整参数"""
    
    def __init__(self, base_process_noise: float = 0.01,
                 base_measurement_noise: float = 0.1):
        """
        Args:
            base_process_noise: 基础过程噪声
            base_measurement_noise: 基础测量噪声
        """
        self.base_Q = base_process_noise
        self.base_R = base_measurement_noise
        
    def estimate_volatility(self, data: np.ndarray, window: int = 20) -> float:
        """估计波动率"""
        if len(data) < window:
            window = len(data)
            
        returns = np.diff(data[-window:]) / data[-window:-1]
        return np.std(returns) if len(returns) > 0 else 0.02
    
    def get_adaptive_params(self, data: np.ndarray) -> Tuple[float, float]:
        """根据波动率自适应调整参数"""
        vol = self.estimate_volatility(data)
        
        # 高波动时：增加测量噪声R（更平滑），减少过程噪声Q（响应更慢）
        # 低波动时：减少测量噪声R（更灵敏），增加过程噪声Q（响应更快）
        
        if vol > 0.03:  # 高波动
            Q = self.base_Q * 0.5
            R = self.base_R * 2.0
        elif vol > 0.02:  # 中等波动
            Q = self.base_Q * 0.8
            R = self.base_R * 1.5
        else:  # 低波动
            Q = self.base_Q * 1.0
            R = self.base_R * 1.0
            
        return Q, R
    
    def denoise(self, data: np.ndarray) -> np.ndarray:
        """自适应去噪"""
        if len(data) < 20:
            # 数据不足，使用基础参数
            denoiser = Denoiser('kalman', self.base_Q, self.base_R)
            return denoiser.denoise(data)
        
        # 每20个点重新估计参数
        result = np.zeros_like(data, dtype=float)
        Q, R = self.base_Q, self.base_R
        kf = KalmanFilter(Q, R)
        
        for i, val in enumerate(data):
            if i > 0 and i % 20 == 0:
                Q, R = self.get_adaptive_params(data[:i+1])
                kf.Q = Q
                kf.R = R
            result[i] = kf.update(val)
            
        return result


# ============ 便捷函数 ============

def denoise_price(data: np.ndarray, method: str = 'kalman',
                  process_noise: float = 0.01,
                  measurement_noise: float = 0.1) -> np.ndarray:
    """便捷函数：对价格序列去噪"""
    denoiser = Denoiser(method, process_noise, measurement_noise)
    return denoiser.denoise(data)


if __name__ == "__main__":
    # 测试
    import matplotlib.pyplot as plt
    
    # 生成测试数据
    np.random.seed(42)
    n = 100
    true_signal = np.sin(np.linspace(0, 4*np.pi, n)) * 10 + 100
    noise = np.random.randn(n) * 2
    noisy_data = true_signal + noise
    
    # 测试不同参数
    params = [
        (0.01, 0.1, "默认参数"),
        (0.005, 0.2, "高平滑"),
        (0.02, 0.05, "高响应"),
    ]
    
    print("去噪模块测试:")
    for Q, R, name in params:
        denoised = denoise_price(noisy_data, 'kalman', Q, R)
        mse = np.mean((denoised - true_signal)**2)
        print(f"  {name}: Q={Q}, R={R}, MSE={mse:.4f}")