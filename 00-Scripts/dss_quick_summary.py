#!/usr/bin/env python3
"""快速收盘总结 - 使用缓存数据"""
import os
import sys
import pandas as pd
from datetime import datetime

CACHE_DIR = "/home/kyj/.openclaw/workspace/data_cache"

# 主要关注的股票
WATCHLIST = {
    'sh.600519': '贵州茅台',
    'sh.601318': '中国平安',
    'sz.000858': '五粮液',
    'sh.600036': '招商银行',
    'sh.601398': '工商银行',
    'sh.600276': '恒瑞医药',
    'sz.002594': '比亚迪',
    'sz.300750': '宁德时代',
    'sh.603986': '兆易创新',
    'sh.688981': '中芯国际',
}

def get_cached_data(symbol):
    """从缓存获取数据"""
    cache_file = f"{CACHE_DIR}/{symbol.replace('.', '_')}_av.parquet"
    if os.path.exists(cache_file):
        df = pd.read_parquet(cache_file)
        return df
    return None

def calculate_change(df):
    """计算涨跌幅"""
    if df is None or len(df) < 2:
        return None
    latest = df.iloc[-1]['Close']
    prev = df.iloc[-2]['Close']
    change = (latest / prev - 1) * 100
    return {'close': latest, 'change': change}

def generate_summary():
    """生成收盘总结"""
    today = datetime.now().strftime('%Y年%m月%d日')
    
    results = []
    for code, name in WATCHLIST.items():
        df = get_cached_data(code)
        data = calculate_change(df)
        if data:
            results.append({
                'code': code,
                'name': name,
                'close': data['close'],
                'change': data['change']
            })
    
    if not results:
        return "无法获取数据 - 缓存中无可用数据"
    
    # 按涨跌幅排序
    results.sort(key=lambda x: x['change'], reverse=True)
    
    up_count = sum(1 for r in results if r['change'] > 0)
    down_count = sum(1 for r in results if r['change'] < 0)
    
    # 生成报告
    summary = f"""
══════════════════════════════════════════════════════════
           📊 每日收盘总结
           DSS AI选股系统 - {today}
══════════════════════════════════════════════════════════

🎯 今日关注股票表现

"""
    
    for i, r in enumerate(results, 1):
        emoji = "📈" if r['change'] > 0 else "📉" if r['change'] < 0 else "➖"
        summary += f"   {emoji} {r['name']:10s} ({r['code']})  收盘价: ¥{r['close']:.2f}  涨跌: {r['change']:+.2f}%\n"
    
    summary += f"""
──────────────────────────────────────────────────────────
📈 统计

   上涨: {up_count}
   下跌: {down_count}
   平盘: {len(results) - up_count - down_count}
   
   最强: {results[0]['name']} ({results[0]['change']:+.2f}%)
   最弱: {results[-1]['name']} ({results[-1]['change']:+.2f}%)

──────────────────────────────────────────────────────────
💡 今日观察

   - 市场情绪: {'偏多' if up_count > down_count else '偏空' if down_count > up_count else '中性'}
   - 建议关注: {results[0]['name']} (表现最强)
   
──────────────────────────────────────────────────────────
⚠️ 数据说明

   数据来源: 本地缓存
   更新时间: 缓存文件最后修改时间
   
   注: 如需最新数据，请运行数据更新脚本

══════════════════════════════════════════════════════════
"""
    return summary

if __name__ == "__main__":
    print(generate_summary())
