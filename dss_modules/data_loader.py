"""数据获取模块 - 多数据源版本"""
import os
import json
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# 缓存目录
CACHE_DIR = "/home/kyj/.openclaw/workspace/data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ============ API Keys ============
FRED_KEY = "c917a48f98933615e6a208e7474b810c"
AV_KEY = "BBQTETM9CS8X8LI8"
FMP_KEY = "oJw67iSq4FuJTIArmUKI9l3e3qZmNZod"

# 股票池
US_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'JNJ', 'WMT', 'PG']
CN_STOCKS = ['sh.600519', 'sh.601318', 'sz.000858', 'sz.000001']

# ============ Alpha Vantage ============
def fetch_alpha_vantage(symbol: str, full: bool = False) -> Optional[pd.DataFrame]:
    """Alpha Vantage获取美股数据"""
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize={'full' if full else 'compact'}&apikey={AV_KEY}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if 'Note' in data or 'Information' in data:
            print(f"[!] AV rate limited")
            return None
            
        ts = data.get("Time Series (Daily)", {})
        if not ts:
            return None
            
        df = pd.DataFrame.from_dict(ts, orient='index')
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df.dropna()
    except Exception as e:
        print(f"[!] AV error: {e}")
        return None

# ============ FMP 基本面数据 ============
def fetch_fmp_fundamentals(symbol: str) -> Optional[Dict]:
    """FMP获取基本面数据"""
    url = f"https://financialmodelingprep.com/api/v3/ratios/{symbol}?apikey={FMP_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except:
        return None

def fetch_fmp_indicator(indicator: str = "gdp") -> Optional[pd.DataFrame]:
    """FMP获取宏观经济指标"""
    url = f"https://financialmodelingprep.com/api/v3/{indicator}?apikey={FMP_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list):
            df = pd.DataFrame(data)
            return df
        return None
    except:
        return None

# ============ FRED 宏观数据 ============
def fetch_fred(series_id: str = "GDP", start: str = None, end: str = None) -> Optional[pd.DataFrame]:
    """FRED获取宏观数据"""
    if start is None:
        start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if end is None:
        end = datetime.now().strftime('%Y-%m-%d')
    
    url = f"https://api.stlouisfed.org/observations?series_id={series_id}&api_key={FRED_KEY}&observation_start={start/fred/series}&observation_end={end}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        obs = data.get('observations', [])
        if obs:
            df = pd.DataFrame(obs)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            return df
        return None
    except:
        return None

# ============ Baostock A股 ============
def fetch_baostock(code: str = "sh.600519", days: int = 250) -> Optional[pd.DataFrame]:
    """Baostock获取A股数据"""
    try:
        import baostock as bs
        lg = bs.login()
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume",
            start_date=(datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d'),
            frequency="d"
        )
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())
        bs.logout()
        
        if not data_list:
            return None
            
        df = pd.DataFrame(data_list, columns=['date','open','high','low','close','volume'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.columns = [c.capitalize() for c in df.columns]
        return df.dropna().tail(days)
    except:
        return None

# ============ 统一接口 ============
def get_stock_data(symbol: str, days: int = 100, source: str = "auto") -> Optional[pd.DataFrame]:
    """获取股票数据"""
    # 尝试缓存
    cache_file = f"{CACHE_DIR}/{symbol.replace('.', '_')}_av.parquet"
    if os.path.exists(cache_file):
        df = pd.read_parquet(cache_file)
        if len(df) >= days:
            return df.tail(days)
    
    # 获取数据
    df = None
    if source == "auto" or source == "av":
        df = fetch_alpha_vantage(symbol)
    elif source == "baostock":
        df = fetch_baostock(symbol, days)
    
    # 缓存
    if df is not None and len(df) > 0:
        cache_file = f"{CACHE_DIR}/{symbol.replace('.', '_')}_av.parquet"
        df.to_parquet(cache_file)
        print(f"[✓] Cached {symbol}: {len(df)} days")
    
    return df

def get_fundamentals(symbol: str) -> Optional[Dict]:
    """获取基本面数据"""
    cache_file = f"{CACHE_DIR}/{symbol}_fund.json"
    
    # 检查缓存
    if os.path.exists(cache_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if (datetime.now() - mtime).days < 7:  # 7天缓存
            with open(cache_file, 'r') as f:
                return json.load(f)
    
    # 获取
    data = fetch_fmp_fundamentals(symbol)
    if data:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
        print(f"[✓] Cached fundamentals for {symbol}")
    return data

def get_macro(indicator: str = "gdp") -> Optional[pd.DataFrame]:
    """获取宏观数据"""
    cache_file = f"{CACHE_DIR}/macro_{indicator}.parquet"
    
    if os.path.exists(cache_file):
        df = pd.read_parquet(cache_file)
        if (datetime.now() - df.index[-1]).days < 30:
            return df
    
    df = fetch_fred(indicator.upper())
    if df is not None:
        df.to_parquet(cache_file)
        print(f"[✓] Cached macro {indicator}")
    return df

# ============ 批量更新 ============
def update_all_stocks(stocks: List[str] = None, full: bool = False) -> Dict[str, int]:
    """批量更新所有股票数据"""
    if stocks is None:
        stocks = US_STOCKS
    
    results = {'success': 0, 'failed': 0, 'cached': 0}
    
    for symbol in stocks:
        # 检查是否已缓存且够用
        cache_file = f"{CACHE_DIR}/{symbol}_av.parquet"
        if os.path.exists(cache_file):
            df = pd.read_parquet(cache_file)
            if len(df) >= 100 and not full:
                print(f"[=] {symbol} cached ({len(df)} days)")
                results['cached'] += 1
                continue
        
        # 获取
        print(f"[>] {symbol}...")
        df = fetch_alpha_vantage(symbol, full)
        
        if df is not None and len(df) > 0:
            df.to_parquet(cache_file)
            print(f"[✓] {symbol}: {len(df)} days")
            results['success'] += 1
        else:
            print(f"[✗] {symbol}: failed")
            results['failed'] += 1
        
        # 避免超限
        time.sleep(12)  # AV免费版5次/分钟
    
    return results

# ============ 主函数 ============
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "update":
            # 更新所有股票
            update_all_stocks()
            
        elif cmd == "update-full":
            # 完整更新
            update_all_stocks(full=True)
            
        elif cmd == "fundamentals":
            # 获取基本面
            for symbol in US_STOCKS[:5]:
                get_fundamentals(symbol)
                
        elif cmd == "macro":
            # 获取宏观数据
            for ind in ["GDP", "UNRATE", "CPI"]:
                get_macro(ind)
        else:
            print("Usage: python data_loader.py [update|update-full|fundamentals|macro]")
    else:
        # 默认：显示状态
        print("=== DSS Data Cache Status ===")
        files = sorted(os.listdir(CACHE_DIR))
        for f in files:
            if f.endswith('.parquet'):
                df = pd.read_parquet(f"{CACHE_DIR}/{f}")
                print(f"  {f}: {len(df)} days")
