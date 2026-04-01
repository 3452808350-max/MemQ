"""
DSS 集成示例 - 如何在选股系统中使用去噪模块
"""
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from denoiser import Denoiser


def denoise_stock_data(
    df: pd.DataFrame,
    method: str = 'wavelet',
    columns: list = None
) -> pd.DataFrame:
    """
    对股票数据进行去噪处理
    
    Args:
        df: 包含 OHLCV 数据的 DataFrame
        method: 去噪方法
        columns: 要处理的列
        
    Returns:
        添加了去噪列的 DataFrame
    """
    if columns is None:
        columns = ['Close', 'High', 'Low', 'Open']
    
    denoiser = Denoiser(method=method)
    
    result = df.copy()
    for col in columns:
        if col in df.columns:
            result[f'{col}_denoised'] = denoiser.denoise(df[col].values)
    
    return result


def calculate_denoised_indicators(
    df: pd.DataFrame,
    price_col: str = 'Close'
) -> pd.DataFrame:
    """
    基于去噪价格计算技术指标
    
    优势：减少噪声对指标的影响，更稳定的信号
    """
    denoiser = Denoiser(method='wavelet')
    
    result = df.copy()
    
    # 去噪价格
    denoised_price = denoiser.denoise(df[price_col].values)
    result['price_denoised'] = denoised_price
    
    # 基于去噪价格计算MA
    result['MA5_denoised'] = pd.Series(denoised_price).rolling(5).mean()
    result['MA20_denoised'] = pd.Series(denoised_price).rolling(20).mean()
    
    # 去噪后的波动率
    returns = pd.Series(denoised_price).pct_change()
    result['volatility_denoised'] = returns.rolling(20).std()
    
    return result


def detect_trend_clean(
    df: pd.DataFrame,
    price_col: str = 'Close',
    method: str = 'kalman'
) -> dict:
    """
    使用去噪方法检测趋势
    
    Returns:
        趋势信息字典
    """
    denoiser = Denoiser(method=method)
    
    if method == 'kalman':
        # 卡尔曼滤波返回状态估计
        denoised, components = denoiser.denoise(
            df[price_col].values, 
            return_components=True
        )
        
        # 使用状态协方差判断趋势稳定性
        P = components['state_covariance']
        stability = 1.0 / (np.mean(P[-20:]) + 1e-6)  # 越小越稳定
    else:
        denoised = denoiser.denoise(df[price_col].values)
        stability = 1.0
    
    # 计算趋势方向
    recent = denoised[-20:]
    slope = (recent[-1] - recent[0]) / len(recent)
    
    # 判断趋势
    if slope > 0.001:
        trend = 'up'
    elif slope < -0.001:
        trend = 'down'
    else:
        trend = 'sideways'
    
    return {
        'trend': trend,
        'slope': slope,
        'stability': stability,
        'current_price_denoised': denoised[-1],
        'original_price': df[price_col].iloc[-1]
    }


# 使用示例
if __name__ == "__main__":
    # 模拟数据
    np.random.seed(42)
    n = 250
    t = np.linspace(0, 10, n)
    price = 100 + 20 * np.sin(t) + np.random.normal(0, 2, n)
    
    df = pd.DataFrame({
        'Close': price,
        'High': price + np.random.uniform(0, 1, n),
        'Low': price - np.random.uniform(0, 1, n),
    })
    
    print("DSS 去噪集成示例")
    print("=" * 50)
    
    # 示例1: 批量去噪
    df_denoised = denoise_stock_data(df, method='wavelet')
    print(f"\n去噪后的列: {[c for c in df_denoised.columns if 'denoised' in c]}")
    
    # 示例2: 计算去噪指标
    df_indicators = calculate_denoised_indicators(df)
    print(f"\n去噪指标列: {[c for c in df_indicators.columns if 'denoised' in c]}")
    
    # 示例3: 趋势检测
    trend_info = detect_trend_clean(df, method='kalman')
    print(f"\n趋势检测:")
    print(f"  方向: {trend_info['trend']}")
    print(f"  斜率: {trend_info['slope']:.4f}")
    print(f"  原始价格: {trend_info['original_price']:.2f}")
    print(f"  去噪价格: {trend_info['current_price_denoised']:.2f}")
    
    print("\n✅ 集成示例完成")