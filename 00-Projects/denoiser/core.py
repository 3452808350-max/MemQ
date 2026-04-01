"""
Denoiser 核心类 - 统一接口
"""
import numpy as np
import pandas as pd
from typing import Union, Optional, Dict, Any
from .methods import (
    wavelet_denoise,
    emd_denoise,
    vmd_denoise,
    kalman_denoise,
    ssa_denoise,
)


class Denoiser:
    """
    金融时间序列去噪器
    
    使用示例:
        denoiser = Denoiser(method='wavelet')
        clean_signal = denoiser.denoise(noisy_signal)
        
        # 或者批量处理
        denoiser = Denoiser()
        results = denoiser.denoise_batch(df, columns=['Close', 'Volume'])
    """
    
    METHODS = {
        'wavelet': wavelet_denoise,
        'emd': emd_denoise,
        'vmd': vmd_denoise,
        'kalman': kalman_denoise,
        'ssa': ssa_denoise,
    }
    
    def __init__(
        self,
        method: str = 'wavelet',
        **method_params
    ):
        """
        初始化去噪器
        
        Args:
            method: 去噪方法 ('wavelet', 'emd', 'vmd', 'kalman', 'ssa')
            **method_params: 方法特定参数
        """
        if method not in self.METHODS:
            raise ValueError(f"Unknown method: {method}. Available: {list(self.METHODS.keys())}")
        
        self.method = method
        self.method_params = method_params
        self._func = self.METHODS[method]
    
    def denoise(
        self,
        signal: Union[np.ndarray, pd.Series],
        return_components: bool = False
    ) -> Union[np.ndarray, tuple]:
        """
        对单个信号去噪
        
        Args:
            signal: 输入信号
            return_components: 是否返回分解的成分
            
        Returns:
            去噪后的信号，如果 return_components=True 则返回 (去噪信号, 成分字典)
        """
        if isinstance(signal, pd.Series):
            signal = signal.values
        
        return self._func(signal, return_components=return_components, **self.method_params)
    
    def denoise_batch(
        self,
        df: pd.DataFrame,
        columns: Optional[list] = None,
        inplace: bool = False,
        suffix: str = '_denoised'
    ) -> pd.DataFrame:
        """
        批量对DataFrame的多个列去噪
        
        Args:
            df: 输入DataFrame
            columns: 要处理的列，None则处理所有数值列
            inplace: 是否原地修改
            suffix: 去噪列的后缀
            
        Returns:
            处理后的DataFrame
        """
        if not inplace:
            df = df.copy()
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col in df.columns:
                df[f'{col}{suffix}'] = self.denoise(df[col].values)
        
        return df
    
    def compare_methods(
        self,
        signal: Union[np.ndarray, pd.Series],
        methods: Optional[list] = None
    ) -> Dict[str, np.ndarray]:
        """
        对比多个去噪方法的效果
        
        Args:
            signal: 输入信号
            methods: 要对比的方法列表，None则对比所有
            
        Returns:
            字典 {方法名: 去噪信号}
        """
        if isinstance(signal, pd.Series):
            signal = signal.values
        
        if methods is None:
            methods = list(self.METHODS.keys())
        
        results = {}
        for method in methods:
            try:
                func = self.METHODS[method]
                results[method] = func(signal)
            except Exception as e:
                results[method] = f"Error: {e}"
        
        return results
    
    @staticmethod
    def evaluate(
        original: np.ndarray,
        denoised: np.ndarray,
        metrics: Optional[list] = None
    ) -> Dict[str, float]:
        """
        评估去噪效果
        
        Args:
            original: 原始信号
            denoised: 去噪信号
            metrics: 评估指标列表
            
        Returns:
            指标字典
        """
        if metrics is None:
            metrics = ['snr', 'mse', 'mae', 'smoothness']
        
        results = {}
        noise = original - denoised
        
        if 'snr' in metrics:
            # 信噪比
            signal_power = np.var(denoised)
            noise_power = np.var(noise)
            results['snr'] = 10 * np.log10(signal_power / (noise_power + 1e-10))
        
        if 'mse' in metrics:
            results['mse'] = np.mean(noise ** 2)
        
        if 'mae' in metrics:
            results['mae'] = np.mean(np.abs(noise))
        
        if 'smoothness' in metrics:
            # 平滑度：一阶差分的标准差
            results['smoothness'] = np.std(np.diff(denoised))
        
        return results