"""
真实基本面数据获取模块 v4
多数据源支持 + 重试机制 + 优雅降级
支持: 东方财富、新浪、同花顺(通过akshare)
"""
import requests
import time
import re
from typing import Optional, Dict, Any

# 尝试导入akshare作为备用数据源
try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

# 缓存机制
_cache: Dict[str, Dict[str, Any]] = {}
_cache_time: Dict[str, float] = {}
CACHE_TTL = 300  # 5分钟缓存


def _get_cached(key: str) -> Optional[Dict]:
    """获取缓存数据"""
    if key in _cache and key in _cache_time:
        if time.time() - _cache_time[key] < CACHE_TTL:
            return _cache[key]
    return None


def _set_cache(key: str, data: Dict):
    """设置缓存"""
    _cache[key] = data
    _cache_time[key] = time.time()


def _retry_request(url: str, params: dict = None, headers: dict = None, 
                   max_retries: int = 3, timeout: int = 10) -> Optional[requests.Response]:
    """带重试的HTTP请求"""
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if headers:
        default_headers.update(headers)
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=default_headers, timeout=timeout)
            if resp.status_code == 200:
                return resp
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # 指数退避: 2s, 4s, 6s
                time.sleep(wait_time)
            continue
    return None


def _get_from_eastmoney(symbol: str) -> Optional[Dict]:
    """从东方财富获取数据 (主要数据源)"""
    # 转换代码: sh.600519 -> 1.600519, sz.000333 -> 0.000333
    if symbol.startswith('sh'):
        secid = f"1.{symbol.replace('sh.', '')}"
    elif symbol.startswith('sz'):
        secid = f"0.{symbol.replace('sz.', '')}"
    else:
        return None
    
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fltt": "2",
        "fields": "f43,f58,f162,f167,f170,f135,f136",
        "secid": secid,
    }
    
    resp = _retry_request(url, params=params)
    if resp:
        try:
            data = resp.json()
            if data.get('data'):
                f = data['data']
                return {
                    'name': f.get('f58', ''),
                    'code': symbol,
                    'close': f.get('f43', 0) / 100 if f.get('f43') else None,
                    'pe': f.get('f162', 0) / 100 if f.get('f162') else None,
                    'pb': f.get('f167', 0) / 100 if f.get('f167') else None,
                    'change_pct': f.get('f170', 0) / 100 if f.get('f170') else None,
                    'source': 'eastmoney'
                }
        except Exception:
            pass
    return None


def _get_from_sina(symbol: str) -> Optional[Dict]:
    """从新浪获取价格数据"""
    # 转换代码: sh.600519 -> sh600519
    if symbol.startswith('sh.'):
        sina_code = f"sh{symbol.replace('sh.', '')}"
    elif symbol.startswith('sz.'):
        sina_code = f"sz{symbol.replace('sz.', '')}"
    else:
        return None
    
    url = f"https://hq.sinajs.cn/list={sina_code}"
    headers = {'Referer': 'https://finance.sina.com.cn'}
    
    resp = _retry_request(url, headers=headers)
    if resp:
        try:
            match = re.search(r'"([^"]+)"', resp.text)
            if match:
                data = match.group(1).split(',')
                if len(data) >= 6:
                    return {
                        'name': data[0],
                        'code': symbol,
                        'open': float(data[1]) if data[1] else None,
                        'last_close': float(data[2]) if data[2] else None,
                        'close': float(data[3]) if data[3] else None,
                        'high': float(data[4]) if data[4] else None,
                        'low': float(data[5]) if data[5] else None,
                        'source': 'sina'
                    }
        except Exception:
            pass
    return None


def _get_financial_from_ths(code: str) -> Optional[Dict]:
    """从同花顺获取财务数据 (通过akshare)"""
    if not HAS_AKSHARE:
        return None
    
    try:
        df = ak.stock_financial_abstract(symbol=code)
        if df is None or df.empty:
            return None
        
        # 获取最新财务数据 (优先最近报告期)
        columns = [c for c in df.columns if c not in ['选项', '指标']]
        latest_col = columns[0] if columns else None  # 最新一期
        
        result = {}
        
        # EPS (每股收益)
        eps_row = df[df['指标'] == '基本每股收益']
        if not eps_row.empty and latest_col:
            val = eps_row[latest_col].values[0]
            result['eps'] = float(val) if val and str(val) != 'nan' else None
        
        # ROE (净资产收益率)
        roe_row = df[df['指标'] == '净资产收益率(ROE)']
        if not roe_row.empty and latest_col:
            val = roe_row[latest_col].values[0]
            result['roe'] = float(val) if val and str(val) != 'nan' else None
        
        # 每股净资产
        na_row = df[df['指标'] == '每股净资产']
        if not na_row.empty and latest_col:
            val = na_row[latest_col].values[0]
            result['net_assets_per_share'] = float(val) if val and str(val) != 'nan' else None
        
        # 毛利率
        gm_row = df[df['指标'] == '毛利率']
        if not gm_row.empty and latest_col:
            val = gm_row[latest_col].values[0]
            result['gross_margin'] = float(val) if val and str(val) != 'nan' else None
        
        result['source'] = 'ths'
        return result
        
    except Exception as e:
        print(f"同花顺数据获取失败 {code}: {e}")
        return None


