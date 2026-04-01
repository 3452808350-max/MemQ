#!/usr/bin/env python3
"""
DSS Daily Stock Pick - 快速版 (20只股票)
用于每日邮件推荐
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_modules.data_loader import get_stock_data
from dss_modules.features import add_technical_indicators
from dss_modules.models import StockModel
import numpy as np
from datetime import datetime

# 精选20只核心股票 - 平衡各行业
CORE_STOCKS = {
    # 银行
    'sh.601398': ('工商银行', '银行'),
    'sh.600036': ('招商银行', '银行'),
    # 保险
    'sh.601318': ('中国平安', '保险'),
    # 能源
    'sh.601857': ('中国石油', '能源'),
    'sh.600028': ('中国石化', '能源'),
    # 白酒
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    # 地产
    'sh.000002': ('万科A', '地产'),
    'sh.600048': ('保利地产', '地产'),
    # 制造业
    'sh.600104': ('上汽集团', '汽车'),
    'sh.600900': ('长江电力', '电力'),
    'sh.600276': ('恒瑞医药', '医药'),
    'sh.601668': ('中国建筑', '基建'),
    # 高科技
    'sh.603986': ('兆易创新', '芯片'),
    'sh.600570': ('恒生电子', '软件'),
    'sz.002594': ('比亚迪', '新能源车'),
    'sz.300750': ('宁德时代', '电池'),
    'sh.601012': ('隆基绿能', '光伏'),
    'sz.002415': ('海康威视', '安防'),
}

def analyze_stock(symbol):
    """分析单只股票"""
    df = get_stock_data(symbol, 250, 'baostock')
    if df is None or len(df) < 100:
        return None
    
    df = add_technical_indicators(df)
    df = df.dropna()
    if len(df) < 30:
        return None
    
    latest = df.iloc[-1]
    
    # 技术信号评分
    score = 0
    
    # RSI (超卖+20, 超买-20)
    rsi = latest.get('RSI', 50)
    if rsi < 30:
        score += 20
    elif rsi > 70:
        score -= 20
    elif rsi < 40:
        score += 10
    elif rsi > 60:
        score -= 10
    
    # MACD (金叉+15, 死叉-15)
    macd = latest.get('MACD', 0)
    if macd > 0:
        score += 15
    else:
        score -= 15
    
    # 均线 (多头+10, 空头-10)
    ma5 = latest.get('MA5', 0)
    ma20 = latest.get('MA20', 0)
    if ma5 > ma20:
        score += 10
    else:
        score -= 10
    
    # 成交量 (高于均量+5)
    vol_ma = latest.get('volume_MA20', 0)
    volume = latest.get('Volume', 0)
    if volume > vol_ma:
        score += 5
    
    # 布林带位置
    bb_pos = latest.get('BB_position', 0.5)
    if bb_pos < 0.2:
        score += 10
    elif bb_pos > 0.8:
        score -= 10
    
    # 预测
    df['label'] = (df['Close'].shift(-5) / df['Close'] > 1.02).astype(int)
    df = df.dropna()
    
    pred_score = 0
    if len(df) > 30:
        feature_cols = [c for c in df.columns if c not in ['Open','High','Low','Close','Volume','label']]
        X = df[feature_cols].values
        y = df['label'].values
        valid = ~np.isnan(X).any(axis=1)
        X, y = X[valid], y[valid]
        if len(X) > 25:
            split = len(X) - 10
            model = StockModel('lgbm')
            model.fit(X[:split], y[:split])
            proba = model.predict_proba(X[split:])
            if proba[0] > 0.5:
                pred_score = int((proba[0] - 0.5) * 200)
            else:
                pred_score = -int((0.5 - proba[0]) * 200)
    
    total_score = score + pred_score
    
    return {
        'close': latest['Close'],
        'score': total_score,
        'tech_score': score,
        'pred_score': pred_score,
        'rsi': rsi,
        'macd': '金叉' if macd > 0 else '死叉',
    }

def pick_best():
    """选出最佳股票"""
    print("正在分析20只核心股票...")
    
    results = []
    for code, (name, industry) in CORE_STOCKS.items():
        print(f"  分析 {name} ({code})...")
        info = analyze_stock(code)
        if info:
            info['code'] = code
            info['name'] = name
            info['industry'] = industry
            results.append(info)
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results

def generate_email_content():
    """生成邮件内容"""
    today = datetime.now().strftime("%Y年%m月%d日")
    results = pick_best()
    
    if not results:
        return "无法获取足够数据"
    
    best = results[0]
    
    # Top 5
    top5 = results[:5]
    
    # 传统 vs 高科技
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

def send_daily_email():
    """生成并发送每日邮件"""
    from email_system import KaguyaEmailReporter
    
    content = generate_email_content()
    today = datetime.now().strftime("%Y-%m-%d")
    
    reporter = KaguyaEmailReporter()
    subject = f"📊 DSS每日股票推荐 - {today}"
    
    success = reporter.send_report(subject, content)
    return success

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "send":
        # 发送邮件
        if send_daily_email():
            print("✅ 邮件发送成功")
        else:
            print("❌ 邮件发送失败")
    else:
        # 仅打印内容
        print(generate_email_content())
