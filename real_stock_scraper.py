#!/usr/bin/env python3
"""
Real Stock Market Data Fetcher
Using Alpha Vantage API with your key
"""

import requests
import json
from datetime import datetime
import time

print("=" * 80)
print("REAL STOCK MARKET DATA FETCHER")
print(f"Using Alpha Vantage API")
print("=" * 80)
print()

# Your Alpha Vantage API key
API_KEY = "MXAYBEBGFHR6PHYW"

def test_api_key():
    """Test if API key is working"""
    print("🔑 TESTING API KEY...")
    
    test_symbol = "AAPL"
    url = "https://www.alphavantage.co/query"
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': test_symbol,
        'apikey': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'Global Quote' in data:
            quote = data['Global Quote']
            price = quote.get('05. price', 'N/A')
            print(f"✅ API Key is WORKING!")
            print(f"   Test symbol: {test_symbol}")
            print(f"   Current price: ${price}")
            return True
        elif 'Note' in data:
            print(f"⚠️ API Note: {data['Note']}")
            print("   (Free tier: 5 calls/minute, 500 calls/day)")
            return True
        elif 'Error Message' in data:
            print(f"❌ API Error: {data['Error Message']}")
            return False
        else:
            print(f"⚠️ Unexpected response: {data}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def get_stock_quote(symbol):
    """Get real-time quote for a stock"""
    url = "https://www.alphavantage.co/query"
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'Global Quote' in data:
            quote = data['Global Quote']
            return {
                'symbol': symbol,
                'price': float(quote.get('05. price', 0)),
                'change': float(quote.get('10. change percent', '0%').replace('%', '')),
                'volume': int(quote.get('06. volume', 0)),
                'timestamp': quote.get('07. latest trading day', '')
            }
        elif 'Note' in data:
            print(f"   Rate limit note for {symbol}: {data['Note'][:50]}...")
            return None
        else:
            return None
            
    except Exception as e:
        print(f"   Error fetching {symbol}: {e}")
        return None

def get_us_market_data():
    """Get US market data"""
    print("\n📈 FETCHING US MARKET DATA...")
    
    us_stocks = [
        ('S&P 500 ETF', 'SPY'),
        ('NASDAQ ETF', 'QQQ'),
        ('Apple', 'AAPL'),
        ('Microsoft', 'MSFT'),
        ('NVIDIA', 'NVDA'),
        ('Tesla', 'TSLA'),
        ('Google', 'GOOGL'),
        ('Amazon', 'AMZN')
    ]
    
    us_data = {}
    
    for name, symbol in us_stocks:
        print(f"   Fetching {name} ({symbol})...")
        quote = get_stock_quote(symbol)
        if quote:
            us_data[name] = quote
        time.sleep(12)  # Free tier: 5 calls per minute = 12 seconds between calls
    
    return us_data

def get_intraday_data(symbol, interval='5min'):
    """Get intraday data (limited by free tier)"""
    url = "https://www.alphavantage.co/query"
    params = {
        'function': 'TIME_SERIES_INTRADAY',
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'outputsize': 'compact'  # 'compact' (latest 100) or 'full'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if f'Time Series ({interval})' in data:
            time_series = data[f'Time Series ({interval})']
            # Get latest data point
            latest_time = sorted(time_series.keys())[-1]
            latest_data = time_series[latest_time]
            
            return {
                'timestamp': latest_time,
                'open': float(latest_data['1. open']),
                'high': float(latest_data['2. high']),
                'low': float(latest_data['3. low']),
                'close': float(latest_data['4. close']),
                'volume': int(latest_data['5. volume'])
            }
        else:
            return None
            
    except Exception as e:
        print(f"Error fetching intraday data: {e}")
        return None

def get_market_status():
    """Check if markets are open"""
    print("\n🕒 CHECKING MARKET HOURS...")
    
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    
    # US Market (EST = GMT-5, Beijing = GMT+8, so 13.5 hours difference)
    # US opens 9:30 EST = 22:30 Beijing
    # US closes 16:00 EST = 05:00 Beijing (next day)
    
    us_open = False
    if (current_hour == 22 and current_minute >= 30) or \
       (current_hour > 22 and current_hour < 29) or \
       (current_hour == 5 and current_minute == 0):
        us_open = True
    
    # HK Market (same timezone as Beijing)
    # Opens 9:30, closes 16:00
    hk_open = False
    if 9 <= current_hour < 16:
        hk_open = True
    
    # A-Share Market
    # Opens 9:30, closes 15:00
    a_open = False
    if 9 <= current_hour < 15:
        a_open = True
    
    return {
        'US': us_open,
        'HK': hk_open,
        'A': a_open,
        'current_time': now.strftime("%Y-%m-%d %H:%M:%S")
    }

def display_results(us_data, market_status):
    """Display formatted results"""
    
    print("\n" + "=" * 80)
    print("REAL-TIME MARKET DATA")
    print("=" * 80)
    print(f"Current Time: {market_status['current_time']} (GMT+8)")
    print()
    
    print("📊 MARKET STATUS:")
    print(f"   US Market: {'🟢 OPEN' if market_status['US'] else '🔴 CLOSED'}")
    print(f"   HK Market: {'🟢 OPEN' if market_status['HK'] else '🔴 CLOSED'}")
    print(f"   A-Shares:  {'🟢 OPEN' if market_status['A'] else '🔴 CLOSED'}")
    
    if us_data:
        print("\n🇺🇸 US STOCKS:")
        print("-" * 40)
        
        # Sort by change percentage
        sorted_stocks = sorted(us_data.items(), 
                             key=lambda x: x[1]['change'] if x[1] else -1000, 
                             reverse=True)
        
        for name, data in sorted_stocks:
            if data:
                change = data['change']
                change_icon = "🟢" if change > 0 else "🔴" if change < 0 else "🟡"
                change_sign = "+" if change > 0 else ""
                print(f"{change_icon} {name:15} ${data['price']:10.2f} {change_sign}{change:6.2f}%")
    
    # Analysis
    print("\n🔍 QUICK ANALYSIS:")
    print("-" * 40)
    
    if us_data:
        gainers = [(n, d) for n, d in us_data.items() if d and d['change'] > 0]
        losers = [(n, d) for n, d in us_data.items() if d and d['change'] < 0]
        
        if gainers:
            top_gainer = max(gainers, key=lambda x: x[1]['change'])
            print(f"📈 Top Gainer: {top_gainer[0]} (+{top_gainer[1]['change']:.2f}%)")
        
        if losers:
            top_loser = min(losers, key=lambda x: x[1]['change'])
            print(f"📉 Top Loser: {top_loser[0]} ({top_loser[1]['change']:.2f}%)")
        
        total = len([d for d in us_data.values() if d])
        positive = len(gainers)
        negative = len(losers)
        
        print(f"\n📊 Sentiment: {positive}/{total} positive, {negative}/{total} negative")
        
        if positive > negative:
            print("   Overall: 🟢 BULLISH")
        elif negative > positive:
            print("   Overall: 🔴 BEARISH")
        else:
            print("   Overall: 🟡 NEUTRAL")

def save_to_file(us_data, market_status):
    """Save data to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"real_market_data_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("REAL MARKET DATA REPORT\n")
        f.write(f"Generated: {market_status['current_time']}\n")
        f.write(f"API Key: {API_KEY[:8]}...\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("MARKET STATUS:\n")
        f.write(f"  US: {'OPEN' if market_status['US'] else 'CLOSED'}\n")
        f.write(f"  HK: {'OPEN' if market_status['HK'] else 'CLOSED'}\n")
        f.write(f"  A:  {'OPEN' if market_status['A'] else 'CLOSED'}\n\n")
        
        if us_data:
            f.write("US STOCK DATA:\n")
            f.write("-" * 40 + "\n")
            for name, data in us_data.items():
                if data:
                    f.write(f"{name:15} ${data['price']:10.2f} {data['change']:7.2f}%\n")
    
    print(f"\n💾 Data saved to: {filename}")
    return filename

def main():
    """Main function"""
    
    print(f"API Key: {API_KEY}")
    print()
    
    # Test API key
    if not test_api_key():
        print("\n❌ API key test failed. Please check your key.")
        return
    
    # Check market hours
    market_status = get_market_status()
    
    # Get US market data
    us_data = get_us_market_data()
    
    # Display results
    display_results(us_data, market_status)
    
    # Save to file
    report_file = save_to_file(us_data, market_status)
    
    print("\n" + "=" * 80)
    print("NEXT STEPS & RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n🎯 FOR YOUR API KEY:")
    print(f"   Key: {API_KEY}")
    print("   Rate limit: 5 calls per minute, 500 calls per day")
    print("   Best for: US stocks, real-time quotes")
    
    print("\n📈 TO EXPAND THIS SYSTEM:")
    print("1. Add more US stocks (prioritize important ones)")
    print("2. Implement caching to reduce API calls")
    print("3. Add error handling for rate limits")
    print("4. Schedule updates during market hours")
    print("5. Add simple technical indicators")
    
    print("\n🇭🇰 FOR HK MARKET DATA:")
    print("   Alpha Vantage supports some HK stocks (e.g., 0700.HK)")
    print("   Format: Use '.HK' suffix for Hong Kong stocks")
    
    print("\n🇨🇳 FOR A-SHARE DATA:")
    print("   Alpha Vantage has LIMITED China A-share data")
    print("   Consider: yfinance library or Chinese financial APIs")
    
    print("\n🚀 READY FOR REAL DATA ANALYSIS!")
    print(f"   Report saved: {report_file}")
    print("   Modify code to add your preferred stocks")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()