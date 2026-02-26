#!/usr/bin/env python3
"""
DSS Daily Stock Pick - 优化版 (使用单一baostock会话)
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# 精选20只核心股票
CORE_STOCKS = {
    'sh.601398': ('工商银行', '银行'),
    'sh.600036': ('招商银行', '银行'),
    'sh.601318': ('中国平安', '保险'),
    'sh.601857': ('中国石油', '能源'),
    'sh.600028': ('中国石化', '能源'),
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    'sh.000002': ('万科A', '地产'),
    'sh.600048': ('保利地产', '地产'),
    'sh.600104': ('上汽集团', '汽车'),
    'sh.600900': ('长江电力', '电力'),
    'sh.600276': ('恒瑞医药', '医药'),
    'sh.601668': ('中国建筑', '基建'),
    'sh.603986': ('兆易创新', '芯片'),
    'sh.600570': ('恒生电子', '软件'),
    'sz.002594': ('比亚迪', '新能源车'),
    'sz.300750': ('宁德时代', '电池'),
    'sh.601012': ('隆基绿能', '光伏'),
    'sz.002415': ('海康威视', '安防'),
    'sh.601012': ('隆基绿能', '光伏'),
}

def add_indicators(df):
    """添加技术指标（包括自适应指标 - 简化版）"""
    prices = df['Close']
    
    # ===== 传统指标 =====
    # RSI (14天)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD (12,26,9)
    exp1 = df['Close'].ewm(span=12).mean()
    exp2 = df['Close'].ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # 均线
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA60'] = df['Close'].rolling(60).mean()
    
    # 成交量均线
    df['volume_MA20'] = df['Volume'].rolling(20).mean()
    
    # 布林带
    df['BB_middle'] = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    df['BB_upper'] = df['BB_middle'] + 2 * bb_std
    df['BB_lower'] = df['BB_middle'] - 2 * bb_std
    df['BB_position'] = (df['Close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
    
    # ===== 自适应指标 (简化版) =====
    # 检测市场状态
    recent_20 = prices.tail(20)
    price_range = recent_20.max() - recent_20.min()
    current_pos = (prices.iloc[-1] - recent_20.min()) / (price_range + 1e-10)
    
    if current_pos > 0.85 or current_pos < 0.15:
        df['Market_Regime'] = 'trending'
    else:
        df['Market_Regime'] = 'range'
    
    # 自适应RSI - 根据波动率调整周期
    volatility = df['Close'].pct_change().tail(20).std()
    if volatility > 0.03:
        rsi_period = 21
    elif volatility < 0.015:
        rsi_period = 10
    else:
        rsi_period = 14
    
    delta2 = df['Close'].diff()
    gain2 = (delta2.where(delta2 > 0, 0)).rolling(window=rsi_period).mean()
    loss2 = (-delta2.where(delta2 < 0, 0)).rolling(window=rsi_period).mean()
    rs2 = gain2 / (loss2 + 1e-10)
    df['RSI_adaptive'] = 100 - (100 / (1 + rs2))
    df['RSI_period'] = rsi_period
    
    # 快速MACD (5,13,7) - 用于震荡市场
    exp1_fast = prices.ewm(span=5).mean()
    exp2_fast = prices.ewm(span=13).mean()
    df['MACD_fast'] = exp1_fast - exp2_fast
    df['MACD_fast_signal'] = df['MACD_fast'].ewm(span=7).mean()
    
    # 成交量变化率
    df['Volume_change'] = df['Volume'].pct_change()
    
    # ATR (Average True Range)
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    df['ATR_pct'] = df['ATR'] / df['Close'] * 100
    
    return df
    
    # 均线
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    
    # 成交量均线
    df['volume_MA20'] = df['Volume'].rolling(20).mean()
    
    # 布林带位置
    df['BB_middle'] = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    df['BB_upper'] = df['BB_middle'] + 2 * bb_std
    df['BB_lower'] = df['BB_middle'] - 2 * bb_std
    df['BB_position'] = (df['Close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
    
    return df

def analyze_stock(code, name, industry):
    """分析单只股票"""
    try:
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume",
            start_date=(datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d'),
            frequency="d"
        )
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())
        
        if not data_list or len(data_list) < 100:
            return None
            
        df = pd.DataFrame(data_list, columns=['date','open','high','low','close','volume'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.columns = [c.capitalize() for c in df.columns]
        df = df.dropna()
        
        if len(df) < 100:
            return None
        
        df = add_indicators(df)
        df = df.dropna()
        
        if len(df) < 30:
            return None
        
        latest = df.iloc[-1]
        
        # 评分 (使用自适应指标增强版)
        score = 0
        
        # 检测市场状态
        market_regime = latest.get('Market_Regime', 'range')
        
        # ===== RSI评分 (权重: 20%) =====
        rsi = latest.get('RSI', 50)
        rsi_adaptive = latest.get('RSI_adaptive', rsi)
        # 使用自适应RSI的值（如果有效）
        if pd.notna(rsi_adaptive) and rsi_adaptive > 0:
            rsi = rsi_adaptive
        
        if rsi < 30:
            score += 15
        elif rsi > 70:
            score -= 15
        elif rsi < 40:
            score += 8
        elif rsi > 60:
            score -= 8
        
        # ===== 双MACD评分 (权重: 25%) =====
        macd = latest.get('MACD', 0)
        macd_hist = latest.get('MACD_hist', 0)
        macd_fast = latest.get('MACD_fast', 0)
        macd_fast_hist = latest.get('MACD_fast', 0) - latest.get('MACD_fast_signal', 0)
        
        # 趋势市场看标准MACD，震荡市场看快速MACD
        if market_regime == 'trending':
            macd_score = macd_hist
        else:
            macd_score = macd_fast_hist
        
        if macd_score > 0:
            score += int(min(20, macd_score * 5))
        else:
            score += int(max(-20, macd_score * 5))
        
        # ===== 均线评分 (权重: 15%) =====
        ma5 = latest.get('MA5', 0)
        ma20 = latest.get('MA20', 0)
        ma60 = latest.get('MA60', 0)
        
        # 多头排列加分
        if ma5 > ma20 > ma60:
            score += 15
        elif ma5 > ma20:
            score += 8
        elif ma5 < ma20 < ma60:
            score -= 15
        elif ma5 < ma20:
            score -= 8
        
        # ===== 成交量评分 (权重: 10%) =====
        vol_ma = latest.get('volume_MA20', 0)
        volume = latest.get('Volume', 0)
        vol_change = latest.get('Volume_change', 0)
        
        if volume > vol_ma * 1.3:  # 放量明显
            score += 10
        elif volume > vol_ma:
            score += 5
        elif volume < vol_ma * 0.7:  # 缩量
            score -= 5
        
        # ===== 布林带评分 (权重: 10%) =====
        bb_pos = latest.get('BB_position', 0.5)
        if bb_pos < 0.15:
            score += 10  # 严重超卖
        elif bb_pos < 0.25:
            score += 5   # 超卖
        elif bb_pos > 0.85:
            score -= 10  # 严重超买
        elif bb_pos > 0.75:
            score -= 5   # 超买
        
        # ===== ATR波动率评分 (权重: 10%) =====
        atr_pct = latest.get('ATR_pct', 0)
        if atr_pct > 3:  # 高波动
            score += 5   # 高波动有机会
        elif atr_pct < 1:  # 低波动
            score -= 5   # 低波动可能盘整
        
        # ===== 趋势预测 (权重: 10%) =====
        returns = df['Close'].pct_change().dropna()
        if len(returns) >= 20:
            recent_return = returns.tail(5).mean()
            pred_score = int(recent_return * 800)  # 调整权重
            score += pred_score
        else:
            pred_score = 0
        
        # ===== ML预测评分 (权重: 15%) =====
        try:
            from dss_ml_predict import get_ml_score
            ml_score, ml_info = get_ml_score(df)
            score += ml_score
            ml_pred_score = ml_score
        except Exception as e:
            ml_pred_score = 0
            ml_info = {'direction': 'neutral', 'confidence': 0.5}
        
        # LSTM 预测
        try:
            from dss_transformer_lstm import get_lstm_signal
            lstm_dir, lstm_conf, lstm_chg = get_lstm_signal(df['Close'], seq_length=20)
            lstm_score = int(lstm_conf * 20) if lstm_dir == 'bull' else (-int(lstm_conf * 20) if lstm_dir == 'bear' else 0)
            score += lstm_score
        except:
            lstm_score = 0
            lstm_dir = 'neutral'
        
        return {
            'code': code,
            'name': name,
            'industry': industry,
            'close': latest['Close'],
            'score': score,
            'tech_score': score - pred_score - ml_pred_score - lstm_score,
            'pred_score': pred_score,
            'ml_score': ml_pred_score,
            'lstm_score': lstm_score,
            'rsi': rsi,
            'macd': '金叉' if macd_hist > 0 else '死叉',
            'regime': market_regime,
            'atr_pct': round(atr_pct, 2),
            'ml_direction': ml_info['direction'],
            'lstm_direction': lstm_dir,
        }
    except Exception as e:
        print(f"  Error analyzing {code}: {e}")
        return None

def generate_report():
    """生成报告"""
    print("="*60)
    print("DSS 每日股票分析")
    print("="*60)
    
    # 登录baostock一次
    print("\n[1/3] 连接数据源...")
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Login failed: {lg.error_msg}")
        return None
    
    try:
        print("[2/3] 分析股票...")
        results = []
        for code, (name, industry) in CORE_STOCKS.items():
            print(f"  分析: {name} ({code})")
            info = analyze_stock(code, name, industry)
            if info:
                results.append(info)
                print(f"    ✓ 评分: {info['score']:+d}")
            else:
                print(f"    ✗ 数据不足")
        
        # 排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        print("[3/3] 生成报告...")
        return results
    finally:
        bs.logout()

def format_email_content(results):
    """格式化邮件内容"""
    if not results:
        return "无法获取足够数据"
    
    today = datetime.now().strftime("%Y年%m月%d日")
    best = results[0]
    top5 = results[:5]
    
    # 传统行业 vs 高科技
    trad_industries = ['银行','保险','能源','白酒','地产','基建','汽车','电力','医药']
    trad = [r for r in results if r['industry'] in trad_industries]
    hi_tech = [r for r in results if r['industry'] not in trad_industries]
    
    best_trad = trad[0] if trad else None
    best_hightech = hi_tech[0] if hi_tech else None
    
    content = f"""
