"""
去噪方法实现
"""
from .wavelet import wavelet_denoise
from .emd import emd_denoise
from .vmd import vmd_denoise
from .kalman import kalman_denoise
from .ssa import ssa_denoise

__all__ = [
    'wavelet_denoise',
    'emd_denoise',
    'vmd_denoise',
    'kalman_denoise',
    'ssa_denoise',
]