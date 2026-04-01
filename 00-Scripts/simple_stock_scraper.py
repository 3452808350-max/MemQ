#!/usr/bin/env python3
"""
Simple Stock Market Data Fetcher
Uses free APIs to get market data
"""

import requests
import json
from datetime import datetime
import time

print("=" * 80)
print("SIMPLE STOCK MARKET DATA FETCHER")
print("=" * 80)
print()

def get_market_data():
    """Fetch market data using free APIs"""
    
    print("📊 FETCHING MARKET DATA...")
    print()
    
    market_data = {
        'US': {},
        'HK': {},
        'A': {}
    }
    
    try:
        # Try to use Alpha Vantage API (free tier)
        # Note: You would need an API key for full functionality
        print("Using simulated data (real API requires key)")
        print("To get real data, you need API keys from:")
        print("1. Alpha Vantage (alphavantage.co) - free tier available")
        print("2. Yahoo Finance API (unofficial)")
        print("3. Other financial data providers")
        print()
        
        # Simulated data for demonstration
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # US Market (simulated)
        market_data['US'] = {
            'S&P 500': {'price': 4950.25, 'change': 0.45, 'symbol': '^GSPC'},
            'NASDAQ': {'price': 15680.35, 'change': 0.82, 'symbol': '^IXIC'},
            'Dow Jones': {'price': 38500.75, 'change': 0.25, 'symbol': '^DJI'},
            'Apple': {'price': 185.20, 'change': 1.20, 'symbol': 'AAPL'},
            'Tesla': {'price': 195.50, 'change': -0.85, 'symbol': 'TSLA'},
            'NVIDIA': {'price': 720.30, 'change': 2.35, 'symbol': 'NVDA'}
        }
        
        # Hong Kong Market (simulated)
        market_data['HK'] = {
            'Hang Seng': {'price': 16580.45, 'change': -0.35, 'symbol': '^HSI'},
            'Tencent': {'price': 285.60, 'change': 0.45, 'symbol': '0700.HK'},
            'Alibaba': {'price': 75.80, 'change': -1.20, 'symbol': '9988.HK'},
            'Meituan': {'price': 92.35, 'change': 0.75, 'symbol': '3690.HK'}
        }
        
        # A-Shares (simulated)
        market_data['A'] = {
            'SSE Composite': {'price': 3050.25, 'change': 0.15, 'symbol': '000001.SS'},
            'SZSE Component': {'price': 9850.75, 'change': -0.25, 'symbol': '399001.SZ'},
            'Kweichow Moutai': {'price': 1650.80, 'change': 0.85, 'symbol': '600519.SS'},
            'Ping An Insurance': {'price': 42.35, 'change': -0.45, 'symbol': '601318.SS'}
        }
        
        return market_data, current_time
        
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def analyze_market(market_data):
    """Analyze market trends"""
    
    print("🔍 MARKET ANALYSIS")
    print("-" * 40)
    
    insights = []
    
    # Analyze each market
    for market_name, stocks in market_data.items():
        if stocks:
            gainers = [(name, data) for name, data in stocks.items() if data['change'] > 0]
            losers = [(name, data) for name, data in stocks.items() if data['change'] < 0]
            
            if gainers:
                top_gainer = max(gainers, key=lambda x: x[1]['change'])
                insights.append(f"📈 {market_name} Top Gainer: {top_gainer[0]} (+{top_gainer[1]['change']}%)")
            
            if losers:
                top_loser = min(losers, key=lambda x: x[1]['change'])
                insights.append(f"📉 {market_name} Top Loser: {top_loser[0]} ({top_loser[1]['change']}%)")
    
    # Overall sentiment
    all_stocks = []
    for stocks in market_data.values():
        all_stocks.extend(stocks.values())
    
    if all_stocks:
        positive = sum(1 for s in all_stocks if s['change'] > 0)
        negative = sum(1 for s in all_stocks if s['change'] < 0)
        total = len(all_stocks)
        
        if positive > negative:
            sentiment = "🟢 BULLISH"
        elif negative > positive:
            sentiment = "🔴 BEARISH"
        else:
            sentiment = "🟡 NEUTRAL"
        
        insights.append(f"\n📊 OVERALL SENTIMENT: {sentiment}")
        insights.append(f"   Positive: {positive}/{total} | Negative: {negative}/{total}")
    
    return insights