══════════════════════════════════════════════════════════
           📊 每日投资建议报告
           DSS AI选股系统 - {today}
══════════════════════════════════════════════════════════

🏆 今日最佳推荐

   股票: {best['name']} ({best['code']})
   行业: {best['industry']}
   收盘价: ¥{best['close']:.2f}
   
   技术评分: {best['tech_score']:+d}
   预测评分: {best['pred_score']:+d}
   综合评分: {best['score']:+d}
   
   RSI: {best['rsi']:.1f}
   MACD: {best['macd']}

──────────────────────────────────────────────────────────
📈 Top 5 推荐

"""
    for i, r in enumerate(top5, 1):
        content += f"   {i}. {r['name']:10s} ({r['code']:8s})  评分: {r['score']:+3d}  行业: {r['industry']}\n"
    
    content += f"""
──────────────────────────────────────────────────────────
📊 行业对比

   传统行业最佳: {best_trad['name'] if best_trad else 'N/A'} (评分: {best_trad['score'] if best_trad else 0:+d})
   高科技最佳:   {best_hightech['name'] if best_hightech else 'N/A'} (评分: {best_hightech['score'] if best_hightech else 0:+d})

──────────────────────────────────────────────────────────
💡 投资建议

   基于DSS系统分析，推荐关注: {best['name']}
   
   理由:
   - 综合评分最高 ({best['score']:+d}分)
   - 技术面{'积极' if best['tech_score'] > 0 else '需要观察'}
   - AI预测{'看涨' if best['pred_score'] > 0 else '看跌'}

⚠️ 免责声明:
   本报告由AI系统自动生成，仅供参考，不构成投资建议。
   投资有风险，入市需谨慎。

══════════════════════════════════════════════════════════
"""
    return content

def send_email(content):
    """发送邮件"""
    from email_system import KaguyaEmailReporter
    
    today = datetime.now().strftime("%Y-%m-%d")
    reporter = KaguyaEmailReporter()
    subject = f"📊 DSS每日股票推荐 - {today}"
    
    return reporter.send_report(subject, content)

if __name__ == "__main__":
    import sys
    from dss_validator import save_prediction
    
    # 生成报告
    results = generate_report()
    
    if results:
        # 保存预测结果（用于3日后验证）
        pred_file = save_prediction(results)
        print(f"📁 预测已保存用于反向验证")
        
        content = format_email_content(results)
        print(content)
        
        # 如果带send参数，发送邮件
        if len(sys.argv) > 1 and sys.argv[1] == "send":
            print("\n" + "="*60)
            if send_email(content):
                print("✅ 邮件发送成功!")
            else:
                print("❌ 邮件发送失败")
    else:
        print("❌ 无法生成报告")
