#!/usr/bin/env python3
"""
DSS 宏观事件分析模块 - 独立测试脚本

用法：
    python3 test_macro_analyzer.py

功能：
1. 获取当前宏观指标（油价、VIX、美元指数等）
2. 计算宏观风险指数
3. 评估对特定股票的影响
4. 生成测试报告

测试成熟后，可将 macro_adjustment 集成到 DSS 主系统
"""
import sys
import os
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from datetime import datetime
from dss_modules.macro_analyzer import (
    run_macro_analysis,
    get_macro_indicators,
    calculate_macro_risk_index,
    assess_industry_impact,
    INDUSTRY_MAP
)

# ============ 测试配置 ============

# 测试股票池（包含不同行业）
TEST_STOCKS = [
    # 航空业（对油价敏感）
    ('sh.601111', '中国国航', 'airline'),
    ('sh.600029', '南方航空', 'airline'),
    
    # 能源业（对油价正向敏感）
    ('sh.601857', '中国石油', 'energy'),
    ('sh.600028', '中国石化', 'energy'),
    
    # 消费业（防御性板块）
    ('sh.600519', '贵州茅台', 'consumer'),
    ('sz.000858', '五粮液', 'consumer'),
    
    # 金融业
    ('sh.601318', '中国平安', 'bank'),
    ('sh.601398', '工商银行', 'bank'),
]

# ============ 测试函数 ============

def test_macro_indicators():
    """测试宏观指标获取"""
    print("\n" + "="*60)
    print("📊 测试 1: 宏观指标获取")
    print("="*60)
    
    indicators = get_macro_indicators()
    
    print(f"\n获取时间：{indicators.get('timestamp', 'N/A')}")
    print(f"\n指标数据:")
    
    labels = {
        'oil_price': '🛢️ 原油价格 (WTI)',
        'vix': '📉 VIX 恐慌指数',
        'dxy': '💵 美元指数',
        'treasury_10y': '📜 10 年期美债收益率',
        'gold': '🥇 黄金价格'
    }
    
    for key, label in labels.items():
        value = indicators.get(key)
        if value:
            print(f"  {label}: {value}")
        else:
            print(f"  {label}: 获取失败")
    
    return indicators


def test_risk_index(indicators):
    """测试风险指数计算"""
    print("\n" + "="*60)
    print("⚠️  测试 2: 宏观风险指数")
    print("="*60)
    
    risk_result = calculate_macro_risk_index(indicators)
    
    risk_score = risk_result['risk_index']
    risk_level = risk_result['risk_level']
    
    # 风险等级图标
    level_icons = {
        'LOW': '🟢',
        'NORMAL': '🟡',
        'ELEVATED': '🟠',
        'HIGH': '🔴'
    }
    
    print(f"\n综合风险指数：{risk_score}")
    print(f"风险等级：{level_icons.get(risk_level, '⚪')} {risk_level}")
    
    print(f"\n风险因素分解:")
    for factor, status in risk_result['factors'].items():
        print(f"  {factor}: {status}")
    
    return risk_result


def test_stock_impact(indicators):
    """测试个股影响评估"""
    print("\n" + "="*60)
    print("🎯 测试 3: 个股影响评估")
    print("="*60)
    
    # 模拟宏观变化（实际使用时会从历史数据计算）
    macro_changes = {
        'oil_price_change_7d': 15.0,  # 油价上涨 15%
        'vix_change_7d': 25.0,  # VIX 上涨 25%
        'gold_change_7d': 8.0,  # 黄金上涨 8%
    }
    
    # 模拟新闻分析结果（实际使用时会从新闻 API 获取）
    news_analysis = {
        'sentiment_score': -30,  # 负面新闻
        'sentiment_label': 'negative',
        'hurt_industries': ['airline', 'consumer'],
        'benefit_industries': ['energy'],
        'confidence': 0.7
    }
    
    print(f"\n模拟情景:")
    print(f"  🛢️  油价 7 天变化：{macro_changes['oil_price_change_7d']:+.1f}%")
    print(f"  📉 VIX 7 天变化：{macro_changes['vix_change_7d']:+.1f}%")
    print(f"  📰 新闻情绪：{news_analysis['sentiment_label']} (score: {news_analysis['sentiment_score']})")
    
    print(f"\n个股影响评估:")
    print(f"{'股票代码':<12} {'名称':<10} {'行业':<12} {'调整系数':>10}")
    print("-"*50)
    
    results = []
    for symbol, name, industry in TEST_STOCKS:
        impact = assess_industry_impact(macro_changes, news_analysis, symbol, industry)
        results.append({
            'symbol': symbol,
            'name': name,
            'industry': industry,
            'impact': impact
        })
        
        # 调整系数图标
        if impact > 0.2:
            icon = "🟢++"
        elif impact > 0:
            icon = "🟢+"
        elif impact < -0.2:
            icon = "🔴--"
        elif impact < 0:
            icon = "🔴-"
        else:
            icon = "⚪"
        
        print(f"{symbol:<12} {name:<10} {industry:<12} {impact:>+8.2f} {icon}")
    
    # 排序
    results.sort(key=lambda x: x['impact'], reverse=True)
    
    print(f"\n🏆 最受益股票：{results[0]['name']} ({results[0]['symbol']}, {results[0]['impact']:+.2f})")
    print(f"📉 最受损股票：{results[-1]['name']} ({results[-1]['symbol']}, {results[-1]['impact']:+.2f})")
    
    return results


def test_full_analysis():
    """测试完整分析流程"""
    print("\n" + "="*60)
    print("🔄 测试 4: 完整分析流程")
    print("="*60)
    
    stock_list = [(s[0], s[2]) for s in TEST_STOCKS]
    result = run_macro_analysis(stock_list)
    
    print(f"\n分析完成时间：{result['timestamp']}")
    print(f"宏观风险指数：{result['risk_index']['risk_index']} ({result['risk_index']['risk_level']})")
    print(f"评估股票数量：{len(result['stock_impacts'])}")
    
    # 保存结果
    output_file = f"/home/kyj/.openclaw/workspace/data_cache/macro/macro_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 报告已保存：{output_file}")
    
    return result


# ============ 主函数 ============

def main():
    print("="*60)
    print("DSS Macro Analyzer - 独立测试套件")
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # 测试 1: 宏观指标获取
        indicators = test_macro_indicators()
        
        # 测试 2: 风险指数计算
        test_risk_index(indicators)
        
        # 测试 3: 个股影响评估
        test_stock_impact(indicators)
        
        # 测试 4: 完整分析流程
        test_full_analysis()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
