#!/usr/bin/env python3
"""
DSS v5.0 - 集成新闻情绪分析 + 图表生成
新增功能：
1. 新闻情绪分析模块
2. 图表生成（Matplotlib 本地版）
3. 加密货币关联分析
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互式后端

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 负号显示

import os

# 创建输出目录
os.makedirs('/home/kyj/.openclaw/workspace/data/charts', exist_ok=True)
os.makedirs('/home/kyj/.openclaw/workspace/data/predictions', exist_ok=True)

# 导入新模块
from dss_modules.api_news import analyze_sentiment, get_market_sentiment_report
from dss_modules.api_crypto import get_crypto_price, calculate_crypto_sentiment

# 核心股票池
CORE_STOCKS = {
    'sh.601398': ('工商银行', '银行'),
    'sh.600036': ('招商银行', '银行'),
    'sh.601318': ('中国平安', '保险'),
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    'sz.002594': ('比亚迪', '新能源车'),
    'sz.300750': ('宁德时代', '电池'),
    'sh.601012': ('隆基绿能', '光伏'),
}

def add_technical_indicators(df):
    """添加技术指标"""
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12).mean()
    exp2 = df['close'].ewm(span=26).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
    
    # 均线
    df['MA5'] = df['close'].rolling(5).mean()
    df['MA20'] = df['close'].rolling(20).mean()
    
    return df

def calculate_stock_score(df):
    """计算股票综合评分（简化版）"""
    if len(df) < 30:
        return 0
    
    latest = df.iloc[-1]
    score = 0
    
    # RSI 评分
    rsi = latest.get('RSI', 50)
    if rsi < 30:
        score += 20
    elif rsi > 70:
        score -= 20
    
    # MACD 评分
    macd = latest.get('MACD', 0)
    if macd > 0:
        score += 15
    
    # 均线评分
    ma5 = latest.get('MA5', 0)
    ma20 = latest.get('MA20', 0)
    if ma5 > ma20:
        score += 10
    
    return int(score)

def generate_stock_chart(symbol, name, df, save_path):
    """使用 Matplotlib 生成本地图表"""
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={'height_ratios': [3, 1]})
    
    # 上图：股价和均线
    ax1 = axes[0]
    dates = pd.to_datetime(df['date'])
    
    # 计算涨跌颜色
    is_up = df['close'].iloc[-1] > df['close'].iloc[0]
    color = '#d62728' if is_up else '#1f77b4'  # 红涨蓝跌
    
    ax1.plot(dates, df['close'], label='收盘价', linewidth=2.5, color=color)
    ax1.plot(dates, df['MA5'], label='MA5', linewidth=1.5, color='#ff7f0e', alpha=0.8)
    ax1.plot(dates, df['MA20'], label='MA20', linewidth=1.5, color='#2ca02c', alpha=0.8)
    
    # 填充价格区域
    ax1.fill_between(dates, df['close'], alpha=0.1, color=color)
    
    ax1.set_title(f'{name} ({symbol}) - {df["close"].iloc[-1]:.2f}元  ({(df["close"].iloc[-1]/df["close"].iloc[0]-1)*100:+.1f}%)', 
                  fontsize=14, fontweight='bold', pad=15)
    ax1.set_ylabel('价格 (元)', fontsize=12)
    ax1.legend(loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # 下图：成交量
    ax2 = axes[1]
    vol_colors = ['#d62728' if df['close'].iloc[i] > df['close'].iloc[i-1] else '#1f77b4' 
                  for i in range(1, len(df))]
    vol_colors = ['gray'] + vol_colors  # 第一天灰色
    
    ax2.bar(dates, vol_colors[:len(dates)], color=vol_colors, alpha=0.6, label='成交量', width=1)
    ax2.set_ylabel('成交量', fontsize=12)
    ax2.set_xlabel('日期', fontsize=12)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return save_path


def generate_html_report(results, sentiment_report, save_path):
    """生成 HTML 报告"""
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>DSS 每日投资建议报告 - {today}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 15px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .sentiment {{ display: inline-block; padding: 8px 20px; border-radius: 20px; color: white; font-weight: bold; }}
        .sentiment.positive {{ background: #27ae60; }}
        .sentiment.negative {{ background: #e74c3c; }}
        .sentiment.neutral {{ background: #95a5a6; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #3498db; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .score-positive {{ color: #27ae60; font-weight: bold; }}
        .score-negative {{ color: #e74c3c; font-weight: bold; }}
        .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; margin: 30px 0; }}
        .chart-item {{ text-align: center; }}
        .chart-item img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 2px solid #eee; color: #7f8c8d; font-size: 14px; }}
        .disclaimer {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 DSS 每日投资建议报告</h1>
        <p><strong>报告时间：</strong>{today}</p>
        <p><strong>市场情绪：</strong><span class="sentiment {'positive' if sentiment_report['sentiment']['overall_score'] > 0 else 'negative' if sentiment_report['sentiment']['overall_score'] < 0 else 'neutral'}">
            {sentiment_report['sentiment']['overall_sentiment'].upper()} ({sentiment_report['sentiment']['overall_score']:+.3f})
        </span></p>
        
        <h2>🏆 Top 5 推荐</h2>
        <table>
            <tr>
                <th>排名</th>
                <th>股票</th>
                <th>代码</th>
                <th>行业</th>
                <th>价格</th>
                <th>综合评分</th>
                <th>技术分</th>
                <th>情绪分</th>
            </tr>
"""
    
    for i, stock in enumerate(results[:5], 1):
        score_class = 'score-positive' if stock['final_score'] > 0 else 'score-negative'
        html += f"""
            <tr>
                <td>{i}</td>
                <td>{stock['name']}</td>
                <td>{stock['code']}</td>
                <td>{stock['industry']}</td>
                <td>¥{stock['close']:.2f}</td>
                <td class="{score_class}">{stock['final_score']:+.1f}</td>
                <td>{stock['tech_score']:+d}</td>
                <td>{stock['sentiment_adjustment']:+.1f}</td>
            </tr>
"""
    
    html += """
        </table>
        
        <h2>📈 股票图表</h2>
        <div class="chart-grid">
"""
    
    for stock in results[:3]:
        chart_path = f"/home/kyj/.openclaw/workspace/data/charts/{stock['code'].replace('.', '_')}_chart.png"
        html += f"""
            <div class="chart-item">
                <h3>{stock['name']} ({stock['code']})</h3>
                <img src="{chart_path}" alt="{stock['name']} 图表">
                <p><strong>评分：</strong><span class="{score_class}">{stock['final_score']:+.1f}</span></p>
            </div>
"""
    
    html += f"""
        </div>
        
        <div class="disclaimer">
            <strong>⚠️ 免责声明：</strong> 本报告由 AI 系统自动生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。
        </div>
        
        <div class="footer">
            <p>DSS 智能股票分析系统 v5.0 | 生成时间：{today}</p>
            <p>数据源：Baostock | 情绪分析：NewsAPI | 图表：Matplotlib</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return save_path

def main():
    """主函数"""
    print("="*70)
    print("🚀 DSS v5.0 - 每日股票分析 (集成新闻情绪 + 图表)")
    print("="*70)
    
    # ========== 1. 获取市场情绪 ==========
    print("\n📰 [1/4] 获取市场情绪...")
    sentiment_report = get_market_sentiment_report()
    sentiment_score = sentiment_report['sentiment']['overall_score']
    print(f"   市场情绪：{sentiment_report['sentiment']['overall_sentiment']}")
    print(f"   情绪分数：{sentiment_score:+.3f}")
    
    # ========== 2. 获取加密货币市场 ==========
    print("\n🪙 [2/4] 获取加密货币市场...")
    try:
        btc = get_crypto_price('bitcoin', 'usd')
        if btc:
            print(f"   比特币：${btc['price']:,.2f} ({btc['change_24h']:+.2f}%)")
        else:
            print("   ⚠️ 无法获取加密货币数据（网络问题）")
    except:
        print("   ⚠️ 无法获取加密货币数据")
    
    # ========== 3. 分析股票 ==========
    print("\n📈 [3/4] 分析股票...")
    lg = bs.login()
    
    results = []
    for code, (name, industry) in CORE_STOCKS.items():
        # 获取数据
        rs = bs.query_history_k_data_plus(
            code,
            "date,close,volume",
            start_date=(datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
            frequency="d"
        )
        
        data = []
        while rs.next():
            data.append(rs.get_row_data())
        
        if not data:
            continue
        
        df = pd.DataFrame(data, columns=['date', 'close', 'volume'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # 添加指标
        df = add_technical_indicators(df)
        
        # 计算评分
        tech_score = calculate_stock_score(df)
        
        # 加入情绪调整
        final_score = tech_score + sentiment_score * 10
        
        results.append({
            'code': code,
            'name': name,
            'industry': industry,
            'close': df['close'].iloc[-1],
            'tech_score': tech_score,
            'sentiment_adjustment': round(sentiment_score * 10, 1),
            'final_score': round(final_score, 1),
            'df': df
        })
        
        print(f"   ✓ {name:8} ({code:10}) 评分：{final_score:+6.1f} (技术：{tech_score:+3d}, 情绪：{sentiment_score*10:+5.1f})")
    
    bs.logout()
    
    # ========== 4. 排序并生成图表 ==========
    print("\n📊 [4/4] 生成图表...")
    results.sort(key=lambda x: x['final_score'], reverse=True)
    
    # 为前 3 名生成图表
    for i, stock in enumerate(results[:3], 1):
        chart_path = f"/home/kyj/.openclaw/workspace/data/charts/{stock['code'].replace('.', '_')}_chart.png"
        generate_stock_chart(stock['code'], stock['name'], stock['df'], chart_path)
        print(f"   📈 {stock['name']} 图表已保存：{chart_path}")
    
    # ========== 输出报告 ==========
    print("\n" + "="*70)
    print("📋 DSS 每日投资建议报告")
    print("="*70)
    print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"市场情绪：{sentiment_report['sentiment']['overall_sentiment']} ({sentiment_score:+.3f})")
    print()
    print("🏆 Top 5 推荐:")
    print("-"*70)
    
    for i, stock in enumerate(results[:5], 1):
        emoji = "📈" if stock['final_score'] > 0 else "📉"
        print(f"{i}. {emoji} {stock['name']:8} ({stock['code']:10})")
        print(f"   行业：{stock['industry']:10} 价格：¥{stock['close']:>8.2f}")
        print(f"   综合评分：{stock['final_score']:+7.1f} (技术：{stock['tech_score']:+3d}, 情绪：{stock['sentiment_adjustment']:+5.1f})")
        print()
    
    # ========== 生成 HTML 报告 ==========
    print("🌐 [5/5] 生成 HTML 报告...")
    html_path = '/home/kyj/.openclaw/workspace/data/reports/dss_report_' + datetime.now().strftime('%Y%m%d_%H%M') + '.html'
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    generate_html_report(results, sentiment_report, html_path)
    print(f"   ✅ HTML 报告已保存：{html_path}")
    
    print("\n" + "="*70)
    print("📁 文件保存位置:")
    print("   图表：/home/kyj/.openclaw/workspace/data/charts/")
    print(f"   报告：{html_path}")
    print()
    print("💡 说明:")
    print("   - 综合评分 = 技术面评分 + 新闻情绪调整")
    print("   - 情绪分数来自财经新闻分析")
    print("   - 图表和 HTML 报告已保存，可在浏览器查看")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
