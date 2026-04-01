"""
DSS Swarm - 收盘自我总结
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_stock_picker import pick_best, STOCKS
from datetime import datetime
from dss_modules.data_loader import get_stock_data

def generate_summary():
    """生成收盘总结"""
    results = pick_best()
    
    if not results:
        return "无法获取数据"
    
    # 当日预测vs实际
    today = datetime.now().strftime("%Y年%m月%d日")
    summary = f"""
══════════════════════════════════════════════════════════
           📊 每日收盘总结
           DSS AI选股系统 - {today}
══════════════════════════════════════════════════════════

🎯 今日推荐表现

"""
    
    # 获取收盘数据
    for r in results[:3]:
        code = r['code']
        df = get_stock_data(code, 2, 'baostock')
        if df is not None and len(df) >= 2:
            today_close = df.iloc[-1]['Close']
            yesterday_close = df.iloc[-2]['Close']
            change = (today_close / yesterday_close - 1) * 100
            r['today_change'] = change
    
    for i, r in enumerate(results[:5], 1):
        change = r.get('today_change', 'N/A')
        if isinstance(change, float):
            change_str = f"{change:+.2f}%"
        else:
            change_str = "N/A"
        
        pred = r.get('pred_score', 0)
        pred_str = "看涨" if pred > 0 else "看跌"
        
        summary += f"   {i}. {r['name']:10s} 今日涨跌: {change_str:8s}  预测: {pred_str}\n"
    
    # 统计
    up_count = sum(1 for r in results if r.get('today_change', 0) > 0)
    total = len([r for r in results if 'today_change' in r])
    
    summary += f"""
──────────────────────────────────────────────────────────
📈 统计

   推荐股票总数: {total}
   上涨: {up_count}
   下跌: {total - up_count}
   准确率: {up_count/total*100:.1f}% (如果预测上涨且实际上涨)

──────────────────────────────────────────────────────────
💡 今日学习

"""
    
    # 简单的学习点
    summary += "   - 技术分析信号需要结合市场整体趋势\n"
    summary += "   - 预测模型需要更多基本面数据改进\n"
    summary += "   - 建议关注成交量配合情况\n"
    
    summary += """
⚠️ 明日计划

   1. 分析今日预测准确率
   2. 调整选股模型参数
   3. 关注持仓股票动态

══════════════════════════════════════════════════════════
"""
    return summary

if __name__ == "__main__":
    print(generate_summary())
