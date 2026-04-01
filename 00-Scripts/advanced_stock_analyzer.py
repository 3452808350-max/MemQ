#!/usr/bin/env python3
"""
Advanced Stock Market Analyzer
With real API integration options
"""

import requests
import json
from datetime import datetime, timedelta
import csv
import os

print("=" * 80)
print("ADVANCED STOCK MARKET ANALYZER")
print("=" * 80)
print()

class StockAnalyzer:
    def __init__(self):
        self.market_data = {
            'US': [],
            'HK': [], 
            'A': []
        }
        self.analysis_results = {}
        
    def fetch_with_alpha_vantage(self, symbol, api_key=None):
        """Fetch stock data using Alpha Vantage API"""
        if not api_key:
            return None
            
        try:
            # Alpha Vantage API endpoint
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'Global Quote' in data:
                quote = data['Global Quote']
                return {
                    'price': float(quote.get('05. price', 0)),
                    'change': float(quote.get('10. change percent', '0%').replace('%', '')),
                    'volume': int(quote.get('06. volume', 0))
                }
        except Exception as e:
            print(f"Alpha Vantage error for {symbol}: {e}")
        
        return None
    
    def fetch_with_yfinance(self, symbol):
        """Fetch using yfinance (would need library installed)"""
        # This is a placeholder - actual implementation needs yfinance
        print(f"[yfinance] Would fetch {symbol}")
        return None
    
    def fetch_chinese_stocks(self, symbol):
        """Fetch Chinese stock data"""
        # Chinese stocks are challenging - may need web scraping
        print(f"[Chinese API] Would fetch {symbol}")
        return None
    
    def get_predefined_watchlist(self):
        """Return predefined watchlist of important stocks"""
        return {
            'US': [
                {'name': 'S&P 500', 'symbol': 'SPY', 'type': 'index'},
                {'name': 'NASDAQ', 'symbol': 'QQQ', 'type': 'index'},
                {'name': 'Apple', 'symbol': 'AAPL', 'type': 'stock'},
                {'name': 'Microsoft', 'symbol': 'MSFT', 'type': 'stock'},
                {'name': 'NVIDIA', 'symbol': 'NVDA', 'type': 'stock'},
                {'name': 'Tesla', 'symbol': 'TSLA', 'type': 'stock'}
            ],
            'HK': [
                {'name': 'Hang Seng', 'symbol': '^HSI', 'type': 'index'},
                {'name': 'Tencent', 'symbol': '0700.HK', 'type': 'stock'},
                {'name': 'Alibaba', 'symbol': 'BABA', 'type': 'stock'},
                {'name': 'Meituan', 'symbol': 'MPNGF', 'type': 'stock'}
            ],
            'A': [
                {'name': 'SSE Composite', 'symbol': '000001.SS', 'type': 'index'},
                {'name': 'Kweichow Moutai', 'symbol': '600519.SS', 'type': 'stock'},
                {'name': 'Ping An Insurance', 'symbol': '601318.SS', 'type': 'stock'},
                {'name': 'Industrial Bank', 'symbol': '601166.SS', 'type': 'stock'}
            ]
        }
    
    def technical_analysis(self, stock_data):
        """Perform basic technical analysis"""
        if not stock_data or len(stock_data) < 2:
            return {}
        
        analysis = {}
        
        # Simple moving average (if we had historical data)
        # RSI calculation (if we had historical data)
        # Support/resistance levels
        
        return analysis
    
    def fundamental_analysis(self, stock_info):
        """Perform fundamental analysis"""
        analysis = {}
        
        # P/E ratio analysis
        # Dividend yield
        # Market cap
        # Revenue growth
        
        return analysis
    
    def market_sentiment_analysis(self):
        """Analyze overall market sentiment"""
        sentiment = {
            'US': 'neutral',
            'HK': 'neutral', 
            'A': 'neutral',
            'overall': 'neutral'
        }
        
        # Count gainers vs losers
        us_gainers = sum(1 for s in self.market_data['US'] if s.get('change', 0) > 0)
        us_total = len(self.market_data['US'])
        
        if us_total > 0:
            if us_gainers > us_total * 0.6:
                sentiment['US'] = 'bullish'
            elif us_gainers < us_total * 0.4:
                sentiment['US'] = 'bearish'
        
        return sentiment
    
    def generate_trading_signals(self):
        """Generate basic trading signals"""
        signals = []
        
        # Simple momentum signals
        for market in ['US', 'HK', 'A']:
            for stock in self.market_data[market]:
                if 'change' in stock and 'name' in stock:
                    change = stock['change']
                    if change > 2.0:  # Strong gain
                        signals.append(f"📈 STRONG BUY: {stock['name']} (+{change}%)")
                    elif change < -2.0:  # Strong loss
                        signals.append(f"📉 STRONG SELL: {stock['name']} ({change}%)")
                    elif change > 0.5:  # Moderate gain
                        signals.append(f"🟢 BUY: {stock['name']} (+{change}%)")
                    elif change < -0.5:  # Moderate loss
                        signals.append(f"🔴 SELL: {stock['name']} ({change}%)")
        
        return signals
    
    def save_analysis_report(self):
        """Save analysis to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"market_analysis_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("STOCK MARKET ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Market data
            for market in ['US', 'HK', 'A']:
                if self.market_data[market]:
                    f.write(f"\n{market} MARKET:\n")
                    f.write("-" * 40 + "\n")
                    for stock in self.market_data[market]:
                        if 'name' in stock and 'price' in stock:
                            change = stock.get('change', 0)
                            change_str = f"+{change}%" if change > 0 else f"{change}%"
                            f.write(f"{stock['name']:20} ${stock['price']:10.2f} {change_str:>8}\n")
            
            # Analysis
            sentiment = self.market_sentiment_analysis()
            f.write(f"\n\nMARKET SENTIMENT:\n")
            f.write(f"US: {sentiment['US']}\n")
            f.write(f"HK: {sentiment['HK']}\n")
            f.write(f"A-shares: {sentiment['A']}\n")
            f.write(f"Overall: {sentiment['overall']}\n")
            
            # Trading signals
            signals = self.generate_trading_signals()
            if signals:
                f.write("\n\nTRADING SIGNALS:\n")
                f.write("-" * 40 + "\n")
                for signal in signals:
                    f.write(f"{signal}\n")
        
        print(f"📄 Report saved to: {filename}")
        return filename
    
    def display_dashboard(self):
        """Display interactive dashboard"""
        print("\n" + "=" * 80)
        print("MARKET ANALYSIS DASHBOARD")
        print("=" * 80)
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Last Updated: {current_time}")
        print()
        
        # Market overview
        print("📊 MARKET OVERVIEW")
        print("-" * 40)
        
        watchlist = self.get_predefined_watchlist()
        for market in ['US', 'HK', 'A']:
            print(f"\n{market} Market:")
            for stock in watchlist[market]:
                print(f"  • {stock['name']} ({stock['symbol']})")
        
        # Analysis results
        print("\n🔍 ANALYSIS RESULTS")
        print("-" * 40)
        
        sentiment = self.market_sentiment_analysis()
        print(f"US Market Sentiment: {sentiment['US'].upper()}")
        print(f"HK Market Sentiment: {sentiment['HK'].upper()}")
        print(f"A-share Sentiment: {sentiment['A'].upper()}")
        
        # Trading signals
        signals = self.generate_trading_signals()
        if signals:
            print("\n🎯 TRADING SIGNALS")
            print("-" * 40)
            for signal in signals[:5]:  # Show top 5 signals
                print(signal)
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-" * 40)
        print("1. Monitor US tech stocks for momentum")
        print("2. Watch HK market for China policy impacts")
        print("3. Consider A-share volatility around policy announcements")
        print("4. Diversify across markets for risk management")
    
    def run_analysis(self):
        """Main analysis workflow"""
        print("Starting market analysis...")
        print()
        
        # Get watchlist
        watchlist = self.get_predefined_watchlist()
        
        # Simulate data collection (replace with real API calls)
        print("📡 COLLECTING MARKET DATA...")
        print("(Simulated data - replace with real API calls)")
        print()
        
        # Simulate US data
        self.market_data['US'] = [
            {'name': 'S&P 500', 'symbol': 'SPY', 'price': 4950.25, 'change': 0.45},
            {'name': 'NASDAQ', 'symbol': 'QQQ', 'price': 15680.35, 'change': 0.82},
            {'name': 'Apple', 'symbol': 'AAPL', 'price': 185.20, 'change': 1.20},
            {'name': 'NVIDIA', 'symbol': 'NVDA', 'price': 720.30, 'change': 2.35},
            {'name': 'Tesla', 'symbol': 'TSLA', 'price': 195.50, 'change': -0.85}
        ]
        
        # Simulate HK data
        self.market_data['HK'] = [
            {'name': 'Hang Seng', 'symbol': '^HSI', 'price': 16580.45, 'change': -0.35},
            {'name': 'Tencent', 'symbol': '0700.HK', 'price': 285.60, 'change': 0.45},
            {'name': 'Alibaba', 'symbol': 'BABA', 'price': 75.80, 'change': -1.20}
        ]
        
        # Simulate A-share data
        self.market_data['A'] = [
            {'name': 'SSE Composite', 'symbol': '000001.SS', 'price': 3050.25, 'change': 0.15},
            {'name': 'Kweichow Moutai', 'symbol': '600519.SS', 'price': 1650.80, 'change': 0.85},
            {'name': 'Ping An Insurance', 'symbol': '601318.SS', 'price': 42.35, 'change': -0.45}
        ]
        
        # Perform analysis
        print("🔍 ANALYZING MARKET TRENDS...")
        sentiment = self.market_sentiment_analysis()
        signals = self.generate_trading_signals()
        
        # Display results
        self.display_dashboard()
        
        # Save report
        report_file = self.save_analysis_report()
        
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"\n📁 Report saved: {report_file}")
        
        return {
            'market_data': self.market_data,
            'sentiment': sentiment,
            'signals': signals,
            'report_file': report_file
        }

def main():
    """Main function"""
    analyzer = StockAnalyzer()
    
    try:
        results = analyzer.run_analysis()
        
        print("\n🎯 NEXT STEPS FOR REAL IMPLEMENTATION:")
        print("1. Get Alpha Vantage API key (free)")
        print("2. Install yfinance: pip install yfinance")
        print("3. Replace simulated data with real API calls")
        print("4. Add more stocks to watchlist")
        print("5. Implement historical data analysis")
        print("6. Set up automated daily reports")
        
        print("\n🚀 Ready to build your professional market analysis system!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Analysis interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()