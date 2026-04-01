#!/usr/bin/env python3
"""
DSS v4.3 完整测试
整合：去噪 + 新闻情绪 + 研报 + Seeking Alpha
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("DSS v4.3 完整系统测试")
print("="*70)

# ============ 1. 测试数据获取 ============
print("\n📊 1. 数据获取测试")
print("-"*50)

from dss_modules.data_loader import get_stock_data

# A股测试
print("【A股数据】")
df_a = get_stock_data('sh.600519', days=100, source='baostock')
if df_a is not None:
    print(f"  ✅ 茅台: {len(df_a)}天数据, 最新收盘 ¥{df_a['Close'].iloc[-1]:.2f}")
else:
    print("  ❌ 茅台数据获取失败")

# ============ 2. 测试去噪模块 ============
print("\n📊 2. 去噪模块测试")
print("-"*50)

from denoiser import Denoiser

if df_a is not None:
    denoiser = Denoiser(method='kalman')
    original = df_a['Close'].values
    denoised = denoiser.denoise(original)
    
    metrics = Denoiser.evaluate(original, denoised)
    print(f"  ✅ Kalman去噪:")
    print(f"     SNR: {metrics['snr']:.2f}dB")
    print(f"     MSE: {metrics['mse']:.4f}")
    print(f"     平滑度: {metrics['smoothness']:.4f}")

# ============ 3. 测试研报模块 ============
print("\n📊 3. 研报数据测试")
print("-"*50)

try:
    from dss_modules.research_report_crawler import get_research_reports, get_rating_summary
    
    print("【东方财富研报】")
    reports = get_research_reports('600519', page_size=3)
    if reports:
        print(f"  ✅ 获取 {len(reports)} 条研报")
        for r in reports[:2]:
            rating = r.get('rating', 'N/A')
            title = r.get('title', '')[:30]
            org = r.get('org', 'N/A')
            print(f"     [{rating}] {title}... - {org}")
        
        # 评级汇总
        summary = get_rating_summary('600519')
        if summary:
            print(f"  📈 评级汇总: 买入{summary.get('buy',0)} 增持{summary.get('outperform',0)} 中性{summary.get('neutral',0)}")
    else:
        print("  ⚠️ 暂无研报数据")
except Exception as e:
    print(f"  ❌ 研报模块错误: {e}")

# ============ 4. 测试Seeking Alpha ============
print("\n📊 4. Seeking Alpha测试 (中概股)")
print("-"*50)

try:
    from dss_modules.seeking_alpha_crawler import SeekingAlphaCrawler
    
    sa = SeekingAlphaCrawler()
    
    # 测试阿里巴巴
    print("【阿里巴巴 BABA】")
    articles = sa.get_seeking_alpha_analysis('BABA', pages=1)  # 修复: pages参数
    if articles:
        bullish = sum(1 for a in articles if a.get('sentiment') == 'Bullish')
        bearish = sum(1 for a in articles if a.get('sentiment') == 'Bearish')
        print(f"  ✅ 获取 {len(articles)} 篇分析")
        print(f"     Bullish: {bullish}, Bearish: {bearish}")
        
        for a in articles[:2]:
            sentiment = a.get('sentiment', 'N/A')
            title = a.get('title', '')[:40]
            print(f"     [{sentiment}] {title}...")
    else:
        print("  ⚠️ 未获取到文章")
except Exception as e:
    print(f"  ❌ Seeking Alpha模块错误: {e}")

# ============ 5. 测试资金流向 ============
print("\n📊 5. 资金流向测试")
print("-"*50)

try:
    from dss_modules.eastmoney_crawler import get_money_flow
    
    print("【茅台资金流向】")
    flow = get_money_flow('600519', days=3)
    if flow and isinstance(flow, dict):
        main_inflow = flow.get('main_net_inflow', 0) or 0
        retail_inflow = flow.get('retail_net_inflow', 0) or 0
        print(f"  ✅ 主力净流入: {main_inflow/10000:.2f}万元")
        print(f"     散户净流入: {retail_inflow/10000:.2f}万元")
    else:
        print("  ⚠️ 暂无资金流向数据")
except Exception as e:
    print(f"  ❌ 资金流向模块错误: {e}")

# ============ 6. 测试新闻情绪 ============
print("\n📊 6. 新闻情绪测试")
print("-"*50)

try:
    from dss_modules.news_crawler import get_hot_news
    from dss_modules.news_sentiment import analyze_news_sentiment
    
    print("【热点财经新闻】")
    news = get_hot_news(limit=5)
    if news:
        print(f"  ✅ 获取 {len(news)} 条热点新闻")
        
        # 分析情绪
        result = analyze_news_sentiment(news)
        if result:
            # SentimentResult是dataclass，用属性访问
            sentiment_val = result.sentiment if hasattr(result, 'sentiment') else 0
            confidence_val = result.confidence if hasattr(result, 'confidence') else 0
            topics_val = result.key_topics if hasattr(result, 'key_topics') else []
            
            # 情绪标签
            if sentiment_val > 0.2:
                label = '乐观'
            elif sentiment_val < -0.2:
                label = '悲观'
            else:
                label = '中性'
            
            print(f"     整体情绪: {label}")
            print(f"     情绪分数: {sentiment_val:.2f}")
            print(f"     置信度: {confidence_val:.0%}")
            
            if topics_val:
                topics = [str(t) for t in topics_val[:3]]
                print(f"     关键词: {', '.join(topics)}")
    else:
        print("  ⚠️ 暂无新闻数据")
except Exception as e:
    print(f"  ❌ 新闻情绪模块错误: {e}")

# ============ 7. 完整选股测试 ============
print("\n" + "="*70)
print("📊 7. DSS完整选股测试")
print("="*70)

from dss_v4 import ImprovedStockPicker

stocks = {
    'sh.600519': ('贵州茅台', '白酒'),
    'sh.601398': ('工商银行', '银行'),
    'sh.601111': ('中国国航', '航空'),
}

picker = ImprovedStockPicker(use_denoise=True, use_news_sentiment=True)

results = []
for code, (name, industry) in stocks.items():
    analysis = picker.analyze_stock(code)
    prediction = picker.predict_with_confidence(code)
    
    if analysis and prediction:
        analysis['name'] = name
        analysis['industry'] = industry
        analysis['prediction'] = prediction
        results.append(analysis)

# 排序
results.sort(key=lambda x: x['total_score'], reverse=True)

print("\n【选股结果】")
print("-"*70)
for i, r in enumerate(results, 1):
    pred = r['prediction']
    sent = r['sentiment_detail']
    
    print(f"\n{i}. {r['name']} ({r['symbol']})")
    print(f"   收盘价: ¥{r['close']:.2f}")
    print(f"   技术评分: {r['tech_score']:+d}")
    print(f"   情绪评分: {sent['total']:+.1f}")
    print(f"     - 技术情绪: {sent['tech_score']:+.1f}")
    print(f"     - 新闻情绪: {sent['news_score']:+.1f}")
    print(f"     - 资金流向: {sent['money_flow_score']:+.1f}")
    print(f"     - 国际视角: {sent.get('international_score', 0):+.1f}")
    
    # 国际视角详情
    if sent.get('international_detail'):
        intl = sent['international_detail']
        if intl.get('results'):
            print(f"     [国际参考: {intl.get('symbol', 'N/A')}]")
    
    print(f"   综合评分: {r['total_score']:+d}")
    print(f"   预测: {pred['direction']} (置信度 {pred['confidence']:.0f}%)")
    
    # 研报评级
    pe = r['fundamentals']['pe']
    roe = r['fundamentals']['roe']
    pe_str = f"{pe:.1f}" if pe else "N/A"
    roe_str = f"{roe:.1f}%" if roe else "N/A"
    print(f"   基本面: PE={pe_str}, ROE={roe_str}")

print("\n" + "="*70)
print("✅ 测试完成!")
print("="*70)