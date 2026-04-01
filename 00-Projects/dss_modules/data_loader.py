"""数据获取模块 - 多数据源版本（修复版）"""
import os
import json
import time
import signal
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# 缓存目录
CACHE_DIR = "/home/kyj/.openclaw/workspace/data_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ============ API Keys (环境变量) ============
# ⚠️ 安全提示：API Key 应通过环境变量配置
# 使用方式：export FRED_API_KEY=your_key
FRED_KEY = os.environ.get("FRED_API_KEY", "")
AV_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
FMP_KEY = os.environ.get("FMP_API_KEY", "")

# 验证必要的 Key
if not FRED_KEY or not AV_KEY:
    print("⚠️  警告：缺少 API Key，部分功能不可用")
    print("   请设置环境变量：FRED_API_KEY, ALPHA_VANTAGE_API_KEY, FMP_API_KEY")

# 股票池
US_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'JNJ', 'WMT', 'PG']
CN_STOCKS = ['sh.600519', 'sh.601318', 'sz.000858', 'sz.000001']

# ============ Baostock 全局登录管理 ============
_BS_LOGGED_IN = False
_BS_LOGIN_TIME = None

def _ensure_baostock_login() -> bool:
    """确保 Baostock 已登录（全局单例，30 分钟自动重连）"""
    global _BS_LOGGED_IN, _BS_LOGIN_TIME
    
    import baostock as bs
    
    # 已登录且未超时（30 分钟自动重连）
    if _BS_LOGGED_IN and _BS_LOGIN_TIME:
        elapsed = (datetime.now() - _BS_LOGIN_TIME).total_seconds()
        if elapsed < 1800:  # 30 分钟
            return True
    
    # 登录
    try:
        lg = bs.login()
        if lg.error_code != '0':
            print(f"[!] Baostock 登录失败：{lg.error_msg}")
            _BS_LOGGED_IN = False
            return False
        _BS_LOGGED_IN = True
        _BS_LOGIN_TIME = datetime.now()
        print("[✓] Baostock 已登录")
        return True
    except Exception as e:
        print(f"[!] Baostock 登录异常：{e}")
        _BS_LOGGED_IN = False
        return False

# ============ Alpha Vantage ============
def fetch_alpha_vantage(symbol: str, full: bool = False) -> Optional[pd.DataFrame]:
    """Alpha Vantage 获取美股数据"""
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

# ============ Alpha Vantage 基本面数据 ============
def fetch_av_fundamentals(symbol: str) -> Optional[Dict]:
    """Alpha Vantage 获取基本面数据 (OVERVIEW)"""
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={AV_KEY}"
    try:
        r = requests.get(url, timeout=15)
        data = r.json()
        if 'Note' in data or 'Information' in data:
            print(f"[!] AV rate limited for fundamentals")
            return None
        if data.get('Symbol'):
            return data
        return None
    except Exception as e:
        print(f"[!] AV fundamentals error: {e}")
        return None

# ============ FMP 基本面数据 (已弃用) ============
def fetch_fmp_fundamentals(symbol: str) -> Optional[Dict]:
    """FMP 获取基本面数据 - 已弃用，Legacy endpoint 不再支持"""
    return None

def fetch_fmp_indicator(indicator: str = "gdp") -> Optional[pd.DataFrame]:
    """FMP 获取宏观经济指标"""
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
    """FRED 获取宏观数据"""
    if start is None:
        start = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if end is None:
        end = datetime.now().strftime('%Y-%m-%d')
    
    url = f"https://api.stlouisfed.org/observations?series_id={series_id}&api_key={FRED_KEY}&observation_start={start}&observation_end={end}"
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

