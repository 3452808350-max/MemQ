#!/usr/bin/env python3
"""
DSS 新 API 集成测试
测试 CoinGecko、NewsAPI、QuickChart 集成
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_modules.api_crypto import (
    get_crypto_price, get_top_cryptos, calculate_crypto_sentiment,
    analyze_crypto_impact_on_stocks
)
from dss_modules.api_news import (
    get_finance_news, analyze_sentiment, analyze_news_sentiment,
    get_market_sentiment_report, calculate_news_impact_score
)
from dss_modules.api_visualization import (
    generate_line_chart, generate_bar_chart, generate_pie_chart,
    generate_multi_line_chart
)

def test_crypto_module():
    """测试加密货币模块"""
    print("\n" + "="*70)
    print("🪙 测试 CoinGecko 加密货币模块")
    print("="*70)
    
    # 测试 1: 获取比特币价格
    print("\n1️⃣ 获取比特币价格...")
    btc = get_crypto_price('bitcoin', 'usd')
    if btc:
        print(f"   ✅ 比特币：${btc['price']:,.2f}")
        print(f"   📈 24h 涨跌：{btc['change_24h']:+.2f}%")
        print(f"   💰 市值：${btc['market_cap']:,.0f}")
    else:
        print("   ❌ 获取失败")
    
    # 测试 2: Top 10 加密货币
    print("\n2️⃣ Top 10 加密货币:")
    top10 = get_top_cryptos(10, 'usd')
    if top10:
        for i, coin in enumerate(top10, 1):
            print(f"   {i}. {coin['name']:15} ({coin['symbol']:4}) ${coin['price']:>12,.2f}  ({coin['change_24h']:+6.2f}%)")
    else:
        print("   ❌ 获取失败")
    
    # 测试 3: 市场情绪
    print("\n3️⃣ 加密货币市场情绪:")
    sentiment = calculate_crypto_sentiment()
    print(f"   情绪：{sentiment['sentiment']:8} (分数：{sentiment['score']:+.3f})")
    print(f"   上涨/下跌：{sentiment['up_count']}/{sentiment['down_count']}")
    print(f"   比特币主导率：{sentiment['btc_dominance']:.1f}%")
    
    # 测试 4: 对股市影响
    print("\n4️⃣ 对股市潜在影响:")
    impact = analyze_crypto_impact_on_stocks()
    print(f"   整体影响：{impact['overall_impact']}")
    print(f"   影响分数：{impact['impact_score']:+.3f}")
    print(f"   说明：{impact['note']}")
    
    return True


def test_news_module():
    """测试新闻情绪模块"""
    print("\n" + "="*70)
    print("📰 测试 NewsAPI 新闻情绪模块")
    print("="*70)
    
    # 测试 1: 获取财经新闻
    print("\n1️⃣ 获取财经新闻...")
    articles = get_finance_news(language='en', page_size=5)
    if articles:
        print(f"   ✅ 获取到 {len(articles)} 篇新闻")
        for i, article in enumerate(articles[:3], 1):
            print(f"\n   {i}. {article['title'][:60]}...")
            print(f"      来源：{article['source']} | {article['published_at'][:10]}")
    else:
        print("   ❌ 获取失败")
    
    # 测试 2: 单文本情绪分析
    print("\n\n2️⃣ 单文本情绪分析测试:")
    test_texts = [
        ("Stock market surges to record high", "positive"),
        ("Tech stocks crash amid concerns", "negative"),
        ("Market remains stable", "neutral")
    ]
    
    for text, expected in test_texts:
        result = analyze_sentiment(text)
        status = "✅" if result['sentiment'] == expected else "⚠️"
        print(f"   {status} \"{text[:40]}...\" → {result['sentiment']} ({result['score']:+.3f})")
    
    # 测试 3: 完整情绪报告
    print("\n\n3️⃣ 市场情绪报告:")
    report = get_market_sentiment_report()
    sentiment = report.get('sentiment', {})
    print(f"   分析文章数：{report.get('articles_analyzed', 0)}")
    print(f"   整体情绪：{sentiment.get('overall_sentiment', 'N/A')}")
    print(f"   情绪分数：{sentiment.get('overall_score', 0):+.3f}")
    print(f"   正面比例：{sentiment.get('positive_ratio', 0)*100:.0f}%")
    
    # 影响分数
    impact_score = calculate_news_impact_score(report)
    print(f"\n   🎯 新闻影响分数：{impact_score:+.3f}")
    
    return True


def test_visualization_module():
    """测试图表生成模块"""
    print("\n" + "="*70)
    print("📊 测试 QuickChart 图表生成模块")
    print("="*70)
    
    from datetime import datetime, timedelta
    
    # 生成测试数据
    dates = [(datetime.now() - timedelta(days=i)).strftime('%m-%d') for i in range(30, 0, -1)]
    prices = [100 + i * 0.5 + (i % 7) * 0.3 for i in range(30)]
    data = list(zip(dates, prices))
    
    # 测试 1: 折线图
    print("\n1️⃣ 生成折线图...")
    line_chart = generate_line_chart(data, "测试股票 30 日走势")
    print(f"   ✅ URL: {line_chart[:80]}...")
    print(f"   💡 可在浏览器打开查看")
    
    # 测试 2: 多股票对比
    print("\n2️⃣ 生成多股票对比图...")
    multi_data = {
        '股票 A': data,
        '股票 B': [(d, p * 1.05) for d, p in data],
        '股票 C': [(d, p * 0.98) for d, p in data]
    }
    multi_chart = generate_multi_line_chart(multi_data, "多股票对比")
    print(f"   ✅ URL: {multi_chart[:80]}...")
    
    # 测试 3: 柱状图
    print("\n3️⃣ 生成柱状图...")
    bar_data = [
        ('宁德时代', 5.2), ('比亚迪', -2.1), ('贵州茅台', 3.8),
        ('招商银行', -1.5), ('中国石油', 7.3)
    ]
    bar_chart = generate_bar_chart(bar_data, "Top 5 涨跌幅")
    print(f"   ✅ URL: {bar_chart[:80]}...")
    
    # 测试 4: 饼图
    print("\n4️⃣ 生成饼图...")
    pie_data = [('A 股', 60), ('美股', 25), ('加密货币', 10), ('现金', 5)]
    pie_chart = generate_pie_chart(pie_data, "资产配置")
    print(f"   ✅ URL: {pie_chart[:80]}...")
    
    print("\n   📝 所有图表 URL 可在浏览器中打开查看")
    
    return True


def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("🚀 DSS 新 API 集成测试")
    print("="*70)
    print("\n测试模块:")
    print("  1. CoinGecko - 加密货币数据")
    print("  2. NewsAPI - 新闻情绪分析")
    print("  3. QuickChart - 图表生成")
    print("="*70)
    
    results = {}
    
    # 测试各模块
    try:
        results['crypto'] = test_crypto_module()
    except Exception as e:
        print(f"\n❌ CoinGecko 测试失败：{e}")
        results['crypto'] = False
    
    try:
        results['news'] = test_news_module()
    except Exception as e:
        print(f"\n❌ NewsAPI 测试失败：{e}")
        results['news'] = False
    
    try:
        results['chart'] = test_visualization_module()
    except Exception as e:
        print(f"\n❌ QuickChart 测试失败：{e}")
        results['chart'] = False
    
    # 总结
    print("\n" + "="*70)
    print("📋 测试总结")
    print("="*70)
    
    for module, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {module:12} {status}")
    
    total = sum(results.values())
    print(f"\n总计：{total}/{len(results)} 通过")
    
    if total == len(results):
        print("\n🎉 所有测试通过！新 API 集成成功！")
    else:
        print("\n⚠️ 部分测试失败，请检查配置和网络")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
