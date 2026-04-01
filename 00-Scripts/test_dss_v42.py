#!/usr/bin/env python3
"""
DSS v4.2 完整测试
展示去噪 + 新闻情绪分析功能
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import warnings
warnings.filterwarnings('ignore')

from dss_v4 import ImprovedStockPicker, NEWS_MODULES_AVAILABLE

print("="*60)
print("DSS v4.2 - 去噪 + 新闻情绪分析测试")
print("="*60)
print(f"\n新闻模块可用: {'✅' if NEWS_MODULES_AVAILABLE else '❌'}")

stocks = {
    'sh.601111': ('中国国航', '航空'),
    'sh.600519': ('贵州茅台', '白酒'),
    'sh.601398': ('工商银行', '银行'),
}

print("\n📊 完整分析:\n")
print("-"*50)

picker = ImprovedStockPicker(use_denoise=True, use_news_sentiment=True)

for code, (name, industry) in stocks.items():
    print(f"\n【{name}】({code})")
    
    analysis = picker.analyze_stock(code)
    prediction = picker.predict_with_confidence(code)
    
    if analysis and prediction:
        print(f"  收盘价: ¥{analysis['close']:.2f}")
        print(f"  技术评分: {analysis['tech_score']:+d}")
        
        # 情绪详情
        sent = analysis['sentiment_detail']
        print(f"  情绪评分:")
        print(f"    - 技术情绪: {sent['tech_score']:+d}")
        print(f"    - 新闻情绪: {sent['news_score']:+d}")
        print(f"    - 资金流向: {sent['money_flow_score']:+d}")
        print(f"    - 情绪总分: {sent['total']:+d}")
        
        # 新闻详情
        if sent['news_detail']:
            news = sent['news_detail']
            print(f"    - 新闻情绪: {news.get('sentiment_label', 'N/A')} (置信度: {news.get('confidence', 0):.0%})")
            if news.get('key_topics'):
                topics = [str(t) for t in news['key_topics'][:3]]
                print(f"    - 关键词: {', '.join(topics)}")
        
        # 资金流向详情
        if sent['money_flow_detail']:
            flow = sent['money_flow_detail']
            main_flow = flow.get('main_net_inflow', 0) / 10000
            print(f"    - 主力净流入: {main_flow:.2f}万元")
        
        print(f"  综合评分: {analysis['total_score']:+d}")
        print(f"  预测: {prediction['direction']} (置信度: {prediction['confidence']:.0f}%)")
    else:
        print("  分析失败")

print("\n" + "="*60)