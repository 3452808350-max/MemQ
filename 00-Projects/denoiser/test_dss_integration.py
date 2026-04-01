"""
Denoiser + DSS 集成测试
评估去噪对技术指标稳定性的影响
"""
import numpy as np
import pandas as pd
import time
import sys
import os
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from denoiser import Denoiser
from denoiser.dss_integration import denoise_stock_data, detect_trend_clean

# ============ 技术指标计算 ============
def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """计算 RSI"""
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi.values

def calculate_macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """计算 MACD"""
    prices = pd.Series(prices)
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        'macd': macd_line.values,
        'signal': signal_line.values,
        'histogram': histogram.values
    }

def calculate_ma(prices: np.ndarray, periods: list = [5, 10, 20, 60]) -> dict:
    """计算均线"""
    prices = pd.Series(prices)
    result = {}
    for p in periods:
        result[f'MA{p}'] = prices.rolling(window=p).mean().values
    return result

def calculate_bollinger(prices: np.ndarray, period: int = 20) -> dict:
    """计算布林带"""
    prices = pd.Series(prices)
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = middle + 2 * std
    lower = middle - 2 * std
    return {
        'upper': upper.values,
        'middle': middle.values,
        'lower': lower.values
    }

# ============ 稳定性指标 ============
def calculate_volatility(indicator: np.ndarray, window: int = 20) -> float:
    """计算指标波动率（用于衡量稳定性）"""
    indicator = pd.Series(indicator).dropna()
    if len(indicator) < window:
        return np.nan
    return indicator.tail(window).std()

def calculate_signal_reversals(signal: np.ndarray, threshold: float = 0) -> int:
    """计算信号反转次数（MACD 从正转负或反之）"""
    signal = pd.Series(signal).dropna()
    reversals = 0
    for i in range(1, len(signal)):
        if signal.iloc[i-1] > threshold and signal.iloc[i] < threshold:
            reversals += 1
        elif signal.iloc[i-1] < threshold and signal.iloc[i] > threshold:
            reversals += 1
    return reversals

def calculate_ma_crossovers(ma_fast: np.ndarray, ma_slow: np.ndarray) -> int:
    """计算均线交叉次数"""
    ma_fast = pd.Series(ma_fast).dropna()
    ma_slow = pd.Series(ma_slow).dropna()
    min_len = min(len(ma_fast), len(ma_slow))
    ma_fast = ma_fast.iloc[:min_len]
    ma_slow = ma_slow.iloc[:min_len]
    
    crossovers = 0
    for i in range(1, min_len):
        diff_prev = ma_fast.iloc[i-1] - ma_slow.iloc[i-1]
        diff_curr = ma_fast.iloc[i] - ma_slow.iloc[i]
        if diff_prev * diff_curr < 0:  # 符号变化 = 交叉
            crossovers += 1
    return crossovers

