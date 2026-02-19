#!/usr/bin/env python3
"""
Stock Market Data Scraper & Analyzer
Fetches latest US, Hong Kong, and A-share market data
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import yfinance as yf
import sys

print("=" * 80)
print("STOCK MARKET DATA SCRAPER & ANALYZER")
print("=" * 80)
print()

def get_us_stocks():
    """Fetch major US stock indices and tech stocks"""
    print("📈 FETCHING US MARKET DATA...")
    
    # Major indices
    indices = {
        'S&P 500': '^GSPC',
        'NASDAQ': '^IXIC', 
        'Dow Jones': '^DJI',
        'Russell 2000': '^RUT'
    }
    
    # Major tech stocks
    tech_stocks = {
        'Apple': 'AAPL',
        'Microsoft': 'MSFT',
        'Google': 'GOOGL',
        'Amazon': 'AMZN',
        'Tesla': 'TSLA',
        'NVIDIA': 'NVDA',
        'Meta': 'META'
    }
    
    us_data = {}
    
    try:
        # Get indices
        for name, symbol in indices.items():
            stock = yf.Ticker(symbol)
            hist = stock.history(period='1d')
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev_close = stock.info.get('previousClose', current)
                change = ((current - prev_close) / prev_close) * 100
                
                us_data[name] = {
                    'symbol': symbol,
                    'price': round(current, 2),
                    'change': round(change, 2),
                    'volume': hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
                }
        
        # Get tech stocks
        for name, symbol in tech_stocks.items():
            stock = yf.Ticker(symbol)
            hist = stock.history(period='1d')
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev_close = stock.info.get('previousClose', current)
                change = ((current - prev_close) / prev_close) * 100
                
                us_data[name] = {
                    'symbol': symbol,
                    'price': round(current, 2),
                    'change': round(change, 2),
                    'volume': hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
                }
        
        return us_data
        
    except Exception as e:
        print(f"Error fetching US data: {e}")
        return {}

def get_hk_stocks():
    """Fetch Hong Kong market data"""
    print("🇭🇰 FETCHING HONG KONG MARKET DATA...")
    
    hk_stocks = {
        'HSI': '^HSI',  # Hang Seng Index
        'Tencent': '0700.HK',
        'Alibaba': '9988.HK',
        'Meituan': '3690.HK',
        'JD.com': '9618.HK',
        'Xiaomi': '1810.HK'
    }
    
    hk_data = {}
    
    try:
        for name, symbol in hk_stocks.items():
            stock = yf.Ticker(symbol)
            hist = stock.history(period='1d')
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev_close = stock.info.get('previousClose', current)
                change = ((current - prev_close) / prev_close) * 100 if prev_close else 0
                
                hk_data[name] = {
                    'symbol': symbol,
                    'price': round(current, 2),
                    'change': round(change, 2),
                    'volume': hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
                }
        
        return hk_data
        
    except Exception as e:
        print(f"Error fetching HK data: {e}")
        return {}

def get_a_shares():
    """Fetch China A-share market data"""
    print("🇨🇳 FETCHING A-SHARE MARKET DATA...")
    
    # Note: yfinance has limited A-share data. Using some available symbols
    a_shares = {
        'SSE Composite': '000001.SS',  # Shanghai Composite
        'SZSE Component': '399001.SZ',  # Shenzhen Component
        'CSI 300': '000300.SS',  # CSI 300 Index
        'Kweichow Moutai': '600519.SS',
        'Industrial Bank': '601166.SS',
        'Ping An Insurance': '601318.SS'
    }
    
    a_data = {}
    
    try:
        for name, symbol in a_shares.items():
            stock = yf.Ticker(symbol)
            hist = stock.history(period='1d')
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev_close = stock.info.get('previousClose', current)
                change = ((current - prev_close) / prev_close) * 100 if prev_close else 0
                
                a_data[name] = {
                    'symbol': symbol,
                    'price': round(current, 2),
                    'change': round(change, 2),
                    'volume': hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
                }
        
        return a_data
        
    except Exception as e:
        print(f"Error fetching A-share data: {e}")
        return {}

def analyze_market(us_data, hk_data, a_data):
    """Analyze market trends and provide insights"""
    print("\n" + "=" * 80)
    print("MARKET ANALYSIS & INSIGHTS")
    print("=" * 80)
    
    insights = []
    
    # US Market Analysis
    if us_data:
        us_gainers = [(k, v) for k, v in us_data.items() if v['change'] > 0]
        us_losers = [(k, v) for k, v in us_data.items() if v['change'] < 0]
        
        if us_gainers:
            top_gainer = max(us_gainers, key=lambda x: x[1]['change'])
            insights.append(f"📈 US Top Gainer: {top_gainer[0]} (+{top_gainer[1]['change']}%)")
        
        if us_losers:
            top_loser = min(us_losers, key=lambda x: x[1]['change'])
            insights.append(f"📉 US Top Loser: {top_loser[0]} ({top_loser[1]['change']}%)")
    
    # HK Market Analysis
    if hk_data:
        hk_gainers = [(k, v) for k, v in hk_data.items() if v['change'] > 0]
        hk_losers = [(k, v) for k, v in hk_data.items() if v['change'] < 0]
        
        if hk_gainers:
            top_gainer = max(hk_gainers, key=lambda x: x[1]['change'])
            insights.append(f"🇭🇰 HK Top Gainer: {top_gainer[0]} (+{top_gainer[1]['change']}%)")
    
    # A-Share Analysis
    if a_data:
        a_gainers = [(k, v) for k, v in a_data.items() if v['change'] > 0]
        a_losers = [(k, v) for k, v in a_data.items() if v['change'] < 0]
        
        if a_gainers:
            top_gainer = max(a_gainers, key=lambda x: x[1]['change'])
            insights.append(f"🇨🇳 A-Share Top Gainer: {top_gainer[0]} (+{top_gainer[1]['change']}%)")
    
    # Overall Market Sentiment
    all_data = list(us_data.values()) + list(hk_data.values()) + list(a_data.values())
    if all_data:
        positive = sum(1 for d in all_data if d.get('change', 0) > 0)
        negative = sum(1 for d in all_data if d.get('change', 0) < 0)
        total = len(all_data)
        
        sentiment = "🟢 BULLISH" if positive > negative else "🔴 BEARISH" if negative > positive else "🟡 NEUTRAL"
        insights.append(f"\n📊 MARKET SENTIMENT: {sentiment}")
        insights.append(f"   Positive: {positive}/{total} | Negative: {negative}/{total}")
    
    return insights

def display_data(us_data, hk_data, a_data, insights):
    """Display formatted market data"""
    
    print("\n" + "=" * 80)
    print("LATEST MARKET DATA")
    print("=" * 80)
    
    # US Market
    if us_data:
        print("\n🇺🇸 US MARKET:")
        print("-" * 40)
        for name, data in us_data.items():
            change_color = "🟢" if data['change'] > 0 else "🔴" if data['change'] < 0 else "🟡"
            print(f"{change_color} {name:20} ${data['price']:10.2f} {data['change']:7.2f}%")
    
    # HK Market
    if hk_data:
        print("\n🇭🇰 HONG KONG MARKET:")
        print("-" * 40)
        for name, data in hk_data.items():
            change_color = "🟢" if data['change'] > 0 else "🔴" if data['change'] < 0 else "🟡"
            print(f"{change_color} {name:20} HK${data['price']:9.2f} {data['change']:7.2f}%")
    
    # A-Shares
    if a_data:
        print("\n🇨🇳 A-SHARES:")
        print("-" * 40)
        for name, data in a_data.items():
            change_color = "🟢" if data['change'] > 0 else "🔴" if data['change'] < 0 else "🟡"
            print(f"{change_color} {name:20} ¥{data['price']:10.2f} {data['change']:7.2f}%")
    
    # Insights
    if insights:
        print("\n" + "=" * 80)
        print("ANALYSIS & INSIGHTS")
        print("=" * 80)
        for insight in insights:
            print(insight)
    
    # Trading Hours Info
    print("\n" + "=" * 80)
    print("TRADING HOURS INFO")
    print("=" * 80)
    now = datetime.now()
    print(f"Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')} (GMT+8)")
    print("\nMarket Hours:")
    print("• US: 9:30 AM - 4:00 PM EST (10:30 PM - 5:00 AM GMT+8)")
    print("• HK: 9:30 AM - 4:00 PM HKT (9:30 AM - 4:00 PM GMT+8)")
    print("• A-Shares: 9:30 AM - 3:00 PM CST (9:30 AM - 3:00 PM GMT+8)")
    
    # Data freshness
    print(f"\n📅 Data as of: {now.strftime('%Y-%m-%d')}")
    print("⚠️ Note: Data may be delayed by 15-20 minutes")

def save_to_csv(us_data, hk_data, a_data):
    """Save data to CSV file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"market_data_{timestamp}.csv"
    
    all_data = []
    for market, data in [("US", us_data), ("HK", hk_data), ("A", a_data)]:
        for name, values in data.items():
            all_data.append({
                'Market': market,
                'Name': name,
                'Symbol': values['symbol'],
                'Price': values['price'],
                'Change %': values['change'],
                'Volume': values.get('volume', 0)
            })
    
    if all_data:
        df = pd.DataFrame(all_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 Data saved to: {filename}")
        return filename
    return None

def main():
    """Main function"""
    print("Starting market data collection...")
    
    # Fetch data
    us_data = get_us_stocks()
    hk_data = get_hk_stocks()
    a_data = get_a_shares()
    
    # Analyze
    insights = analyze_market(us_data, hk_data, a_data)
    
    # Display
    display_data(us_data, hk_data, a_data, insights)
    
    # Save to CSV
    csv_file = save_to_csv(us_data, hk_data, a_data)
    
    print("\n" + "=" * 80)
    print("DATA COLLECTION COMPLETE")
    print("=" * 80)
    
    if csv_file:
        print(f"📁 Data file: {csv_file}")
    
    return us_data, hk_data, a_data, csv_file

if __name__ == "__main__":
    try:
        us_data, hk_data, a_data, csv_file = main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()