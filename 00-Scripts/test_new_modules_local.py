#!/usr/bin/env python3
"""
DSS 新模块本地测试（不依赖外部 API）
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_modules.api_news import analyze_sentiment, analyze_news_sentiment
from dss_modules.api_visualization import (
    generate_line_chart, generate_bar_chart, generate_pie_chart,
    generate_multi_line_chart
)
from datetime import datetime, timedelta

print("="*70)
print("🚀 DSS 新模块本地测试")
print("="*70)

# ========== 测试新闻情绪分析 ==========
print("\n" + "="*70)
print("📰 测试新闻情绪分析")
print("="*70)

test_texts = [
    "Stock market surges to record high on strong earnings",
    "Tech stocks crash amid regulatory concerns",
    "Market remains stable as investors wait for Fed decision",
    "Bitcoin breaks $50,000 as institutional adoption grows",
    "Federal Reserve announces interest rate cut"
]

print("\n单文本情绪分析:")
for text in test_texts:
    result = analyze_sentiment(text)
    emoji = "📈" if result['sentiment'] == 'positive' else "📉" if result['sentiment'] == 'negative' else "➡️"
    print(f"   {emoji} {result['sentiment']:9} ({result['score']:+.3f}) - {text[:50]}...")

# 批量分析
print("\n批量新闻情绪分析:")
mock_articles = [
    {'title': 'Tech stocks rally on AI boom', 'description': 'Major tech companies surge'},
    {'title': 'Oil prices drop on demand concerns', 'description': 'Energy sector under pressure'},
    {'title': 'Fed maintains steady policy', 'description': 'Central bank keeps rates unchanged'},
    {'title': 'Crypto market sees mixed signals', 'description': 'Bitcoin up, altcoins down'},
]

batch_result = analyze_news_sentiment(mock_articles)
print(f"   分析文章数：{batch_result['article_count']}")
print(f"   整体情绪：{batch_result['overall_sentiment']}")
print(f"   情绪分数：{batch_result['overall_score']:+.3f}")
print(f"   正面/负面：{batch_result['positive_ratio']*100:.0f}% / {batch_result['negative_ratio']*100:.0f}%")

# ========== 测试图表生成 ==========
print("\n" + "="*70)
print("📊 测试图表生成")
print("="*70)

# 生成测试数据
dates = [(datetime.now() - timedelta(days=i)).strftime('%m-%d') for i in range(30, 0, -1)]
prices = [100 + i * 0.5 + (i % 7) * 0.3 for i in range(30)]
data = list(zip(dates, prices))

# 测试折线图
print("\n1️⃣ 折线图 (股价走势):")
line_chart = generate_line_chart(data, "测试股票 30 日走势", width=800, height=400)
print(f"   ✅ URL 已生成 ({len(line_chart)} 字符)")
print(f"   🔗 {line_chart[:100]}...")

# 测试多股票对比
print("\n2️⃣ 多股票对比图:")
multi_data = {
    '宁德时代': data,
    '比亚迪': [(d, p * 1.05) for d, p in data],
    '贵州茅台': [(d, p * 0.98) for d, p in data]
}
multi_chart = generate_multi_line_chart(multi_data, "热门股票对比", width=800, height=400)
print(f"   ✅ URL 已生成 ({len(multi_chart)} 字符)")

# 测试柱状图
print("\n3️⃣ 柱状图 (涨跌幅):")
bar_data = [
    ('宁德时代', 5.2), ('比亚迪', -2.1), ('贵州茅台', 3.8),
    ('招商银行', -1.5), ('中国石油', 7.3)
]
bar_chart = generate_bar_chart(bar_data, "Top 5 涨跌幅对比", width=800, height=400)
print(f"   ✅ URL 已生成 ({len(bar_chart)} 字符)")

# 测试饼图
print("\n4️⃣ 饼图 (资产配置):")
pie_data = [('A 股', 60), ('美股', 25), ('加密货币', 10), ('现金', 5)]
pie_chart = generate_pie_chart(pie_data, "投资组合配置", width=500, height=500)
print(f"   ✅ URL 已生成 ({len(pie_chart)} 字符)")

# ========== 总结 ==========
print("\n" + "="*70)
print("📋 测试总结")
print("="*70)
print("""
✅ 新闻情绪分析模块 - 正常
✅ 图表生成模块 - 正常

📝 使用说明:
   1. 图表 URL 可在浏览器中直接打开查看
   2. 邮件报告中可嵌入图表图片
   3. NewsAPI 需自行申请 Key (免费 100 次/天)

🔗 配置位置:
   - dss_config.py 中的 EXTERNAL_APIS 配置
   - 设置 newsapi.key 为你的 API Key

🚀 下一步:
   - 将新模块集成到 dss_daily_optimized.py
   - 在邮件报告中添加图表和情绪分析
""")
print("="*70 + "\n")