# ============ 主测试函数 ============
def test_denoiser_impact(symbol: str, df: pd.DataFrame) -> dict:
    """
    测试去噪对技术指标的影响
    
    Returns:
        包含各项测试结果的字典
    """
    print(f"\n{'='*60}")
    print(f"📊 测试股票: {symbol}")
    print(f"{'='*60}")
    
    prices = df['Close'].values
    
    # 测试三种去噪方法（根据 Denoiser 支持的方法）
    methods = ['wavelet', 'kalman', 'emd']
    results = {
        'symbol': symbol,
        'data_points': len(prices),
        'price_range': (prices.min(), prices.max()),
        'methods': {}
    }
    
    for method in methods:
        print(f"\n🔹 方法: {method.upper()}")
        method_start = time.time()
        
        # 去噪处理
        denoiser = Denoiser(method=method)
        try:
            denoised_prices = denoiser.denoise(prices)
        except Exception as e:
            print(f"  ❌ 去噪失败: {e}")
            continue
        
        denoise_time = time.time() - method_start
        
        # 计算原始指标
        rsi_orig = calculate_rsi(prices)
        macd_orig = calculate_macd(prices)
        ma_orig = calculate_ma(prices)
        bb_orig = calculate_bollinger(prices)
        
        # 计算去噪后指标
        rsi_denoised = calculate_rsi(denoised_prices)
        macd_denoised = calculate_macd(denoised_prices)
        ma_denoised = calculate_ma(denoised_prices)
        bb_denoised = calculate_bollinger(denoised_prices)
        
        # ============ 稳定性对比 ============
        
        # 1. RSI 稳定性
        rsi_vol_orig = calculate_volatility(rsi_orig)
        rsi_vol_den = calculate_volatility(rsi_denoised)
        rsi_improvement = (rsi_vol_orig - rsi_vol_den) / rsi_vol_orig * 100 if rsi_vol_orig > 0 else 0
        
        # 2. MACD 稳定性
        macd_vol_orig = calculate_volatility(macd_orig['macd'])
        macd_vol_den = calculate_volatility(macd_denoised['macd'])
        macd_improvement = (macd_vol_orig - macd_vol_den) / macd_vol_orig * 100 if macd_vol_orig > 0 else 0
        
        # 3. MACD 信号反转次数
        macd_reversals_orig = calculate_signal_reversals(macd_orig['histogram'])
        macd_reversals_den = calculate_signal_reversals(macd_denoised['histogram'])
        reversal_reduction = (macd_reversals_orig - macd_reversals_den) / macd_reversals_orig * 100 if macd_reversals_orig > 0 else 0
        
        # 4. 均线交叉次数
        ma_cross_orig = calculate_ma_crossovers(ma_orig['MA5'], ma_orig['MA20'])
        ma_cross_den = calculate_ma_crossovers(ma_denoised['MA5'], ma_denoised['MA20'])
        cross_reduction = (ma_cross_orig - ma_cross_den) / ma_cross_orig * 100 if ma_cross_orig > 0 else 0
        
        # 5. 布林带宽稳定性
        bb_width_orig = bb_orig['upper'] - bb_orig['lower']
        bb_width_den = bb_denoised['upper'] - bb_denoised['lower']
        bb_vol_orig = calculate_volatility(bb_width_orig)
        bb_vol_den = calculate_volatility(bb_width_den)
        bb_improvement = (bb_vol_orig - bb_vol_den) / bb_vol_orig * 100 if bb_vol_orig > 0 else 0
        
        # 6. 价格保真度
        price_diff = np.abs(prices - denoised_prices)
        price_rmse = np.sqrt(np.mean(price_diff**2))
        price_mape = np.mean(price_diff / prices) * 100
        
        # 保存结果
        results['methods'][method] = {
            'denoise_time_ms': denoise_time * 1000,
            'rsi': {
                'volatility_original': rsi_vol_orig,
                'volatility_denoised': rsi_vol_den,
                'improvement_pct': rsi_improvement
            },
            'macd': {
                'volatility_original': macd_vol_orig,
                'volatility_denoised': macd_vol_den,
                'improvement_pct': macd_improvement,
                'signal_reversals_original': macd_reversals_orig,
                'signal_reversals_denoised': macd_reversals_den,
                'reversal_reduction_pct': reversal_reduction
            },
            'moving_averages': {
                'crossovers_original': ma_cross_orig,
                'crossovers_denoised': ma_cross_den,
                'reduction_pct': cross_reduction
            },
            'bollinger': {
                'width_volatility_original': bb_vol_orig,
                'width_volatility_denoised': bb_vol_den,
                'improvement_pct': bb_improvement
            },
            'fidelity': {
                'rmse': price_rmse,
                'mape_pct': price_mape
            }
        }
        
        # 打印摘要
        print(f"  ⏱️  处理时间: {denoise_time*1000:.2f} ms")
        print(f"  📈 RSI 波动率: {rsi_vol_orig:.2f} → {rsi_vol_den:.2f} ({rsi_improvement:+.1f}%)")
        print(f"  📊 MACD 波动率: {macd_vol_orig:.4f} → {macd_vol_den:.4f} ({macd_improvement:+.1f}%)")
        print(f"  🔄 MACD 信号反转: {macd_reversals_orig} → {macd_reversals_den} ({reversal_reduction:+.1f}%)")
        print(f"  ➡️  MA5/MA20 交叉: {ma_cross_orig} → {ma_cross_den} ({cross_reduction:+.1f}%)")
        print(f"  📏 价格保真度 (MAPE): {price_mape:.3f}%")
    
    return results

def test_trend_detection(df: pd.DataFrame) -> dict:
    """测试趋势检测功能"""
    print(f"\n{'='*60}")
    print("📈 趋势检测测试")
    print(f"{'='*60}")
    
    methods = ['wavelet', 'kalman']
    trend_results = {}
    
    for method in methods:
        start = time.time()
        trend_info = detect_trend_clean(df, method=method)
        elapsed = time.time() - start
        
        trend_results[method] = {
            'trend': trend_info['trend'],
            'slope': trend_info['slope'],
            'stability': trend_info['stability'],
            'time_ms': elapsed * 1000
        }
        
        print(f"\n🔹 {method.upper()}:")
        print(f"  趋势: {trend_info['trend']}")
        print(f"  斜率: {trend_info['slope']:.6f}")
        print(f"  稳定性: {trend_info['stability']:.4f}")
        print(f"  时间: {elapsed*1000:.2f} ms")
    
    return trend_results

