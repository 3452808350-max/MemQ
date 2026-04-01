#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSI (相对强弱指数) 计算模块

相对强弱指数 (Relative Strength Index) 是一个动量振荡指标，
用于衡量价格变动的速度和幅度，取值范围 0-100。

通常 RSI > 70 表示超买，RSI < 30 表示超卖。
"""

from typing import Union, List
import numpy as np


def calculate_rsi(
    prices: Union[List[float], np.ndarray],
    period: int = 14
) -> np.ndarray:
    """
    计算相对强弱指数 (RSI)
    
    参数:
        prices: 价格序列，支持 list 或 numpy array
        period: 计算周期，默认 14
    
    返回:
        RSI 值序列 (numpy array)，与输入价格序列长度相同
        前 period 个值为 NaN（因为需要足够的历史数据）
    
    异常:
        ValueError: 当输入参数无效时抛出
    """
    # ========== 输入验证 ==========
    # 检查价格序列是否为空
    if prices is None or len(prices) == 0:
        raise ValueError("价格序列不能为空")
    
    # 转换为 numpy 数组以便计算
    prices_array = np.array(prices, dtype=float)
    
    # 检查价格序列长度是否足够
    if len(prices_array) < period + 1:
        raise ValueError(
            f"价格序列长度 ({len(prices_array)}) 必须大于周期 ({period}) + 1"
        )
    
    # 检查周期是否有效
    if period <= 0:
        raise ValueError("周期必须为正整数")
    
    # 检查价格是否都为正数
    if np.any(prices_array <= 0):
        raise ValueError("价格必须为正数")
    
    # ========== 计算价格变化 ==========
    # 计算相邻周期的价格差值
    # deltas[i] = prices[i] - prices[i-1]
    deltas = np.diff(prices_array)
    
    # ========== 分离上涨和下跌 ==========
    # 上涨幅度：正的变化值，下跌为 0
    gains = np.where(deltas > 0, deltas, 0)
    
    # 下跌幅度：负的变化值的绝对值，上涨为 0
    losses = np.where(deltas < 0, -deltas, 0)
    
    # ========== 计算初始平均涨幅和跌幅 ==========
    # 使用前 period 个变化值的简单平均作为初始值
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    # ========== 初始化 RSI 序列 ==========
    # RSI 序列长度与价格序列相同
    rsi = np.full(len(prices_array), np.nan)
    
    # ========== 计算第一个 RSI 值 ==========
    # 第一个 RSI 值位于索引 period 处（因为需要 period+1 个价格数据）
    if avg_loss == 0:
        # 如果没有下跌，RSI 为 100
        rsi[period] = 100.0
    else:
        # RS = 平均涨幅 / 平均跌幅
        rs = avg_gain / avg_loss
        # RSI = 100 - (100 / (1 + RS))
        rsi[period] = 100 - (100 / (1 + rs))
    
    # ========== 计算后续 RSI 值 ==========
    # 使用平滑方式（Wilder's Smoothing）计算后续的平均涨幅和跌幅
    # 公式：新平均 = (前平均 * (period-1) + 当前值) / period
    for i in range(period, len(deltas)):
        # 更新平均涨幅和跌幅
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # 计算 RSI
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100 - (100 / (1 + rs))
    
    return rsi


def main():
    """主函数：演示 RSI 计算"""
    # 示例输入
    prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
    period = 14
    
    print("=" * 60)
    print("RSI (相对强弱指数) 计算演示")
    print("=" * 60)
    print(f"\n输入价格序列: {prices}")
    print(f"计算周期: {period}")
    print(f"价格序列长度: {len(prices)}")
    
    # 注意：示例数据长度 (10) 小于周期 +1 (15)，会触发错误
    # 这里我们使用更短的周期来演示
    demo_period = 3
    print(f"\n为演示目的，使用周期: {demo_period}")
    print("-" * 60)
    
    try:
        rsi_values = calculate_rsi(prices, period=demo_period)
        
        print("\n计算结果:")
        print(f"{'索引':<6} {'价格':<10} {'RSI':<10}")
        print("-" * 60)
        
        for i, (price, rsi) in enumerate(zip(prices, rsi_values)):
            if np.isnan(rsi):
                print(f"{i:<6} {price:<10.2f} {'NaN':<10}")
            else:
                print(f"{i:<6} {price:<10.2f} {rsi:<10.2f}")
        
        print("-" * 60)
        print("\n说明:")
        print(f"- 前 {demo_period} 个值为 NaN（需要足够的历史数据）")
        print(f"- 第一个 RSI 值在索引 {demo_period} 处")
        print("- RSI > 70: 超买区域")
        print("- RSI < 30: 超卖区域")
        
    except ValueError as e:
        print(f"\n错误: {e}")
    
    # ========== 使用更长的价格序列演示标准周期 ==========
    print("\n" + "=" * 60)
    print("使用标准周期 (14) 和更长的价格序列")
    print("=" * 60)
    
    # 生成一个更长的价格序列（20 个数据点）
    np.random.seed(42)  # 固定随机种子以便复现
    long_prices = 100 + np.cumsum(np.random.randn(20) * 2)
    long_prices = np.maximum(long_prices, 1)  # 确保价格为正
    
    print(f"\n价格序列长度: {len(long_prices)}")
    print(f"计算周期: 14")
    
    try:
        rsi_14 = calculate_rsi(long_prices, period=14)
        
        print("\n计算结果:")
        print(f"{'索引':<6} {'价格':<12} {'RSI':<10} {'状态':<10}")
        print("-" * 60)
        
        for i, (price, rsi) in enumerate(zip(long_prices, rsi_14)):
            if np.isnan(rsi):
                status = "-"
            elif rsi > 70:
                status = "超买"
            elif rsi < 30:
                status = "超卖"
            else:
                status = "正常"
            
            print(f"{i:<6} {price:<12.2f} {rsi:<10.2f} {status:<10}")
        
        print("-" * 60)
        print(f"\n最新 RSI 值: {rsi_14[-1]:.2f}")
        
    except ValueError as e:
        print(f"\n错误: {e}")


if __name__ == "__main__":
    main()
