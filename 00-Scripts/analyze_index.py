"""
深证成指 (399001.SZ) 技术分析与情绪分析
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dss_modules.data_loader import get_stock_data, _ensure_baostock_login
from dss_modules.features import add_technical_indicators
import baostock as bs

# ============ 去噪模块 ============
class KalmanDenoiser:
    """Kalman滤波去噪"""
    def __init__(self, Q=0.005, R=0.5):
        self.Q = Q  # 过程噪声
        self.R = R  # 测量噪声
    
    def denoise(self, prices):
        n = len(prices)
        x = np.zeros(n)  # 状态估计
        P = np.zeros(n)  # 误差协方差
        x[0] = prices[0]
        P[0] = 1.0
        
        for i in range(1, n):
            # 预测
            x[i] = x[i-1]
            P[i] = P[i-1] + self.Q
            
            # 更新
            K = P[i] / (P[i] + self.R)
            x[i] = x[i] + K * (prices[i] - x[i])
            P[i] = (1 - K) * P[i]
        
        return x

# ============ 获取指数数据 ============
def get_index_data(code: str, days: int = 500):
    """获取指数数据"""
    if not _ensure_baostock_login():
        return None
    
    try:
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume",
            start_date=(datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d'),
            frequency="d"
        )
        
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list:
            return None
        
        df = pd.DataFrame(data_list, columns=['date','open','high','low','close','volume'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.columns = [c.capitalize() for c in df.columns]
        
        return df.dropna().tail(days)
    except Exception as e:
        print(f"获取指数数据失败: {e}")
        return None

# ============ 技术分析 ============
def technical_analysis(df, denoiser=None):
    """技术分析"""
    close = df['Close'].values
    
    # 去噪处理
    if denoiser:
        close_denoised = denoiser.denoise(close)
        df['Close_denoised'] = close_denoised
    
    # 添加技术指标
    df = add_technical_indicators(df)
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    # 技术评分
    score = 0
    signals = []
    
    # 1. RSI分析
    rsi = latest.get('RSI', 50)
    if pd.notna(rsi):
        if rsi < 30:
            score += 20
            signals.append(f"RSI超卖({rsi:.1f}) → 看涨")
        elif rsi < 40:
            score += 10
            signals.append(f"RSI偏低({rsi:.1f}) → 偏多")
        elif rsi > 70:
            score -= 20
            signals.append(f"RSI超买({rsi:.1f}) → 看跌")
        elif rsi > 60:
            score -= 10
            signals.append(f"RSI偏高({rsi:.1f}) → 偏空")
        else:
            signals.append(f"RSI中性({rsi:.1f})")
    
    # 2. MACD分析
    macd = latest.get('MACD', 0)
    macd_signal = latest.get('MACD_signal', 0)
    macd_prev = prev.get('MACD', 0)
    
    if pd.notna(macd) and pd.notna(macd_signal):
        if macd > macd_signal:
            score += 10
            signals.append(f"MACD金叉({macd:.2f} > {macd_signal:.2f}) → 看涨")
        else:
            score -= 10
            signals.append(f"MACD死叉({macd:.2f} < {macd_signal:.2f}) → 看跌")
        
        # MACD柱变化
        hist = macd - macd_signal
        hist_prev = macd_prev - prev.get('MACD_signal', 0)
        if hist > hist_prev:
            score += 5
            signals.append(f"MACD柱扩大({hist:.2f}) → 动能增强")
        else:
            score -= 5
            signals.append(f"MACD柱缩小({hist:.2f}) → 动能减弱")
    
    # 3. 均线分析
    ma5 = latest.get('MA5', 0)
    ma10 = latest.get('MA10', 0)
    ma20 = latest.get('MA20', 0)
    ma60 = latest.get('MA60', 0)
    
    if pd.notna(ma5) and pd.notna(ma10) and pd.notna(ma20):
        if ma5 > ma10 > ma20:
            score += 15
            signals.append(f"均线多头排列(MA5>MA10>MA20) → 看涨")
        elif ma5 < ma10 < ma20:
            score -= 15
            signals.append(f"均线空头排列(MA5<MA10<MA20) → 看跌")
        else:
            # 短期趋势
            if ma5 > ma10:
                score += 5
                signals.append(f"短期均线金叉(MA5>MA10) → 偏多")
            else:
                score -= 5
                signals.append(f"短期均线死叉(MA5<MA10) → 偏空")
        
        # 价格与MA20关系
        close_val = latest['Close']
        if close_val > ma20:
            score += 5
            signals.append(f"价格站上MA20({ma20:.2f}) → 支撑有效")
        else:
            score -= 5
            signals.append(f"价格跌破MA20({ma20:.2f}) → 支撑失守")
        
        # MA60趋势
        if pd.notna(ma60) and close_val > ma60:
            score += 5
            signals.append(f"价格在MA60之上({ma60:.2f}) → 中期趋势向上")
    
    # 4. 布林带分析
    bb_upper = latest.get('BB_upper', 0)
    bb_lower = latest.get('BB_lower', 0)
    bb_pos = latest.get('BB_position', 0.5)
    
    if pd.notna(bb_upper) and pd.notna(bb_lower):
        if bb_pos < 0.2:
            score += 10
            signals.append(f"布林带下轨附近(位置:{bb_pos:.2f}) → 超卖")
        elif bb_pos > 0.8:
            score -= 10
            signals.append(f"布林带上轨附近(位置:{bb_pos:.2f}) → 超买")
        else:
            signals.append(f"布林带中轨附近(位置:{bb_pos:.2f})")
    
    # 5. 成交量分析
    volume = latest.get('Volume', 0)
    vol_ma20 = latest.get('volume_MA20', 0)
    
    if pd.notna(volume) and pd.notna(vol_ma20) and vol_ma20 > 0:
        vol_ratio = volume / vol_ma20
        if vol_ratio > 2.0:
            score += 10
            signals.append(f"成交量放大{vol_ratio:.1f}倍 → 市场活跃")
        elif vol_ratio > 1.5:
            score += 5
            signals.append(f"成交量放量{vol_ratio:.1f}倍")
        elif vol_ratio < 0.5:
            score -= 5
            signals.append(f"成交量萎缩{vol_ratio:.1f}倍 → 市场观望")
    
    # 6. 趋势动量
    mom5 = latest.get('momentum_5', 0)
    mom10 = latest.get('momentum_10', 0)
    mom20 = latest.get('momentum_20', 0)
    
    if pd.notna(mom5) and pd.notna(mom10) and pd.notna(mom20):
        if mom5 > 0 and mom10 > 0 and mom20 > 0:
            score += 10
            signals.append(f"短期动量全部为正 → 上涨趋势确立")
        elif mom5 < 0 and mom10 < 0 and mom20 < 0:
            score -= 10
            signals.append(f"短期动量全部为负 → 下跌趋势确立")
        else:
            if mom5 > 0:
                score += 3
                signals.append(f"5日动量向上({mom5*100:.2f}%)")
            else:
                score -= 3
                signals.append(f"5日动量向下({mom5*100:.2f}%)")
    
    # 7. KDJ分析
    stoch_k = latest.get('stoch_k', 50)
    stoch_d = latest.get('stoch_d', 50)
    
    if pd.notna(stoch_k) and pd.notna(stoch_d):
        if stoch_k < 20 and stoch_d < 20:
            score += 15
            signals.append(f"KDJ超卖区(K:{stoch_k:.1f}, D:{stoch_d:.1f}) → 反弹信号")
        elif stoch_k > 80 and stoch_d > 80:
            score -= 15
            signals.append(f"KDJ超买区(K:{stoch_k:.1f}, D:{stoch_d:.1f}) → 回调风险")
        elif stoch_k > stoch_d:
            score += 5
            signals.append(f"KDJ金叉(K:{stoch_k:.1f} > D:{stoch_d:.1f})")
        else:
            score -= 5
            signals.append(f"KDJ死叉(K:{stoch_k:.1f} < D:{stoch_d:.1f})")
    
    # 8. 波动率分析
    vol_5 = latest.get('volatility_5', 0)
    vol_20 = latest.get('volatility_20', 0)
    
    if pd.notna(vol_5) and pd.notna(vol_20):
        if vol_5 > vol_20 * 1.5:
            score -= 5
            signals.append(f"短期波动率飙升 → 市场不稳定")
        elif vol_5 < vol_20 * 0.5:
            score += 5
            signals.append(f"波动率收敛 → 可能即将突破")
    
    return {
        'score': score,
        'signals': signals,
        'indicators': {
            'RSI': rsi,
            'MACD': macd,
            'MACD_signal': macd_signal,
            'MA5': ma5,
            'MA10': ma10,
            'MA20': ma20,
            'MA60': ma60,
            'BB_position': bb_pos,
            'volume_ratio': volume / vol_ma20 if vol_ma20 > 0 else 1,
            'momentum_5': mom5,
            'momentum_10': mom10,
            'momentum_20': mom20,
            'stoch_k': stoch_k,
            'stoch_d': stoch_d,
        },
        'latest': latest
    }

# ============ 趋势判断 ============
def determine_trend(df):
    """判断当前趋势"""
    close = df['Close']
    
    # 20日均线斜率
    ma20 = close.rolling(20).mean()
    slope = (ma20.iloc[-1] - ma20.iloc[-5]) / ma20.iloc[-5] * 100
    
    # 高低点分析
    recent_high = close.iloc[-20:].max()
    recent_low = close.iloc[-20:].min()
    current = close.iloc[-1]
    
    # 高点低点序列
    highs = close.rolling(5).max().iloc[-20:]
    lows = close.rolling(5).min().iloc[-20:]
    
    higher_highs = (highs.diff() > 0).sum()
    lower_lows = (lows.diff() < 0).sum()
    
    if slope > 0.5 and higher_highs > lower_lows:
        return "上升趋势", slope
    elif slope < -0.5 and lower_lows > higher_highs:
        return "下降趋势", slope
    else:
        return "震荡整理", slope

# ============ 综合预测 ============
def predict_next_week(df, tech_result):
    """预测未来一周走势"""
    score = tech_result['score']
    indicators = tech_result['indicators']
    
    # 置信度计算
    confidence = min(95, max(5, 50 + abs(score)))
    
    # 趋势判断
    trend, slope = determine_trend(df)
    
    # 预测方向
    if score >= 30:
        prediction = "上涨"
        confidence = min(95, confidence + 10)
    elif score >= 10:
        prediction = "偏涨"
    elif score <= -30:
        prediction = "下跌"
        confidence = min(95, confidence + 10)
    elif score <= -10:
        prediction = "偏跌"
    else:
        prediction = "横盘震荡"
        confidence = max(10, confidence - 20)
    
    # 风险因素
    risks = []
    
    if indicators.get('RSI', 50) > 70:
        risks.append("RSI超买，短期回调风险较高")
    if indicators.get('RSI', 50) < 30:
        risks.append("RSI超卖，但可能存在反弹机会")
    if indicators.get('volume_ratio', 1) < 0.6:
        risks.append("成交量萎缩，市场观望情绪浓厚")
    if indicators.get('momentum_5', 0) < -0.03:
        risks.append("短期动量转弱，注意风险")
    if slope > 2:
        risks.append("短期涨幅较大，注意获利回吐")
    
    return {
        'prediction': prediction,
        'confidence': confidence,
        'trend': trend,
        'trend_slope': slope,
        'risks': risks
    }

# ============ 主程序 ============
if __name__ == "__main__":
    print("="*60)
    print("深证成指 (399001.SZ) 技术分析报告")
    print("="*60)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取数据
    print("📊 正在获取指数数据...")
    df = get_index_data("sz.399001", days=500)
    
    if df is None:
        print("❌ 获取数据失败")
        sys.exit(1)
    
    print(f"✅ 获取到 {len(df)} 个交易日数据")
    print(f"   日期范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
    print()
    
    # 最新数据
    latest = df.iloc[-1]
    print(f"📈 最新行情:")
    print(f"   收盘价: {latest['Close']:.2f}")
    print(f"   最高:   {latest['High']:.2f}")
    print(f"   最低:   {latest['Low']:.2f}")
    print(f"   成交量: {latest['Volume']/1e8:.2f}亿")
    print()
    
    # 技术分析
    print("-"*60)
    print("📋 技术面分析")
    print("-"*60)
    
    denoiser = KalmanDenoiser(Q=0.005, R=0.5)
    tech_result = technical_analysis(df.copy(), denoiser)
    
    print(f"\n技术评分: {tech_result['score']:+d}")
    print("\n信号明细:")
    for signal in tech_result['signals']:
        print(f"   • {signal}")
    
    # 预测
    print("\n" + "-"*60)
    print("🔮 未来一周走势预测")
    print("-"*60)
    
    prediction = predict_next_week(df, tech_result)
    
    print(f"\n当前趋势: {prediction['trend']} (斜率: {prediction['trend_slope']:.2f}%)")
    print(f"预测方向: {prediction['prediction']}")
    print(f"置信度:   {prediction['confidence']:.0f}%")
    
    if prediction['risks']:
        print("\n⚠️  风险提示:")
        for risk in prediction['risks']:
            print(f"   • {risk}")
    
    # 关键位置
    print("\n" + "-"*60)
    print("📍 关键位置")
    print("-"*60)
    
    indicators = tech_result['indicators']
    latest_price = latest['Close']
    
    print(f"\n当前价位: {latest_price:.2f}")
    if pd.notna(indicators.get('MA20')):
        print(f"MA20支撑/压力: {indicators['MA20']:.2f} (距离: {((indicators['MA20']/latest_price-1)*100):+.2f}%)")
    if pd.notna(indicators.get('MA60')):
        print(f"MA60支撑/压力: {indicators['MA60']:.2f} (距离: {((indicators['MA60']/latest_price-1)*100):+.2f}%)")
    if pd.notna(indicators.get('BB_upper')):
        print(f"布林上轨: {indicators['BB_upper']:.2f} (距离: {((indicators['BB_upper']/latest_price-1)*100):+.2f}%)")
    if pd.notna(indicators.get('BB_lower')):
        print(f"布林下轨: {indicators['BB_lower']:.2f} (距离: {((indicators['BB_lower']/latest_price-1)*100):+.2f}%)")
    
    # 近期高低点
    recent_high = df['Close'].iloc[-20:].max()
    recent_low = df['Close'].iloc[-20:].min()
    print(f"\n近20日高点: {recent_high:.2f}")
    print(f"近20日低点: {recent_low:.2f}")
    
    print("\n" + "="*60)
    print("分析完成")
    print("="*60)