# ============ Baostock A 股（修复版） ============
def fetch_baostock(code: str = "sh.600519", days: int = 250, timeout_sec: int = 15) -> Optional[pd.DataFrame]:
    """Baostock 获取 A 股数据 - 修复版（全局登录 + 超时保护）"""
    # 确保登录
    if not _ensure_baostock_login():
        return None
    
    import baostock as bs
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Baostock 请求超时 ({timeout_sec}秒)")
    
    try:
        # 设置超时
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_sec)
        
        rs = bs.query_history_k_data_plus(
            code, "date,open,high,low,close,volume",
            start_date=(datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d'),
            frequency="d"
        )
        
        data_list = []
        while (rs.error_code == '0') and rs.next():
            data_list.append(rs.get_row_data())
        
        # 取消超时
        signal.alarm(0)
        
        if not data_list:
            return None
            
        df = pd.DataFrame(data_list, columns=['date','open','high','low','close','volume'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.columns = [c.capitalize() for c in df.columns]
        return df.dropna().tail(days)
    
    except TimeoutError as e:
        print(f"[!] {e} - 代码：{code}")
        return None
    except Exception as e:
        print(f"[!] Baostock 错误 [{code}]: {e}")
        return None

# ============ 统一接口 ============
# 缓存 TTL（秒）
CACHE_TTL_SECONDS = 86400  # 24 小时

def get_stock_data(symbol: str, days: int = 100, source: str = "auto", force_refresh: bool = False) -> Optional[pd.DataFrame]:
    """获取股票数据（带 TTL 缓存）
    
    Args:
        symbol: 股票代码
        days: 需要的天数
        source: 数据源 ('auto', 'av', 'baostock')
        force_refresh: 是否强制刷新缓存
    
    Returns:
        股票数据 DataFrame 或 None
    """
    # 尝试缓存（A 股也缓存）
    cache_file = f"{CACHE_DIR}/{symbol.replace('.', '_')}.parquet"
    cache_meta_file = f"{CACHE_DIR}/{symbol.replace('.', '_')}_meta.json"
    
    # ✅ 检查缓存是否存在且未过期（TTL 机制）
    if not force_refresh and os.path.exists(cache_file):
        # 检查 TTL
        cache_valid = True
        if os.path.exists(cache_meta_file):
            try:
                with open(cache_meta_file, 'r') as f:
                    meta = json.load(f)
                cached_at = meta.get('cached_at', 0)
                age_seconds = time.time() - cached_at
                if age_seconds > CACHE_TTL_SECONDS:
                    cache_valid = False
                    print(f"[\u26a0\ufe0f] 缓存过期：{symbol} ({age_seconds/3600:.1f}h > 24h)")
            except:
                pass
        
        if cache_valid:
            df = pd.read_parquet(cache_file)
            if len(df) >= days:
                return df.tail(days)
    
    # 获取数据
    df = None
    if source == "auto" or source == "av":
        df = fetch_alpha_vantage(symbol)
    elif source == "baostock":
        df = fetch_baostock(symbol, days)
    
    # 缓存（带时间戳）
    if df is not None and len(df) > 0:
        df.to_parquet(cache_file)
        # ✅ 保存缓存元数据
        with open(cache_meta_file, 'w') as f:
            json.dump({
                'symbol': symbol,
                'cached_at': time.time(),
                'rows': len(df),
                'source': source
            }, f)
        print(f"[\u2713] Cached {symbol}: {len(df)} days")
    
    return df

def get_fundamentals(symbol: str) -> Optional[Dict]:
    """获取基本面数据"""
    cache_file = f"{CACHE_DIR}/{symbol}_fund.json"
    
    # 检查缓存
    if os.path.exists(cache_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if (datetime.now() - mtime).days < 7:  # 7 天缓存
            with open(cache_file, 'r') as f:
                return json.load(f)
    
    # 获取
    data = fetch_av_fundamentals(symbol)
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
        time.sleep(12)  # AV 免费版 5 次/分钟
    
    return results

# ============ 主函数 ============
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "update":
            update_all_stocks()
        elif cmd == "update-full":
            update_all_stocks(full=True)
        elif cmd == "fundamentals":
            for symbol in US_STOCKS[:5]:
                get_fundamentals(symbol)
        elif cmd == "macro":
            for ind in ["GDP", "UNRATE", "CPI"]:
                get_macro(ind)
        else:
            print("Usage: python data_loader.py [update|update-full|fundamentals|macro]")
    else:
        print("=== DSS Data Cache Status ===")
        files = sorted(os.listdir(CACHE_DIR))
        for f in files:
            if f.endswith('.parquet'):
                df = pd.read_parquet(f"{CACHE_DIR}/{f}")
                print(f"  {f}: {len(df)} days")
