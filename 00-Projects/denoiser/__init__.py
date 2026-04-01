"""
Denoiser - 金融时间序列去噪模块

支持方法:
- wavelet: 小波去噪
- emd: 经验模态分解
- vmd: 变分模态分解
- kalman: 卡尔曼滤波
- ssa: 奇异谱分析
"""

from .core import Denoiser
from .methods import (
    wavelet_denoise,
    emd_denoise,
    vmd_denoise,
    kalman_denoise,
    ssa_denoise,
)

__all__ = [
    'Denoiser',
    'wavelet_denoise',
    'emd_denoise',
    'vmd_denoise',
    'kalman_denoise',
    'ssa_denoise',
]

__version__ = '1.0.0'