def generate_summary_report(all_results: list) -> str:
    """生成汇总报告"""
    report = []
    report.append("\n" + "="*70)
    report.append("📊 去噪效果汇总报告")
    report.append("="*70)
    
    for method in ['wavelet', 'kalman', 'emd']:
        report.append(f"\n🔹 {method.upper()} 方法汇总:")
        report.append("-" * 50)
        
        # 收集该方法的所有数据
        method_data = []
        for r in all_results:
            if method in r['methods']:
                method_data.append(r['methods'][method])
        
        if not method_data:
            report.append("  无有效数据")
            continue
        
        # 计算平均值
        avg_rsi_imp = np.mean([m['rsi']['improvement_pct'] for m in method_data])
        avg_macd_imp = np.mean([m['macd']['improvement_pct'] for m in method_data])
        avg_reversal_red = np.mean([m['macd']['reversal_reduction_pct'] for m in method_data])
        avg_cross_red = np.mean([m['moving_averages']['reduction_pct'] for m in method_data])
        avg_mape = np.mean([m['fidelity']['mape_pct'] for m in method_data])
        avg_time = np.mean([m['denoise_time_ms'] for m in method_data])
        
        report.append(f"  RSI 波动率改善: {avg_rsi_imp:+.1f}%")
        report.append(f"  MACD 波动率改善: {avg_macd_imp:+.1f}%")
        report.append(f"  信号反转减少: {avg_reversal_red:+.1f}%")
        report.append(f"  MA交叉减少: {avg_cross_red:+.1f}%")
        report.append(f"  价格偏差(MAPE): {avg_mape:.3f}%")
        report.append(f"  平均处理时间: {avg_time:.2f} ms")
    
    report.append("\n" + "="*70)
    report.append("📝 结论与建议")
    report.append("="*70)
    
    # 综合评估
    best_method = None
    best_score = -999
    
    for method in ['wavelet', 'kalman', 'emd']:
        method_data = [r['methods'][method] for r in all_results if method in r['methods']]
        if not method_data:
            continue
        
        # 综合评分：波动改善 - 价格偏差
        avg_rsi = np.mean([m['rsi']['improvement_pct'] for m in method_data])
        avg_macd = np.mean([m['macd']['improvement_pct'] for m in method_data])
        avg_mape = np.mean([m['fidelity']['mape_pct'] for m in method_data])
        
        score = (avg_rsi + avg_macd) / 2 - avg_mape  # 改善越大越好，偏差越小越好
        
        if score > best_score:
            best_score = score
            best_method = method
    
    if best_method:
        report.append(f"\n✅ 推荐方法: {best_method.upper()}")
        report.append(f"   综合评分: {best_score:.2f}")
    
    report.append("\n📌 关键发现:")
    report.append("  1. 去噪能显著降低技术指标的波动性")
    report.append("  2. 信号反转次数减少意味着更少的假信号")
    report.append("  3. 均线交叉减少可避免频繁交易")
    report.append("  4. 但过度去噪会丢失重要价格信息")
    report.append("\n⚠️  建议:")
    report.append("  - 短线交易: 使用较轻的去噪参数")
    report.append("  - 趋势跟踪: 可使用较强去噪")
    report.append("  - 结合原始指标验证，避免过度依赖")
    
    return "\n".join(report)

# ============ 主程序 ============
if __name__ == "__main__":
    # 加载股票数据
    cache_dir = "/home/kyj/.openclaw/workspace/data_cache"
    
    # 测试股票列表（使用存在的缓存文件）
    test_stocks = ['AAPL', 'NVDA', 'GOOGL', 'AMZN']
    
    all_results = []
    
    for symbol in test_stocks:
        # 尝试不同的文件名格式
        cache_file = None
        for suffix in ['', '_av']:
            test_path = f"{cache_dir}/{symbol}{suffix}.parquet"
            if os.path.exists(test_path):
                cache_file = test_path
                break
        
        if cache_file is None:
            print(f"⚠️  {symbol} 缓存文件不存在，跳过")
            continue
        
        try:
            df = pd.read_parquet(cache_file)
            if len(df) < 100:
                print(f"⚠️  {symbol} 数据不足 ({len(df)} days)")
                continue
            
            # 运行测试
            result = test_denoiser_impact(symbol, df.tail(200))  # 使用最近200天数据
            all_results.append(result)
            
            # 测试趋势检测
            trend_result = test_trend_detection(df.tail(100))
            result['trend_detection'] = trend_result
            
        except FileNotFoundError:
            print(f"⚠️  {symbol} 缓存文件不存在")
        except Exception as e:
            print(f"❌ {symbol} 测试失败: {e}")
    
    # 生成汇总报告
    if all_results:
        report = generate_summary_report(all_results)
        print(report)
        
        # 保存报告
        report_path = "/home/kyj/.openclaw/workspace/denoiser/test_results.md"
        with open(report_path, 'w') as f:
            f.write(f"# Denoiser + DSS 集成测试报告\n\n")
            f.write(f"测试时间: {pd.Timestamp.now()}\n\n")
            f.write("```\n" + report + "\n```\n")
        print(f"\n📄 报告已保存至: {report_path}")
    
    print("\n✅ 测试完成")