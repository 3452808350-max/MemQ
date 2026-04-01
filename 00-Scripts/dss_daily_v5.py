#!/usr/bin/env python3
"""
DSS Daily - v5.0 增强版
在原有 dss_daily_optimized.py 基础上添加：
1. 新闻情绪分析
2. 图表生成
3. HTML 报告
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

# 先运行原有逻辑
exec(open('/home/kyj/.openclaw/workspace/dss_daily_optimized.py').read())

# 然后添加增强功能
from dss_modules.api_news import get_market_sentiment_report, calculate_news_impact_score
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def generate_enhanced_charts(results, save_dir='/home/kyj/.openclaw/workspace/data/charts'):
    """为 Top 3 股票生成增强图表"""
    os.makedirs(save_dir, exist_ok=True)
    
    for stock in results[:3]:
        code = stock['code']
        name = stock['name']
        
        # 获取历史数据
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
        
        # 计算均线
        df['MA5'] = df['close'].rolling(5).mean()
        df['MA20'] = df['close'].rolling(20).mean()
        
        # 创建图表
        fig, axes = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={'height_ratios': [3, 1]})
        
        # 上图：股价
        ax1 = axes[0]
        dates = pd.to_datetime(df['date'])
        is_up = df['close'].iloc[-1] > df['close'].iloc[0]
        color = '#d62728' if is_up else '#1f77b4'
        
        ax1.plot(dates, df['close'], label='收盘价', linewidth=2.5, color=color)
        ax1.plot(dates, df['MA5'], label='MA5', linewidth=1.5, color='#ff7f0e', alpha=0.8)
        ax1.plot(dates, df['MA20'], label='MA20', linewidth=1.5, color='#2ca02c', alpha=0.8)
        ax1.fill_between(dates, df['close'], alpha=0.1, color=color)
        
        change_pct = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        ax1.set_title(f'{name} ({code}) - {df["close"].iloc[-1]:.2f}元  ({change_pct:+.1f}%)', 
                     fontsize=14, fontweight='bold', pad=15)
        ax1.set_ylabel('价格 (元)', fontsize=12)
        ax1.legend(loc='upper left', framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # 下图：成交量
        ax2 = axes[1]
        vol_colors = ['#d62728' if df['close'].iloc[i] > df['close'].iloc[i-1] else '#1f77b4' 
                     for i in range(1, len(df))]
        vol_colors = ['gray'] + vol_colors
        ax2.bar(range(len(df)), vol_colors, color=vol_colors, alpha=0.6)
        ax2.set_ylabel('成交量', fontsize=12)
        ax2.set_xlabel('日期', fontsize=12)
        ax2.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        plt.tight_layout()
        save_path = f"{save_dir}/{code.replace('.', '_')}_chart.png"
        plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   📈 {name} 图表已保存：{save_path}")


def generate_html_report(results, sentiment_report, save_path):
    """生成 HTML 报告"""
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    sentiment_score = sentiment_report['sentiment']['overall_score']
    sentiment_label = sentiment_report['sentiment']['overall_sentiment']
    
    html = f"""<!DOCTYPE html>
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
        <p><strong>市场情绪：</strong><span class="sentiment {'positive' if sentiment_score > 0 else 'negative' if sentiment_score < 0 else 'neutral'}">
            {sentiment_label.upper()} ({sentiment_score:+.3f})
        </span></p>
        
        <h2>🏆 Top 5 推荐</h2>
        <table>
            <tr><th>排名</th><th>股票</th><th>代码</th><th>行业</th><th>价格</th><th>评分</th><th>RSI</th><th>MACD</th></tr>
"""
    
    for i, stock in enumerate(results[:5], 1):
        score_class = 'score-positive' if stock['score'] > 0 else 'score-negative'
        html += f"""<tr>
            <td>{i}</td><td>{stock['name']}</td><td>{stock['code']}</td>
            <td>{stock['industry']}</td><td>¥{stock['close']:.2f}</td>
            <td class="{score_class}">{stock['score']:+d}</td>
            <td>{stock['rsi']:.1f}</td><td>{stock['macd']}</td>
        </tr>"""
    
    html += """</table><h2>📈 股票图表</h2><div class="chart-grid">"""
    
    for stock in results[:3]:
        chart_path = f"/home/kyj/.openclaw/workspace/data/charts/{stock['code'].replace('.', '_')}_chart.png"
        html += f"""<div class="chart-item">
            <h3>{stock['name']} ({stock['code']})</h3>
            <img src="{chart_path}" alt="{stock['name']}">
            <p><strong>评分：</strong><span class="{score_class}">{stock['score']:+d}</span></p>
        </div>"""
    
    html += f"""</div><div class="disclaimer">
        <strong>⚠️ 免责声明：</strong> 本报告由 AI 系统自动生成，仅供参考，不构成投资建议。
    </div><div class="footer">
        <p>DSS 智能股票分析系统 v5.0 | {today}</p>
    </div></div></body></html>"""
    
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return save_path


# 主程序
if __name__ == "__main__":
    print("="*70)
    print("🚀 DSS v5.0 - 每日股票分析 (增强版)")
    print("="*70)
    
    # 1. 获取市场情绪
    print("\n📰 [1/5] 获取市场情绪...")
    sentiment_report = get_market_sentiment_report()
    sentiment_score = sentiment_report['sentiment']['overall_score']
    print(f"   市场情绪：{sentiment_report['sentiment']['overall_sentiment']} ({sentiment_score:+.3f})")
    
    # 2. 运行原有分析
    print("\n📈 [2/5] 分析股票...")
    results = generate_report()
    
    if not results:
        print("❌ 分析失败")
        sys.exit(1)
    
    # 3. 应用情绪调整
    print("\n🎯 [3/5] 应用情绪调整...")
    for stock in results:
        stock['sentiment_adjust'] = int(sentiment_score * 10)
        stock['final_score'] = stock['score'] + stock['sentiment_adjust']
    
    results.sort(key=lambda x: x['final_score'], reverse=True)
    
    for stock in results[:5]:
        print(f"   ✓ {stock['name']:8} 原评分：{stock['score']:+3d} → 调整后：{stock['final_score']:+4d}")
    
    # 4. 生成图表
    print("\n📊 [4/5] 生成图表...")
    generate_enhanced_charts(results)
    
    # 5. 生成 HTML 报告
    print("\n🌐 [5/5] 生成 HTML 报告...")
    html_path = f"/home/kyj/.openclaw/workspace/data/reports/dss_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    generate_html_report(results, sentiment_report, html_path)
    print(f"   ✅ HTML 报告已保存：{html_path}")
    
    # 输出最终报告
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
        print(f"{i}. {emoji} {stock['name']:8} ({stock['code']})")
        print(f"   行业：{stock['industry']:10} 价格：¥{stock['close']:>8.2f}")
        print(f"   综合评分：{stock['final_score']:+7d} (原始：{stock['score']:+3d}, 情绪：{stock['sentiment_adjust']:+4d})")
        print(f"   RSI: {stock['rsi']:.1f} | MACD: {stock['macd']}")
        print()
    
    print("="*70)
    print("📁 文件保存位置:")
    print("   图表：/home/kyj/.openclaw/workspace/data/charts/")
    print(f"   报告：{html_path}")
    print("="*70 + "\n")
