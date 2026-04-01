"""
DSS Swarm - 收盘自我总结 (轻量版)
只分析少量股票，快速生成总结
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from datetime import datetime
from dss_modules.data_loader import get_stock_data
from dss_modules.features import add_technical_indicators

# 精选 10 只股票快速分析
QUICK_STOCKS = {
    'sh.600519': '贵州茅台',
    'sh.601318': '中国平安',
    'sz.000858': '五粮液',
    'sz.000002': '万科 A',
    'sh.601857': '中国石油',
    'sz.002594': '比亚迪',
    'sz.300750': '宁德时代',
    'sh.600036': '招商银行',
    'sh.601398': '工商银行',
    'sz.002415': '海康威视',
}

def analyze_quick(code, name):
    """快速分析单只股票"""
    df = get_stock_data(code, 60, 'baostock')
    if df is None or len(df) < 30:
        return None
    
    df = add_technical_indicators(df)
    # 只删除关键字段为空的行
    df = df.dropna(subset=['Close', 'RSI', 'MACD'])
    if len(df) < 10:
        return None
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    # 计算涨跌
    change_pct = (latest['Close'] / prev['Close'] - 1) * 100 if prev['Close'] > 0 else 0
    
    # 简单信号
    rsi = latest.get('RSI', 50)
    macd = latest.get('MACD', 0)
    
    signal = "中性"
    if rsi < 30 and macd > 0:
        signal = "看涨"
    elif rsi > 70 and macd < 0:
        signal = "看跌"
    elif macd > 0:
        signal = "偏多"
    elif macd < 0:
        signal = "偏空"
    
    return {
        'name': name,
        'code': code,
        'close': latest['Close'],
        'change': change_pct,
        'rsi': rsi,
        'macd': macd,
        'signal': signal,
    }

def generate_summary():
    """生成收盘总结"""
    today = datetime.now().strftime("%Y年%m月%d日")
    
    results = []
    for code, name in QUICK_STOCKS.items():
        info = analyze_quick(code, name)
        if info:
            results.append(info)
    
    if not results:
        return "⚠️ 无法获取市场数据，请稍后重试"
    
    # 排序
    results.sort(key=lambda x: x['change'], reverse=True)
    
    summary = f"""
══════════════════════════════════════════════════════════
           📊 DSS 每日收盘总结
           {today}
══════════════════════════════════════════════════════════

🎯 市场概览 (精选 10 只股票)

"""
    
    # 领涨
    summary += "📈 领涨股票:\n"
    for r in results[:3]:
        summary += f"   • {r['name']:10s} {r['change']:+.2f}%  信号：{r['signal']}\n"
    
    # 领跌
    summary += "\n📉 领跌股票:\n"
    for r in results[-3:][::-1]:
        summary += f"   • {r['name']:10s} {r['change']:+.2f}%  信号：{r['signal']}\n"
    
    # 统计
    up_count = sum(1 for r in results if r['change'] > 0)
    down_count = len(results) - up_count
    
    summary += f"""
──────────────────────────────────────────────────────────
📊 市场情绪

   上涨：{up_count}/{len(results)}  ({up_count/len(results)*100:.0f}%)
   下跌：{down_count}/{len(results)}  ({down_count/len(results)*100:.0f}%)
   
   整体情绪：{'偏多 🟢' if up_count > down_count else '偏空 🔴' if down_count > up_count else '中性 ⚪'}

──────────────────────────────────────────────────────────
💡 今日观察

"""
    
    # 根据数据生成观察
    avg_change = sum(r['change'] for r in results) / len(results)
    if avg_change > 1:
        summary += "   • 市场整体表现强劲，多数股票上涨\n"
    elif avg_change < -1:
        summary += "   • 市场承压，注意风险控制\n"
    else:
        summary += "   • 市场震荡整理，方向不明\n"
    
    # RSI 观察
    high_rsi = [r for r in results if r['rsi'] > 70]
    low_rsi = [r for r in results if r['rsi'] < 30]
    if high_rsi:
        summary += f"   • 注意：{', '.join(r['name'] for r in high_rsi)} RSI 超买\n"
    if low_rsi:
        summary += f"   • 关注：{', '.join(r['name'] for r in low_rsi)} RSI 超卖，或有反弹机会\n"
    
    summary += """
⚠️ 明日计划

   1. 继续跟踪持仓股票动态
   2. 关注市场整体趋势变化
   3. 根据信号调整仓位

══════════════════════════════════════════════════════════
⚕️ 免责声明：本总结仅供参考，不构成投资建议
"""
    
    return summary

if __name__ == "__main__":
    print(generate_summary())
