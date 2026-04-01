"""
贵金属数据获取模块
支持黄金、白银、铂金、钯金的实时行情和历史数据

数据源（按优先级）：
1. 东方财富网 (EastMoney): 上金所、上期所数据
2. 新浪财经 (Sina): 备用数据源
3. Yahoo Finance: 国际金价（需要yfinance库）
4. 模拟数据: 离线模式使用

使用示例:
    from precious_metals import get_gold_price, get_silver_price, calculate_gold_spread
    
    # 获取黄金价格
    gold = get_gold_price()
    print(f"Au99.99: {gold['au9999']}")
    print(f"伦敦金: {gold['london']}")
    
    # 计算内外价差
    spread = calculate_gold_spread()
    print(f"价差: {spread['spread_cny']:.2f} 元/克")
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union, Any
import time
import random
import re
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 配置
# ============================================================================

# 东方财富API
EM_BASE_URL = "https://push2.eastmoney.com/api/qt"
EM_FUTURES_LIST = f"{EM_BASE_URL}/clist/get"  # 期货列表
EM_STOCK_GET = f"{EM_BASE_URL}/stock/get"      # 个股行情

# 新浪API
SINA_METAL_API = "https://hq.sinajs.cn/list="

# 市场代码
# 142: 上期所期货 (SHFE)
# 143: 上海黄金交易所 (SGE)
# 133: 外盘

# 东方财富请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'https://quote.eastmoney.com/',
}

# 默认汇率
USD_CNY_RATE = 7.24

# 金衡盎司转克
TROY_OUNCE_TO_GRAM = 31.1034768

# 模拟数据（离线模式使用）
MOCK_DATA = {
    'gold': {
        'au9999': {'last': 480.50, 'open': 479.80, 'high': 481.20, 'low': 478.50, 'prev_close': 479.30},
        'au_td': {'last': 479.80, 'open': 479.00, 'high': 480.50, 'low': 478.00, 'prev_close': 478.60},
        'london': {'last': 2050.50, 'open': 2048.00, 'high': 2055.00, 'low': 2045.00, 'prev_close': 2046.30},
    },
    'silver': {
        'ag9999': {'last': 6250, 'open': 6230, 'high': 6280, 'low': 6210, 'prev_close': 6220},
        'ag_td': {'last': 6230, 'open': 6210, 'high': 6260, 'low': 6190, 'prev_close': 6200},
        'london': {'last': 26.50, 'open': 26.30, 'high': 26.80, 'low': 26.10, 'prev_close': 26.25},
    },
    'platinum': {
        'london': {'last': 985.00, 'open': 982.00, 'high': 990.00, 'low': 978.00, 'prev_close': 980.00},
    },
    'palladium': {
        'london': {'last': 1020.00, 'open': 1015.00, 'high': 1025.00, 'low': 1010.00, 'prev_close': 1012.00},
    }
}

# 离线模式开关
OFFLINE_MODE = False


# ============================================================================
# 工具函数
# ============================================================================

def _make_request(url: str, params: dict = None, retries: int = 3, timeout: int = 10) -> Optional[dict]:
    """发送HTTP请求并返回JSON数据"""
    if OFFLINE_MODE:
        return None
        
    for i in range(retries):
        try:
            response = requests.get(
                url, 
                params=params,
                headers=HEADERS,
                timeout=timeout
            )
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return {'text': response.text}
            elif response.status_code == 403:
                logger.warning(f"Access forbidden (403) for {url}")
                break
        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout for {url}")
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error for {url}: {e}")
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            
        if i < retries - 1:
            time.sleep(random.uniform(0.5, 1.5))
    
    return None


def _parse_em_stock_data(data: dict) -> Optional[dict]:
    """解析东方财富个股行情数据"""
    if not data or not data.get('data'):
        return None
    
    d = data['data']
    # 东方财富字段映射
    # f43: 最新价, f44: 最高价, f45: 最低价, f46: 今开
    # f47: 成交量, f48: 成交额, f50: 昨收
    # f51: 涨跌额, f52: 涨跌幅, f55: 时间
    # f57: 代码, f58: 名称
    # f60: 昨收价
    
    try:
        last = d.get('f43')
        high = d.get('f44')
        low = d.get('f45')
        open_price = d.get('f46')
        prev_close = d.get('f60')
        
        # 处理100倍价格问题（东方财富某些价格需要除以100）
        if last and last > 10000:
            last = last / 100
        if high and high > 10000:
            high = high / 100
        if low and low > 10000:
            low = low / 100
        if open_price and open_price > 10000:
            open_price = open_price / 100
        if prev_close and prev_close > 10000:
            prev_close = prev_close / 100
        
        return {
            'code': d.get('f57'),
            'name': d.get('f58'),
            'last': last / 100 if last else None,
            'open': open_price / 100 if open_price else None,
            'high': high / 100 if high else None,
            'low': low / 100 if low else None,
            'prev_close': prev_close / 100 if prev_close else None,
            'volume': d.get('f47'),
            'amount': d.get('f48'),
        }
    except Exception as e:
        logger.warning(f"Error parsing EM data: {e}")
        return None


def _parse_em_list_data(data: dict) -> List[dict]:
    """解析东方财富列表数据"""
    if not data or not data.get('data') or not data['data'].get('diff'):
        return []
    
    result = []
    for item in data['data']['diff']:
        try:
            last = item.get('f2')
            high = item.get('f4')
            low = item.get('f5')
            open_price = item.get('f17')
            prev_close = item.get('f18')
            
            # 某些价格需要除以100或1000
            # 黄金价格通常在400-500，白银在5000-7000
            # f2可能是实际价格，不需要调整
            
            result.append({
                'code': item.get('f12'),
                'name': item.get('f14'),
                'last': last,
                'open': open_price,
                'high': high,
                'low': low,
                'prev_close': prev_close,
                'change': item.get('f3'),
                'change_pct': item.get('f4'),
                'volume': item.get('f5'),
                'amount': item.get('f6'),
            })
        except Exception as e:
            continue
    
    return result


def _parse_sina_data(data_str: str) -> Dict[str, Any]:
    """解析Sina行情数据格式"""
    result = {}
    
    for line in data_str.strip().split('\n'):
        if not line or '=' not in line:
            continue
            
        try:
            match = re.match(r'var hq_str_(\w+)="(.*)";', line)
            if not match:
                continue
                
            code = match.group(1)
            data = match.group(2)
            
            if not data:
                result[code] = {'status': 'no_data'}
                continue
            
            parts = data.split(',')
            
            if len(parts) >= 10:
                try:
                    # 尝试解析数值
                    parsed = {
                        'name': parts[0] if not parts[0].replace('.', '').isdigit() else '',
                        'open': float(parts[1]) if parts[1] else None,
                        'prev_close': float(parts[2]) if parts[2] else None,
                        'last': float(parts[3]) if parts[3] else None,
                        'high': float(parts[4]) if parts[4] else None,
                        'low': float(parts[5]) if parts[5] else None,
                        'bid': float(parts[6]) if parts[6] else None,
                        'ask': float(parts[7]) if parts[7] else None,
                        'volume': float(parts[8]) if parts[8] else None,
                        'amount': float(parts[9]) if parts[9] else None,
                    }
                except ValueError:
                    parsed = {'raw': data, 'parts': parts}
                
                result[code] = parsed
        except Exception:
            continue
    
    return result


def _get_usd_cny_rate() -> float:
    """获取USD/CNY实时汇率"""
    if OFFLINE_MODE:
        return USD_CNY_RATE
    
    try:
        # 尝试从东方财富获取汇率
        params = {
            'secid': '116.USDCNY',
            'fields': 'f43,f57,f58'
        }
        data = _make_request(EM_STOCK_GET, params)
        if data and data.get('data'):
            rate = data['data'].get('f43')
            if rate:
                return rate / 100 if rate > 10 else rate
    except:
        pass
    
    return USD_CNY_RATE


def _calculate_change(last: float, prev_close: float) -> tuple:
    """计算涨跌额和涨跌幅"""
    if last is None or prev_close is None or prev_close == 0:
        return None, None
    change = last - prev_close
    change_pct = (change / prev_close) * 100
    return change, change_pct


# ============================================================================
# 东方财富数据源
# ============================================================================

def _fetch_sge_gold_em() -> Dict[str, Any]:
    """从东方财富获取上海黄金交易所黄金数据"""
    result = {}
    
    # 东方财富上金所代码
    sge_codes = {
        'Au99.99': 'Au99.99',
        'Au99.95': 'Au99.95',
        'Au(T+D)': 'Au(T+D)',
        'Au100g': 'Au100g',
        'mAu(T+D)': 'mAu(T+D)',
    }
    
    # 市场代码 143 = 上海黄金交易所
    for name, code in sge_codes.items():
        params = {
            'secid': f'143.{code}',
            'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f170,f171'
        }
        data = _make_request(EM_STOCK_GET, params)
        if data:
            parsed = _parse_em_stock_data(data)
            if parsed and parsed.get('last'):
                change, change_pct = _calculate_change(parsed['last'], parsed['prev_close'])
                result[name.lower().replace('(', '').replace(')', '').replace('.', '')] = {
                    'name': name,
                    'code': code,
                    'last': parsed['last'],
                    'open': parsed['open'],
                    'high': parsed['high'],
                    'low': parsed['low'],
                    'prev_close': parsed['prev_close'],
                    'change': change,
                    'change_pct': change_pct,
                    'volume': parsed.get('volume'),
                    'amount': parsed.get('amount'),
                    'unit': '元/克'
                }
    
    return result


def _fetch_sge_silver_em() -> Dict[str, Any]:
    """从东方财富获取上海黄金交易所白银数据"""
    result = {}
    
    sge_codes = {
        'Ag99.99': 'Ag99.99',
        'Ag(T+D)': 'Ag(T+D)',
    }
    
    for name, code in sge_codes.items():
        params = {
            'secid': f'143.{code}',
            'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60'
        }
        data = _make_request(EM_STOCK_GET, params)
        if data:
            parsed = _parse_em_stock_data(data)
            if parsed and parsed.get('last'):
                change, change_pct = _calculate_change(parsed['last'], parsed['prev_close'])
                key = name.lower().replace('(', '').replace(')', '').replace('.', '')
                result[key] = {
                    'name': name,
                    'code': code,
                    'last': parsed['last'],
                    'open': parsed['open'],
                    'high': parsed['high'],
                    'low': parsed['low'],
                    'prev_close': parsed['prev_close'],
                    'change': change,
                    'change_pct': change_pct,
                    'volume': parsed.get('volume'),
                    'amount': parsed.get('amount'),
                    'unit': '元/千克'
                }
    
    return result


def _fetch_international_gold_em() -> Dict[str, Any]:
    """从东方财富获取国际金价数据"""
    result = {}
    
    # 伦敦金 - 外盘代码
    params = {
        'secid': '133.XAUUSD',
        'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60'
    }
    data = _make_request(EM_STOCK_GET, params)
    if data:
        parsed = _parse_em_stock_data(data)
        if parsed and parsed.get('last'):
            change, change_pct = _calculate_change(parsed['last'], parsed['prev_close'])
            result['london'] = {
                'name': '伦敦金',
                'code': 'XAUUSD',
                'last': parsed['last'],
                'open': parsed['open'],
                'high': parsed['high'],
                'low': parsed['low'],
                'prev_close': parsed['prev_close'],
                'change': change,
                'change_pct': change_pct,
                'unit': '美元/盎司'
            }
    
    return result


def _fetch_international_silver_em() -> Dict[str, Any]:
    """从东方财富获取国际银价数据"""
    result = {}
    
    # 伦敦银
    params = {
        'secid': '133.XAGUSD',
        'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60'
    }
    data = _make_request(EM_STOCK_GET, params)
    if data:
        parsed = _parse_em_stock_data(data)
        if parsed and parsed.get('last'):
            change, change_pct = _calculate_change(parsed['last'], parsed['prev_close'])
            result['london'] = {
                'name': '伦敦银',
                'code': 'XAGUSD',
                'last': parsed['last'],
                'open': parsed['open'],
                'high': parsed['high'],
                'low': parsed['low'],
                'prev_close': parsed['prev_close'],
                'change': change,
                'change_pct': change_pct,
                'unit': '美元/盎司'
            }
    
    return result


# ============================================================================
# 核心API函数
# ============================================================================

def get_gold_price(use_mock: bool = False) -> Dict[str, Any]:
    """
    获取黄金价格数据
    
    参数:
        use_mock: 是否使用模拟数据（离线模式）
    
    返回:
        {
            'au9999': {'last': 480.50, 'change': 1.2, 'change_pct': 0.25, ...},
            'au_td': {...},
            'london': {'last': 2050.50, 'change': 5.2, ...},  # 美元/盎司
            'timestamp': '2024-03-25 15:30:00',
            'usd_cny': 7.24,
            'source': 'eastmoney'  # 数据来源
        }
    """
    result = {
        'au9999': None,
        'au9995': None,
        'au_td': None,
        'au100g': None,
        'london': None,
        'ny_gold': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'usd_cny': USD_CNY_RATE,
        'source': None
    }
    
    # 使用模拟数据
    if use_mock or OFFLINE_MODE:
        result.update(MOCK_DATA['gold'])
        result['source'] = 'mock'
        return result
    
    # 尝试东方财富数据源
    try:
        # 获取上金所黄金
        sge_gold = _fetch_sge_gold_em()
        if sge_gold:
            result.update(sge_gold)
            result['source'] = 'eastmoney'
        
        # 获取国际金价
        intl_gold = _fetch_international_gold_em()
        if intl_gold:
            result['london'] = intl_gold.get('london')
            if not result['source']:
                result['source'] = 'eastmoney'
        
        # 获取汇率
        result['usd_cny'] = _get_usd_cny_rate()
        
    except Exception as e:
        logger.warning(f"Error fetching gold price: {e}")
    
    # 如果没有获取到数据，使用模拟数据
    if not result['source']:
        logger.info("Using mock data for gold price")
        result.update(MOCK_DATA['gold'])
        result['source'] = 'mock'
    
    return result


def get_silver_price(use_mock: bool = False) -> Dict[str, Any]:
    """
    获取白银价格数据
    
    返回:
        {
            'ag9999': {'last': 5200, 'change': 25, 'change_pct': 0.48, ...},
            'ag_td': {...},
            'london': {'last': 24.5, ...},  # 美元/盎司
            'timestamp': '2024-03-25 15:30:00',
            'usd_cny': 7.24
        }
    """
    result = {
        'ag9999': None,
        'ag_td': None,
        'london': None,
        'ny_silver': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'usd_cny': USD_CNY_RATE,
        'source': None
    }
    
    if use_mock or OFFLINE_MODE:
        result.update(MOCK_DATA['silver'])
        result['source'] = 'mock'
        return result
    
    try:
        # 获取上金所白银
        sge_silver = _fetch_sge_silver_em()
        if sge_silver:
            result.update(sge_silver)
            result['source'] = 'eastmoney'
        
        # 获取国际银价
        intl_silver = _fetch_international_silver_em()
        if intl_silver:
            result['london'] = intl_silver.get('london')
            if not result['source']:
                result['source'] = 'eastmoney'
        
        result['usd_cny'] = _get_usd_cny_rate()
        
    except Exception as e:
        logger.warning(f"Error fetching silver price: {e}")
    
    if not result['source']:
        logger.info("Using mock data for silver price")
        result.update(MOCK_DATA['silver'])
        result['source'] = 'mock'
    
    return result


def get_precious_metals(use_mock: bool = False) -> Dict[str, Any]:
    """
    获取所有贵金属价格列表
    
    返回:
        {
            'gold': {...},      # 黄金数据
            'silver': {...},     # 白银数据
            'platinum': {...},   # 铂金数据
            'palladium': {...},  # 钯金数据
            'timestamp': '2024-03-25 15:30:00',
            'usd_cny': 7.24
        }
    """
    result = {
        'gold': None,
        'silver': None,
        'platinum': None,
        'palladium': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'usd_cny': USD_CNY_RATE
    }
    
    # 获取黄金数据
    result['gold'] = get_gold_price(use_mock)
    result['usd_cny'] = result['gold'].get('usd_cny', USD_CNY_RATE)
    
    # 获取白银数据
    result['silver'] = get_silver_price(use_mock)
    
    # 铂金和钯金
    if use_mock or OFFLINE_MODE:
        result['platinum'] = {'london': MOCK_DATA['platinum']['london']}
        result['palladium'] = {'london': MOCK_DATA['palladium']['london']}
    else:
        # 尝试获取铂金和钯金
        try:
            # 铂金
            params = {
                'secid': '133.XPTUSD',
                'fields': 'f43,f44,f45,f46,f57,f58,f60'
            }
            data = _make_request(EM_STOCK_GET, params)
            if data and data.get('data'):
                d = data['data']
                result['platinum'] = {
                    'london': {
                        'name': '伦敦铂金',
                        'last': d.get('f43'),
                        'prev_close': d.get('f60'),
                        'unit': '美元/盎司'
                    }
                }
            
            # 钯金
            params['secid'] = '133.XPDUSD'
            data = _make_request(EM_STOCK_GET, params)
            if data and data.get('data'):
                d = data['data']
                result['palladium'] = {
                    'london': {
                        'name': '伦敦钯金',
                        'last': d.get('f43'),
                        'prev_close': d.get('f60'),
                        'unit': '美元/盎司'
                    }
                }
        except Exception as e:
            logger.warning(f"Error fetching platinum/palladium: {e}")
        
        # 如果获取失败，使用模拟数据
        if not result.get('platinum'):
            result['platinum'] = {'london': MOCK_DATA['platinum']['london']}
        if not result.get('palladium'):
            result['palladium'] = {'london': MOCK_DATA['palladium']['london']}
    
    return result


def get_shfe_gold(contract: str = None, use_mock: bool = False) -> Dict[str, Any]:
    """
    获取上期所(SHFE)黄金期货数据
    
    参数:
        contract: 合约代码，如 'AU2406'，默认获取主力合约
        use_mock: 是否使用模拟数据
    
    返回:
        {
            'main_contract': 'AU2406',
            'contracts': [
                {
                    'code': 'AU2406',
                    'name': '黄金2406',
                    'last': 485.00,
                    'change': 1.5,
                    'change_pct': 0.31,
                    'volume': 123456,
                    ...
                },
                ...
            ],
            'timestamp': '2024-03-25 15:30:00'
        }
    """
    result = {
        'main_contract': None,
        'contracts': [],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': None
    }
    
    if use_mock or OFFLINE_MODE:
        result['contracts'] = [
            {'code': 'AU2406', 'name': '黄金2406', 'last': 485.00, 'prev_close': 483.50, 'volume': 125000}
        ]
        result['main_contract'] = 'AU2406'
        result['source'] = 'mock'
        return result
    
    try:
        # 东方财富上期所黄金期货列表
        # fs=m:142 表示上期所
        params = {
            'pn': 1,
            'pz': 20,
            'po': 1,
            'np': 1,
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': 'm:142,m:142+f:!50',  # 上期所期货，排除期权
            'fields': 'f1,f2,f3,f4,f5,f6,f7,f12,f13,f14,f15,f16,f17,f18'
        }
        data = _make_request(EM_FUTURES_LIST, params)
        
        if data and data.get('data') and data['data'].get('diff'):
            max_volume = 0
            for item in data['data']['diff']:
                code = item.get('f12', '')
                # 只取黄金合约 (AU开头)
                if not code.startswith('AU'):
                    continue
                
                last = item.get('f2')
                prev_close = item.get('f18')
                volume = item.get('f5', 0) or 0
                change = item.get('f3')
                change_pct = item.get('f4')
                
                contract_data = {
                    'code': code,
                    'name': item.get('f14', ''),
                    'last': last,
                    'open': item.get('f17'),
                    'high': item.get('f15'),
                    'low': item.get('f16'),
                    'prev_close': prev_close,
                    'change': change,
                    'change_pct': change_pct,
                    'volume': volume,
                    'amount': item.get('f6'),
                    'unit': '元/克'
                }
                result['contracts'].append(contract_data)
                
                # 找主力合约（成交量最大）
                if volume > max_volume:
                    max_volume = volume
                    result['main_contract'] = code
            
            result['source'] = 'eastmoney'
    
    except Exception as e:
        logger.warning(f"Error fetching SHFE gold: {e}")
    
    # 如果没有数据，使用模拟数据
    if not result['contracts']:
        result['contracts'] = [
            {'code': 'AU2406', 'name': '黄金2406', 'last': 485.00, 'prev_close': 483.50, 'volume': 125000}
        ]
        result['main_contract'] = 'AU2406'
        result['source'] = 'mock'
    
    # 如果指定了合约
    if contract and result['contracts']:
        for c in result['contracts']:
            if c['code'] == contract:
                result['specified_contract'] = c
                break
    
    return result


def get_shfe_silver(contract: str = None, use_mock: bool = False) -> Dict[str, Any]:
    """
    获取上期所(SHFE)白银期货数据
    """
    result = {
        'main_contract': None,
        'contracts': [],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': None
    }
    
    if use_mock or OFFLINE_MODE:
        result['contracts'] = [
            {'code': 'AG2406', 'name': '白银2406', 'last': 6250, 'prev_close': 6220, 'volume': 250000}
        ]
        result['main_contract'] = 'AG2406'
        result['source'] = 'mock'
        return result
    
    try:
        params = {
            'pn': 1,
            'pz': 20,
            'po': 1,
            'np': 1,
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': 'm:142',
            'fields': 'f1,f2,f3,f4,f5,f6,f7,f12,f13,f14,f15,f16,f17,f18'
        }
        data = _make_request(EM_FUTURES_LIST, params)
        
        if data and data.get('data') and data['data'].get('diff'):
            max_volume = 0
            for item in data['data']['diff']:
                code = item.get('f12', '')
                # 只取白银合约 (AG开头)
                if not code.startswith('AG'):
                    continue
                
                last = item.get('f2')
                prev_close = item.get('f18')
                volume = item.get('f5', 0) or 0
                
                contract_data = {
                    'code': code,
                    'name': item.get('f14', ''),
                    'last': last,
                    'open': item.get('f17'),
                    'high': item.get('f15'),
                    'low': item.get('f16'),
                    'prev_close': prev_close,
                    'change': item.get('f3'),
                    'change_pct': item.get('f4'),
                    'volume': volume,
                    'amount': item.get('f6'),
                    'unit': '元/千克'
                }
                result['contracts'].append(contract_data)
                
                if volume > max_volume:
                    max_volume = volume
                    result['main_contract'] = code
            
            result['source'] = 'eastmoney'
    
    except Exception as e:
        logger.warning(f"Error fetching SHFE silver: {e}")
    
    if not result['contracts']:
        result['contracts'] = [
            {'code': 'AG2406', 'name': '白银2406', 'last': 6250, 'prev_close': 6220, 'volume': 250000}
        ]
        result['main_contract'] = 'AG2406'
        result['source'] = 'mock'
    
    if contract and result['contracts']:
        for c in result['contracts']:
            if c['code'] == contract:
                result['specified_contract'] = c
                break
    
    return result


def calculate_gold_spread(use_mock: bool = False) -> Dict[str, Any]:
    """
    计算黄金内外价差
    
    比较上海黄金交易所Au99.99与伦敦金的价差，
    考虑汇率换算和单位转换（盎司转克）
    
    返回:
        {
            'sge_price': 480.50,           # 上金所金价 (元/克)
            'london_price_usd': 2050.50,   # 伦敦金价 (美元/盎司)
            'london_price_cny': 476.85,    # 伦敦金价折算人民币 (元/克)
            'spread_cny': 3.65,            # 价差 (元/克)
            'spread_pct': 0.77,            # 价差百分比 (%)
            'usd_cny': 7.24,               # 汇率
            'import_cost': 485.00,         # 进口成本 (估算，含税费)
            'arbitrage_opportunity': True, # 是否存在套利机会
            'timestamp': '2024-03-25 15:30:00'
        }
    """
    result = {
        'sge_price': None,
        'london_price_usd': None,
        'london_price_cny': None,
        'spread_cny': None,
        'spread_pct': None,
        'usd_cny': None,
        'import_cost': None,
        'arbitrage_opportunity': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 获取黄金价格
    gold_data = get_gold_price(use_mock)
    
    # 上金所金价
    if gold_data.get('au9999') and gold_data['au9999'].get('last'):
        result['sge_price'] = gold_data['au9999']['last']
    elif gold_data.get('au_td') and gold_data['au_td'].get('last'):
        result['sge_price'] = gold_data['au_td']['last']
    
    # 伦敦金价
    if gold_data.get('london') and gold_data['london'].get('last'):
        result['london_price_usd'] = gold_data['london']['last']
    
    # 汇率
    result['usd_cny'] = gold_data.get('usd_cny', USD_CNY_RATE)
    
    # 计算价差
    if result['sge_price'] and result['london_price_usd'] and result['usd_cny']:
        # 伦敦金价格换算为人民币元/克
        # (美元/盎司) × (人民币/美元) / (克/盎司) = 人民币/克
        result['london_price_cny'] = (result['london_price_usd'] * result['usd_cny']) / TROY_OUNCE_TO_GRAM
        
        # 计算价差
        result['spread_cny'] = result['sge_price'] - result['london_price_cny']
        
        # 价差百分比
        if result['london_price_cny'] > 0:
            result['spread_pct'] = (result['spread_cny'] / result['london_price_cny']) * 100
        
        # 估算进口成本（含关税、增值税等，约2-3%）
        import_cost_rate = 1.025  # 2.5%综合成本
        result['import_cost'] = result['london_price_cny'] * import_cost_rate
        
        # 判断套利机会
        if result['sge_price'] > result['import_cost']:
            result['arbitrage_opportunity'] = True
        else:
            result['arbitrage_opportunity'] = False
    
    return result


def calculate_silver_spread(use_mock: bool = False) -> Dict[str, Any]:
    """
    计算白银内外价差
    
    返回:
        {
            'sge_price': 5200,             # 上金所银价 (元/千克)
            'london_price_usd': 24.5,      # 伦敦银价 (美元/盎司)
            'london_price_cny': 5698,      # 伦敦银价折算人民币 (元/千克)
            'spread_cny': -498,            # 价差 (元/千克)
            'spread_pct': -8.74,           # 价差百分比 (%)
            'usd_cny': 7.24,
            'timestamp': '2024-03-25 15:30:00'
        }
    """
    result = {
        'sge_price': None,
        'london_price_usd': None,
        'london_price_cny': None,
        'spread_cny': None,
        'spread_pct': None,
        'usd_cny': None,
        'import_cost': None,
        'arbitrage_opportunity': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 获取白银价格
    silver_data = get_silver_price(use_mock)
    
    # 上金所银价 (元/千克)
    if silver_data.get('ag9999') and silver_data['ag9999'].get('last'):
        result['sge_price'] = silver_data['ag9999']['last']
    elif silver_data.get('ag_td') and silver_data['ag_td'].get('last'):
        result['sge_price'] = silver_data['ag_td']['last']
    
    # 伦敦银价
    if silver_data.get('london') and silver_data['london'].get('last'):
        result['london_price_usd'] = silver_data['london']['last']
    
    # 汇率
    result['usd_cny'] = silver_data.get('usd_cny', USD_CNY_RATE)
    
    # 计算价差
    if result['sge_price'] and result['london_price_usd'] and result['usd_cny']:
        # 伦敦银价格换算为人民币元/千克
        result['london_price_cny'] = (result['london_price_usd'] * result['usd_cny'] * 1000) / TROY_OUNCE_TO_GRAM
        
        # 计算价差
        result['spread_cny'] = result['sge_price'] - result['london_price_cny']
        
        # 价差百分比
        if result['london_price_cny'] > 0:
            result['spread_pct'] = (result['spread_cny'] / result['london_price_cny']) * 100
        
        # 估算进口成本
        import_cost_rate = 1.03
        result['import_cost'] = result['london_price_cny'] * import_cost_rate
        
        # 判断套利机会
        if result['sge_price'] > result['import_cost']:
            result['arbitrage_opportunity'] = True
        else:
            result['arbitrage_opportunity'] = False
    
    return result


def get_gold_ratio(use_mock: bool = False) -> Dict[str, Any]:
    """
    获取金银比价和其他贵金属比价
    
    返回:
        {
            'gold_silver_ratio': 83.5,      # 金银比
            'gold_platinum_ratio': 1.2,     # 金铂比
            'gold_palladium_ratio': 0.85,   # 金钯比
            'timestamp': '2024-03-25 15:30:00'
        }
    """
    result = {
        'gold_silver_ratio': None,
        'gold_platinum_ratio': None,
        'gold_palladium_ratio': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 获取贵金属价格
    metals = get_precious_metals(use_mock)
    
    gold_price = None
    silver_price = None
    platinum_price = None
    palladium_price = None
    
    # 提取黄金价格
    if metals.get('gold') and metals['gold'].get('london'):
        gold_price = metals['gold']['london'].get('last')
    
    # 提取白银价格
    if metals.get('silver') and metals['silver'].get('london'):
        silver_price = metals['silver']['london'].get('last')
    
    # 提取铂金价格
    if metals.get('platinum') and metals['platinum'].get('london'):
        platinum_price = metals['platinum']['london'].get('last')
    
    # 提取钯金价格
    if metals.get('palladium') and metals['palladium'].get('london'):
        palladium_price = metals['palladium']['london'].get('last')
    
    # 计算比价
    if gold_price and silver_price and silver_price > 0:
        result['gold_silver_ratio'] = gold_price / silver_price
    
    if gold_price and platinum_price and platinum_price > 0:
        result['gold_platinum_ratio'] = gold_price / platinum_price
    
    if gold_price and palladium_price and palladium_price > 0:
        result['gold_palladium_ratio'] = gold_price / palladium_price
    
    return result


def format_price_report(metals: str = 'all', use_mock: bool = False) -> str:
    """
    生成贵金属价格报告
    
    参数:
        metals: 'all', 'gold', 'silver', 'platinum', 'palladium'
        use_mock: 是否使用模拟数据
    
    返回:
        格式化的价格报告字符串
    """
    report_lines = []
    report_lines.append("=" * 50)
    report_lines.append("📊 贵金属价格报告")
    report_lines.append("=" * 50)
    
    if metals in ['all', 'gold']:
        gold = get_gold_price(use_mock)
        source = gold.get('source', 'unknown')
        report_lines.append(f"\n🔸 黄金 (数据源: {source})")
        if gold.get('au9999'):
            d = gold['au9999']
            change_str = f"{'+' if d.get('change', 0) >= 0 else ''}{d.get('change', 0):.2f}" if d.get('change') is not None else '-'
            pct_str = f"{'+' if d.get('change_pct', 0) >= 0 else ''}{d.get('change_pct', 0):.2f}%" if d.get('change_pct') is not None else '-'
            report_lines.append(f"  Au99.99: ¥{d.get('last', '-'):.2f}/克 ({change_str}, {pct_str})")
        if gold.get('au_td'):
            d = gold['au_td']
            change_str = f"{'+' if d.get('change', 0) >= 0 else ''}{d.get('change', 0):.2f}" if d.get('change') is not None else '-'
            pct_str = f"{'+' if d.get('change_pct', 0) >= 0 else ''}{d.get('change_pct', 0):.2f}%" if d.get('change_pct') is not None else '-'
            report_lines.append(f"  Au(T+D): ¥{d.get('last', '-'):.2f}/克 ({change_str}, {pct_str})")
        if gold.get('london'):
            d = gold['london']
            change_str = f"{'+' if d.get('change', 0) >= 0 else ''}{d.get('change', 0):.2f}" if d.get('change') is not None else '-'
            report_lines.append(f"  伦敦金: ${d.get('last', '-'):.2f}/盎司 ({change_str})")
    
    if metals in ['all', 'silver']:
        silver = get_silver_price(use_mock)
        source = silver.get('source', 'unknown')
        report_lines.append(f"\n🔹 白银 (数据源: {source})")
        if silver.get('ag9999'):
            d = silver['ag9999']
            change_str = f"{'+' if d.get('change', 0) >= 0 else ''}{d.get('change', 0):.0f}" if d.get('change') is not None else '-'
            report_lines.append(f"  Ag99.99: ¥{d.get('last', '-'):.0f}/千克 ({change_str})")
        if silver.get('ag_td'):
            d = silver['ag_td']
            change_str = f"{'+' if d.get('change', 0) >= 0 else ''}{d.get('change', 0):.0f}" if d.get('change') is not None else '-'
            report_lines.append(f"  Ag(T+D): ¥{d.get('last', '-'):.0f}/千克 ({change_str})")
        if silver.get('london'):
            d = silver['london']
            change_str = f"{'+' if d.get('change', 0) >= 0 else ''}{d.get('change', 0):.2f}" if d.get('change') is not None else '-'
            report_lines.append(f"  伦敦银: ${d.get('last', '-'):.2f}/盎司 ({change_str})")
    
    if metals == 'all':
        # 价差分析
        spread = calculate_gold_spread(use_mock)
        if spread.get('spread_cny') is not None:
            report_lines.append("\n📈 黄金内外价差")
            report_lines.append(f"  上金所: ¥{spread.get('sge_price', '-'):.2f}/克")
            report_lines.append(f"  伦敦金折算: ¥{spread.get('london_price_cny', '-'):.2f}/克")
            spread_str = f"{'+' if spread.get('spread_cny', 0) >= 0 else ''}{spread.get('spread_cny', 0):.2f}"
            report_lines.append(f"  价差: {spread_str} 元/克 ({spread.get('spread_pct', 0):.2f}%)")
            if spread.get('arbitrage_opportunity'):
                report_lines.append("  ⚠️ 存在套利空间")
        
        # 金银比
        ratio = get_gold_ratio(use_mock)
        if ratio.get('gold_silver_ratio'):
            report_lines.append(f"\n📊 金银比: {ratio.get('gold_silver_ratio'):.1f}")
    
    report_lines.append("\n" + "=" * 50)
    report_lines.append(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"汇率: USD/CNY = {USD_CNY_RATE:.2f}")
    
    return "\n".join(report_lines)


# ============================================================================
# 便捷函数
# ============================================================================

def get_current_gold_price() -> Optional[float]:
    """获取当前黄金价格（上金所Au99.99）"""
    gold = get_gold_price()
    if gold.get('au9999') and gold['au9999'].get('last'):
        return gold['au9999']['last']
    return None


def get_current_silver_price() -> Optional[float]:
    """获取当前白银价格（上金所Ag99.99）"""
    silver = get_silver_price()
    if silver.get('ag9999') and silver['ag9999'].get('last'):
        return silver['ag9999']['last']
    return None


def get_london_gold_price() -> Optional[float]:
    """获取伦敦金价（美元/盎司）"""
    gold = get_gold_price()
    if gold.get('london') and gold['london'].get('last'):
        return gold['london']['last']
    return None


def get_london_silver_price() -> Optional[float]:
    """获取伦敦银价（美元/盎司）"""
    silver = get_silver_price()
    if silver.get('london') and silver['london'].get('last'):
        return silver['london']['last']
    return None


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    print("测试贵金属数据模块")
    print("-" * 50)
    
    # 测试黄金价格
    print("\n1. 黄金价格:")
    gold = get_gold_price()
    print(f"   Au99.99: {gold.get('au9999')}")
    print(f"   伦敦金: {gold.get('london')}")
    print(f"   数据源: {gold.get('source')}")
    
    # 测试白银价格
    print("\n2. 白银价格:")
    silver = get_silver_price()
    print(f"   Ag99.99: {silver.get('ag9999')}")
    print(f"   伦敦银: {silver.get('london')}")
    print(f"   数据源: {silver.get('source')}")
    
    # 测试价差计算
    print("\n3. 黄金内外价差:")
    spread = calculate_gold_spread()
    print(f"   上金所: {spread.get('sge_price')}")
    print(f"   伦敦金折算: {spread.get('london_price_cny')}")
    print(f"   价差: {spread.get('spread_cny')}")
    
    # 测试价格报告
    print("\n4. 价格报告:")
    print(format_price_report())