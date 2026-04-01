#!/usr/bin/env python3
"""
Quick Stock Check with Real API
"""

import requests
import json
from datetime import datetime

API_KEY = "MXAYBEBGFHR6PHYW"

print("=" * 80)
print("QUICK STOCK CHECK - REAL API TEST")
print("=" * 80)
print()

def get_quote(symbol):
    """Get single stock quote"""
    url = "https://www.alphavantage.co/query"
    params = {
        'function': 'GLOBAL_QUOTE',
        'symbol': symbol,
        'apikey': API_KEY
    }
    
    try:
        print(f"Fetching {symbol}...")
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'Global Quote' in data:
            quote = data['Global Quote']
            return {
                'symbol': symbol,
                'price': float(quote.get('05. price', 0)),
                'change': float(quote.get('10. change percent', '0%').replace('%', '')),
                'volume': int(quote.get('06. volume', 0))
            }
        elif 'Note' in data:
            print(f"   Note: {data['Note'][:60]}...")
            return None
        elif 'Error Message' in data:
            print(f"   Error: {data['Error Message']}")
            return None
        else:
            print(f"   Unexpected response")
            return None
            
    except Exception as e:
        print(f"   Error: {e}")
        return None

# Test with a few key stocks
stocks_to_check = [
    ('Apple', 'AAPL'),
    ('Tesla', 'TSLA'),
    ('NVIDIA', 'NVDA')
]

results = []

for name, symbol in stocks_to_check:
    data = get_quote(symbol)
    if data:
        results.append((name, data))
    # Small delay to avoid rate limit
    import time
    time.sleep(2)

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)

if results:
    for name, data in results:
        change = data['change']
        icon = "🟢" if change > 0 else "🔴" if change < 0 else "🟡"
        sign = "+" if change > 0 else ""
        print(f"{icon} {name:10} ${data['price']:8.2f} {sign}{change:6.2f}%")
    
    # Simple analysis
    print("\n📊 QUICK ANALYSIS:")
    gains = sum(1 for _, d in results if d['change'] > 0)
    losses = sum(1 for _, d in results if d['change'] < 0)
    print(f"   Gainers: {gains}, Losers: {losses}")
    
    if gains > losses:
        print("   Sentiment: 🟢 Positive")
    elif losses > gains:
        print("   Sentiment: 🔴 Negative")
    else:
        print("   Sentiment: 🟡 Neutral")
else:
    print("❌ No data retrieved. Possible issues:")
    print("   1. API key invalid")
    print("   2. Rate limit reached")
    print("   3. Network issues")

print("\n" + "=" * 80)
print("API STATUS")
print("=" * 80)
print(f"Key: {API_KEY}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Check market hours
now = datetime.now()
hour = now.hour
print(f"\n🕒 MARKET HOURS (Beijing Time):")
print(f"   US Market: 22:30 - 05:00 (next day)")
print(f"   Current: {hour:02d}:{now.minute:02d}")
print(f"   US Market is: {'🔴 CLOSED' if 5 <= hour < 22 else '🟢 OPEN'}")

print("\n🎯 NEXT:")
print("1. Try more stocks (MSFT, GOOGL, AMZN)")
print("2. Add HK stocks (e.g., 0700.HK for Tencent)")
print("3. Implement batch processing with delays")
print("4. Save data to database/file")