def display_data(market_data, current_time, insights):
    """Display market data"""
    
    print("\n" + "=" * 80)
    print("MARKET DATA SUMMARY")
    print("=" * 80)
    print(f"Last Updated: {current_time}")
    print()
    
    # Display each market
    markets = [
        ("🇺🇸 US MARKET", market_data['US'], "$"),
        ("🇭🇰 HONG KONG MARKET", market_data['HK'], "HK$"),
        ("🇨🇳 A-SHARES", market_data['A'], "¥")
    ]
    
    for market_name, stocks, currency in markets:
        if stocks:
            print(f"\n{market_name}")
            print("-" * 40)
            for name, data in stocks.items():
                change = data['change']
                change_icon = "🟢" if change > 0 else "🔴" if change < 0 else "🟡"
                change_sign = "+" if change > 0 else ""
                print(f"{change_icon} {name:20} {currency}{data['price']:10.2f} {change_sign}{change:6.2f}%")
    
    # Display insights
    if insights:
        print("\n" + "=" * 80)
        print("ANALYSIS & INSIGHTS")
        print("=" * 80)
        for insight in insights:
            print(insight)

def get_real_time_data_option():
    """Show options for getting real-time data"""
    
    print("\n" + "=" * 80)
    print("HOW TO GET REAL-TIME DATA")
    print("=" * 80)
    
    print("\n🔑 FREE API OPTIONS:")
    print("1. Alpha Vantage (alphavantage.co)")
    print("   • Free tier: 5 API calls per minute, 500 per day")
    print("   • Get key: Sign up for free account")
    
    print("\n2. Yahoo Finance (yfinance Python library)")
    print("   • Unofficial API, no key required")
    print("   • Install: pip install yfinance")
    print("   • May have rate limits")
    
    print("\n3. Financial Modeling Prep (financialmodelingprep.com)")
    print("   • Free tier: 250 requests per day")
    print("   • Good for US stocks")
    
    print("\n📱 CHINA-SPECIFIC OPTIONS:")
    print("• East Money (东方财富) API")
    print("• Sina Finance (新浪财经) API")
    print("• Tencent Finance (腾讯财经) API")
    print("• Note: Chinese APIs may require authentication")
    
    print("\n💡 RECOMMENDATION:")
    print("Start with Alpha Vantage for US stocks")
    print("Use yfinance for quick prototyping")
    print("For A-shares, consider web scraping Chinese financial sites")

def create_implementation_plan():
    """Create a plan for implementing real data collection"""
    
    print("\n" + "=" * 80)
    print("IMPLEMENTATION PLAN")
    print("=" * 80)
    
    plan = """
    PHASE 1: SETUP (Week 1)
    1. Sign up for Alpha Vantage API (free)
    2. Install required libraries:
       pip install pandas yfinance requests
    3. Test basic data fetching
    
    PHASE 2: US MARKET (Week 2)
    1. Implement Alpha Vantage for US stocks
    2. Add error handling and rate limiting
    3. Create data storage (CSV/JSON)
    
    PHASE 3: HK & A-SHARES (Week 3)
    1. Research Chinese financial APIs
    2. Implement HK stock data
    3. Implement A-share data (most challenging)
    
    PHASE 4: ANALYSIS (Week 4)
    1. Add technical indicators
    2. Implement trend analysis
    3. Create visualization
    
    PHASE 5: AUTOMATION (Week 5)
    1. Schedule daily updates
    2. Add email/SMS alerts
    3. Create web dashboard
    """
    
    print(plan)

def main():
    """Main function"""
    
    # Get market data
    market_data, current_time = get_market_data()
    
    if not market_data:
        print("❌ Failed to fetch market data")
        return
    
    # Analyze
    insights = analyze_market(market_data)
    
    # Display
    display_data(market_data, current_time, insights)
    
    # Show real data options
    get_real_time_data_option()
    
    # Show implementation plan
    create_implementation_plan()
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n1. Get API keys for real data")
    print("2. Modify code to use real APIs")
    print("3. Add more stocks and indices")
    print("4. Implement data storage and analysis")
    print("\nReady to build your real market data system! 🚀")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")