def get_stock_realtime(symbol: str) -> Dict:
    """
    获取股票实时数据 (价格 + 基本面)
    
    Args:
        symbol: 股票代码，如 'sh.600519', 'sz.000333'
    
    Returns:
        Dict with keys: name, code, close, pe, pb, roe, change_pct, source
        失败时返回带有 error 字段的字典，不会返回 None
    """
    # 检查缓存
    cached = _get_cached(symbol)
    if cached:
        return cached
    
    result = {
        'name': '',
        'code': symbol,
        'close': None,
        'pe': None,
        'pb': None,
        'roe': None,
        'change_pct': None,
        'eps': None,
        'gross_margin': None,
        'source': 'none',
        'error': None
    }
    
    # 提取纯代码
    code = symbol.replace('sh.', '').replace('sz.', '')
    
    # 1. 尝试东方财富 (主要数据源)
    em_data = _get_from_eastmoney(symbol)
    if em_data:
        result.update(em_data)
        result['error'] = None  # 清除错误标记
        _set_cache(symbol, result)
        return result
    
    # 2. 东方财富失败，使用新浪 + 同花顺组合
    print(f"东方财富API不可用，切换到新浪+同花顺数据源: {symbol}")
    
    # 获取价格 (新浪)
    sina_data = _get_from_sina(symbol)
    if sina_data:
        result['name'] = sina_data['name']
        result['close'] = sina_data['close']
        result['open'] = sina_data.get('open')
        result['high'] = sina_data.get('high')
        result['low'] = sina_data.get('low')
        if sina_data.get('last_close') and sina_data.get('close'):
            result['change_pct'] = (sina_data['close'] - sina_data['last_close']) / sina_data['last_close'] * 100
        result['source'] = 'sina'
    
    # 获取财务数据 (同花顺)
    ths_data = _get_financial_from_ths(code)
    if ths_data:
        result['roe'] = ths_data.get('roe')
        result['eps'] = ths_data.get('eps')
        result['gross_margin'] = ths_data.get('gross_margin')
        
        # 计算PE和PB
        if result['close'] and result['eps'] and result['eps'] > 0:
            result['pe'] = result['close'] / result['eps']
        
        if result['close'] and ths_data.get('net_assets_per_share') and ths_data['net_assets_per_share'] > 0:
            result['pb'] = result['close'] / ths_data['net_assets_per_share']
        
        # 更新数据源
        if result['source'] == 'sina':
            result['source'] = 'sina+ths'
        else:
            result['source'] = 'ths'
    
    # 检查是否有有效数据
    if result['close'] is None:
        result['error'] = '无法获取价格数据'
    elif result['pe'] is None and result['roe'] is None:
        result['error'] = '价格数据正常，但基本面数据不可用'
    
    _set_cache(symbol, result)
    return result


def get_stocks_realtime(symbols: list) -> list:
    """
    批量获取股票数据
    
    Args:
        symbols: 股票代码列表，如 ['sh.600519', 'sz.000333']
    
    Returns:
        List of dicts
    """
    results = []
    for symbol in symbols:
        data = get_stock_realtime(symbol)
        results.append(data)
        time.sleep(0.1)  # 避免请求过快
    return results


if __name__ == "__main__":
    stocks = ['sh.600519', 'sz.000333', 'sh.601111', 'sh.600048', 'sz.002304', 'sz.300024']
    
    print("=== 真实基本面数据 v4 (多数据源) ===")
    print("=" * 70)
    
    for s in stocks:
        data = get_stock_realtime(s)
        if data.get('error'):
            print(f"{s}: {data['error']}")
        else:
            pe_str = f"{data['pe']:.1f}" if data.get('pe') else "N/A"
            pb_str = f"{data['pb']:.2f}" if data.get('pb') else "N/A"
            roe_str = f"{data['roe']:.1f}%" if data.get('roe') else "N/A"
            change_str = f"{data['change_pct']:+.2f}%" if data.get('change_pct') is not None else "N/A"
            source_str = f"[{data.get('source', '?')}]"
            
            print(f"{s} {data.get('name', 'Unknown'):8s} "
                  f"价:{data['close']:7.2f} PE:{pe_str:6s} PB:{pb_str:5s} "
                  f"ROE:{roe_str:6s} 涨跌:{change_str:7s} {source_str}")
        
        time.sleep(0.2)  # 避免请求过快