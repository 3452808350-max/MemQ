"""
东方财富新闻爬虫模块
获取个股资讯、行业新闻、资金流向数据

API来源：
- 公告: https://np-anotice-stock.eastmoney.com/api/security/ann
- 资金流向: http://push2.eastmoney.com/api/qt/stock/fflow/
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union
import time
import random
import re
import json

# ============================================================================
# 配置
# ============================================================================

# 东方财富API基础URL
EM_NOTICE_API = "https://np-anotice-stock.eastmoney.com/api/security/ann"
EM_MONEY_FLOW_API = "http://push2.eastmoney.com/api/qt/stock/fflow"
EM_STOCK_INFO_API = "https://push2.eastmoney.com/api/qt/stock/get"

# 反爬虫配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'https://www.eastmoney.com/',
}

# 行业板块映射 (东方财富板块代码)
SECTOR_MAP = {
    '银行': 'BK0478',
    '证券': 'BK0477',
    '保险': 'BK0479',
    '房地产': 'BK0451',
    '酿酒': 'BK0479',
    '医药': 'BK0727',
    '汽车': 'BK0480',
    '半导体': 'BK0897',
    '软件': 'BK0732',
    '电子': 'BK0733',
    '通信': 'BK0734',
    '传媒': 'BK0735',
    '电力': 'BK0476',
    '煤炭': 'BK0475',
    '石油': 'BK0474',
    '钢铁': 'BK0481',
    '有色金属': 'BK0472',
    '化工': 'BK0470',
    '建材': 'BK0469',
    '机械': 'BK0468',
}

# 公告类型映射
ANN_TYPE_MAP = {
    '001001': '年报',
    '001002': '半年报',
    '001003': '季报',
    '001004': '业绩预告',
    '001005': '业绩快报',
    '001006': '公告',
    '002001': '董事会决议',
    '002002': '股东大会',
    '003001': '交易提示',
    '004001': '风险提示',
    '005001': '首发新股',
    '005002': '增发',
    '005003': '配股',
}

# ============================================================================
# 工具函数
# ============================================================================

def _make_request(url: str, params: dict = None, max_retries: int = 3) -> Optional[dict]:
    """
    发起HTTP请求（带重试和反爬处理）
    
    Args:
        url: 请求URL
        params: 请求参数
        max_retries: 最大重试次数
    
    Returns:
        JSON响应数据或None
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    
    for attempt in range(max_retries):
        try:
            # 随机延时防止被封
            if attempt > 0:
                time.sleep(random.uniform(1, 3))
            
            response = session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            # 尝试解析JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                # 尝试JSONP格式
                text = response.text
                if 'callback' in text or '(' in text:
                    # 提取JSONP中的JSON
                    match = re.search(r'\{.*\}', text, re.DOTALL)
                    if match:
                        return json.loads(match.group())
                return {'raw_text': text}
                
        except requests.exceptions.RequestException as e:
            print(f"[!] 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None
            continue
    
    return None


def _format_stock_code(symbol: str) -> tuple:
    """
    格式化股票代码
    
    Args:
        symbol: 股票代码 (如 '600519', 'SH600519', '000001', 'SZ000001')
    
    Returns:
        (市场代码, 标准化代码, secid)
        例如: (1, 'SH600519', '1.600519')
    """
    symbol = symbol.upper().strip()
    
    # 已经带前缀
    if symbol.startswith('SH'):
        code = symbol[2:]
        return 1, f"SH{code}", f"1.{code}"
    elif symbol.startswith('SZ'):
        code = symbol[2:]
        return 0, f"SZ{code}", f"0.{code}"
    elif symbol.startswith('BJ'):
        code = symbol[2:]
        return 0, f"BJ{code}", f"0.{code}"
    
    # 判断市场
    if symbol.startswith(('6', '9')):
        return 1, f"SH{symbol}", f"1.{symbol}"
    elif symbol.startswith(('0', '1', '2', '3')):
        return 0, f"SZ{symbol}", f"0.{symbol}"
    elif symbol.startswith(('4', '8')):
        return 0, f"BJ{symbol}", f"0.{symbol}"
    else:
        return 1, f"SH{symbol}", f"1.{symbol}"  # 默认上海


def _parse_ann_time(time_str: str) -> datetime:
    """
    解析公告时间字符串
    
    Args:
        time_str: 时间字符串
    
    Returns:
        datetime对象
    """
    if not time_str:
        return datetime.now()
    
    # 尝试多种格式
    formats = [
        '%Y-%m-%d %H:%M:%S:%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y/%m/%d %H:%M',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(time_str[:26] if 'f' in fmt else time_str[:19], fmt)
        except ValueError:
            continue
    
    return datetime.now()


# ============================================================================
# 个股新闻（公告）
# ============================================================================

def get_stock_news_em(symbol: str, page_size: int = 20) -> List[Dict]:
    """
    获取个股相关新闻（公告）
    
    Args:
        symbol: 股票代码 (如 '600519', 'SH600519')
        page_size: 返回新闻数量
    
    Returns:
        新闻列表，每条新闻包含:
        - title: 标题
        - content: 内容摘要
        - source: 来源
        - publish_time: 发布时间
        - url: 链接
        - ann_type: 公告类型
        - art_code: 公告代码
    """
    market, code, secid = _format_stock_code(symbol)
    pure_code = code[2:]  # 去掉前缀
    
    # 构建请求参数 - 获取更多公告以便过滤
    params = {
        'cb': '',  # JSONP回调（留空则返回JSON）
        'sr': -1,  # 排序方向 -1为倒序
        'page_size': min(page_size * 3, 100),  # 获取更多数据用于过滤
        'page_index': 1,
        'client_source': 'web',
        'f_node': 0,  # 分类节点
        's_node': 0,  # 子节点
    }
    
    data = _make_request(EM_NOTICE_API, params)
    
    news_list = []
    
    if data and 'data' in data and 'list' in data['data']:
        for item in data['data']['list']:
            # 检查是否是指定股票的公告
            codes = item.get('codes', [])
            stock_codes = [c.get('stock_code', '') for c in codes]
            
            # 过滤：只返回指定股票的公告
            if pure_code not in stock_codes:
                continue
            
            # 提取公告类型
            columns = item.get('columns', [])
            ann_type = columns[0].get('column_name', '公告') if columns else '公告'
            
            # 提取股票名称
            stock_name = codes[0].get('short_name', '') if codes else ''
            
            # 构建URL
            art_code = item.get('art_code', '')
            url = f"https://data.eastmoney.com/notices/detail/{art_code}.html" if art_code else ''
            
            news_list.append({
                'title': item.get('title', ''),
                'content': '',  # 公告列表没有摘要，需要单独获取
                'source': '东方财富公告',
                'publish_time': _parse_ann_time(item.get('display_time', '')),
                'url': url,
                'ann_type': ann_type,
                'art_code': art_code,
                'code': code,
                'stock_name': stock_name,
            })
            
            # 达到请求的数量就停止
            if len(news_list) >= page_size:
                break
    
    # 如果没有找到该股票的公告，返回市场热点公告
    if not news_list:
        print(f"[!] 未找到股票 {symbol} 的公告，返回市场热点公告")
        return get_hot_news(page_size)
    
    return news_list


def get_stock_announcement(symbol: str, ann_type: str = None, page_size: int = 20) -> List[Dict]:
    """
    获取个股公告（支持按类型筛选）
    
    Args:
        symbol: 股票代码
        ann_type: 公告类型 ('年报', '半年报', '季报', '业绩预告' 等)
        page_size: 返回数量
    
    Returns:
        公告列表
    """
    market, code, secid = _format_stock_code(symbol)
    
    # 公告类型代码映射
    type_code_map = {
        '年报': '001001',
        '半年报': '001002',
        '季报': '001003',
        '业绩预告': '001004',
        '业绩快报': '001005',
    }
    
    # 构建请求参数
    params = {
        'cb': '',
        'sr': -1,
        'page_size': page_size,
        'page_index': 1,
        'client_source': 'web',
        'f_node': 0,
        's_node': 0,
        'code': symbol,
    }
    
    # 如果指定了公告类型，设置f_node
    if ann_type and ann_type in type_code_map:
        params['f_node'] = int(type_code_map[ann_type][:3])
    
    data = _make_request(EM_NOTICE_API, params)
    
    announcements = []
    
    if data and 'data' in data and 'list' in data['data']:
        for item in data['data']['list']:
            columns = item.get('columns', [])
            item_ann_type = columns[0].get('column_name', '公告') if columns else '公告'
            
            # 如果指定了类型，过滤
            if ann_type and ann_type not in item_ann_type:
                continue
            
            art_code = item.get('art_code', '')
            
            announcements.append({
                'title': item.get('title', ''),
                'ann_type': item_ann_type,
                'publish_time': _parse_ann_time(item.get('display_time', '')),
                'notice_date': item.get('notice_date', ''),
                'url': f"https://data.eastmoney.com/notices/detail/{art_code}.html",
                'art_code': art_code,
            })
    
    return announcements


# ============================================================================
# 行业新闻
# ============================================================================

def get_sector_news(sector: str = None, sector_code: str = None, page_size: int = 20) -> List[Dict]:
    """
    获取行业新闻（使用公告API，因为新闻API不稳定）
    
    Args:
        sector: 行业名称 (如 '银行', '医药', '半导体')
        sector_code: 行业代码 (如 'BK0478')
        page_size: 返回新闻数量
    
    Returns:
        新闻列表
    """
    # 东方财富行业新闻API较不稳定，使用公告API作为替代
    # 可以获取该行业龙头股的公告作为行业动态参考
    
    # 行业龙头股映射
    sector_leaders = {
        '银行': '601398',  # 工商银行
        '证券': '601688',  # 华泰证券
        '保险': '601318',  # 中国平安
        '房地产': '000002',  # 万科A
        '酿酒': '600519',  # 贵州茅台
        '医药': '600276',  # 恒瑞医药
        '汽车': '600104',  # 上汽集团
        '半导体': '603986',  # 兆易创新
        '软件': '600570',  # 恒生电子
        '电子': '000725',  # 京东方A
        '通信': '600050',  # 中国联通
        '传媒': '601801',  # 皖新传媒
        '电力': '600900',  # 长江电力
        '煤炭': '601088',  # 中国神华
        '石油': '601857',  # 中国石油
        '钢铁': '600019',  # 宝钢股份
        '有色金属': '601899',  # 紫金矿业
        '化工': '600309',  # 万华化学
        '建材': '600585',  # 海螺水泥
        '机械': '600031',  # 三一重工
    }
    
    # 获取行业龙头代码
    if sector in sector_leaders:
        leader_code = sector_leaders[sector]
        news = get_stock_news_em(leader_code, page_size=page_size)
        for n in news:
            n['sector'] = sector
        return news
    
    # 如果没有指定行业，返回热点公告
    params = {
        'cb': '',
        'sr': -1,
        'page_size': page_size,
        'page_index': 1,
        'client_source': 'web',
        'f_node': 0,
        's_node': 0,
    }
    
    data = _make_request(EM_NOTICE_API, params)
    
    news_list = []
    
    if data and 'data' in data and 'list' in data['data']:
        for item in data['data']['list']:
            columns = item.get('columns', [])
            ann_type = columns[0].get('column_name', '公告') if columns else '公告'
            
            # 提取股票信息
            codes = item.get('codes', [])
            stock_name = codes[0].get('short_name', '') if codes else ''
            stock_code = codes[0].get('stock_code', '') if codes else ''
            
            art_code = item.get('art_code', '')
            
            news_list.append({
                'title': item.get('title', ''),
                'content': '',
                'source': '东方财富公告',
                'publish_time': _parse_ann_time(item.get('display_time', '')),
                'url': f"https://data.eastmoney.com/notices/detail/{art_code}.html",
                'ann_type': ann_type,
                'stock_name': stock_name,
                'stock_code': stock_code,
                'sector': sector or '市场热点',
            })
    
    return news_list


def get_hot_news(page_size: int = 30) -> List[Dict]:
    """
    获取热门财经新闻（公告形式）
    
    Args:
        page_size: 返回新闻数量
    
    Returns:
        新闻列表
    """
    return get_sector_news(page_size=page_size)


# ============================================================================
# 资金流向
# ============================================================================

def get_money_flow(symbol: str, days: int = 5) -> Dict:
    """
    获取个股资金流向数据
    
    数据字段说明（东方财富资金流向API返回格式）:
    [0]: 日期
    [1]: 主力净流入
    [2]: 小单净流入
    [3]: 中单净流入
    [4]: 大单净流入
    [5]: 超大单净流入
    [6-12]: 其他指标
    
    Args:
        symbol: 股票代码 (如 '600519')
        days: 查询天数
    
    Returns:
        资金流向数据
    """
    market, code, secid = _format_stock_code(symbol)
    
    result = {
        'symbol': code,
        'stock_name': '',
        'main_net_inflow': 0,
        'retail_net_inflow': 0,
        'main_net_inflow_ratio': 0,
        'history': [],
        'summary': {},
    }
    
    # 获取日K线资金流向
    url = f"{EM_MONEY_FLOW_API}/daykline/get"
    params = {
        'lmt': days,
        'klt': 101,  # 日K
        'secid': secid,
        'fields1': 'f1,f2,f3,f7',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63',
    }
    
    data = _make_request(url, params)
    
    if data and 'data' in data:
        # 获取股票名称
        result['stock_name'] = data['data'].get('name', '')
        
        klines = data['data'].get('klines', [])
        history = []
        
        for kline in klines:
            if isinstance(kline, str):
                parts = kline.split(',')
                if len(parts) >= 6:
                    try:
                        # 根据东方财富API实际返回格式解析
                        # [0]=日期, [1]=主力净流入, [2]=小单净流入, [3]=中单净流入, [4]=大单净流入, [5]=超大单净流入
                        main_inflow = float(parts[1]) if parts[1] else 0
                        small_inflow = float(parts[2]) if parts[2] else 0
                        mid_inflow = float(parts[3]) if parts[3] else 0
                        big_inflow = float(parts[4]) if len(parts) > 4 and parts[4] else 0
                        super_inflow = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                        
                        entry = {
                            'date': parts[0],
                            'main_net_inflow': main_inflow,
                            'small_net_inflow': small_inflow,
                            'mid_net_inflow': mid_inflow,
                            'big_net_inflow': big_inflow,
                            'super_net_inflow': super_inflow,
                            # 散户净流入 = 小单 + 中单
                            'retail_net_inflow': small_inflow + mid_inflow,
                        }
                        history.append(entry)
                    except (ValueError, IndexError) as e:
                        print(f"[!] 解析K线数据错误: {e}")
                        continue
        
        result['history'] = history
        
        # 计算最新数据
        if history:
            latest = history[-1]
            result['main_net_inflow'] = latest.get('main_net_inflow', 0)
            result['retail_net_inflow'] = latest.get('retail_net_inflow', 0)
            
            # 计算汇总
            total_main = sum(h.get('main_net_inflow', 0) for h in history)
            total_retail = sum(h.get('retail_net_inflow', 0) for h in history)
            total_super = sum(h.get('super_net_inflow', 0) for h in history)
            total_big = sum(h.get('big_net_inflow', 0) for h in history)
            
            result['summary'] = {
                'period_days': len(history),
                'total_main_net_inflow': total_main,
                'total_retail_net_inflow': total_retail,
                'total_super_net_inflow': total_super,
                'total_big_net_inflow': total_big,
                'avg_main_net_inflow': total_main / len(history) if history else 0,
                'positive_days': sum(1 for h in history if h.get('main_net_inflow', 0) > 0),
                'negative_days': sum(1 for h in history if h.get('main_net_inflow', 0) < 0),
            }
    
    return result


def get_money_flow_realtime(symbol: str) -> Dict:
    """
    获取实时资金流向（分时数据）
    
    Args:
        symbol: 股票代码
    
    Returns:
        实时资金流向数据
    """
    market, code, secid = _format_stock_code(symbol)
    
    url = f"{EM_MONEY_FLOW_API}/kline/get"
    params = {
        'lmt': 0,  # 全部数据
        'klt': 1,  # 分时
        'secid': secid,
        'fields1': 'f1,f2,f3,f7',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
    }
    
    data = _make_request(url, params)
    
    result = {
        'symbol': code,
        'stock_name': '',
        'realtime_flow': [],
        'summary': {},
    }
    
    if data and 'data' in data:
        result['stock_name'] = data['data'].get('name', '')
        
        klines = data['data'].get('klines', [])
        flows = []
        
        for kline in klines:
            if isinstance(kline, str):
                parts = kline.split(',')
                if len(parts) >= 3:
                    try:
                        flows.append({
                            'time': parts[0],
                            'main_net_inflow': float(parts[1]) if parts[1] else 0,
                            'cumulative_main_inflow': float(parts[2]) if parts[2] else 0,
                        })
                    except ValueError:
                        continue
        
        result['realtime_flow'] = flows
        
        if flows:
            total_main = flows[-1].get('cumulative_main_inflow', 0) if flows else 0
            result['summary'] = {
                'total_main_net_inflow': total_main,
                'data_points': len(flows),
                'latest_time': flows[-1].get('time', '') if flows else '',
            }
    
    return result


# ============================================================================
# 行业资金流向
# ============================================================================

def get_sector_money_flow(sector: str = None, top_n: int = 10) -> List[Dict]:
    """
    获取行业资金流向排行
    
    Args:
        sector: 行业名称（可选，不指定则返回全部行业）
        top_n: 返回前N个行业
    
    Returns:
        行业资金流向列表
    """
    # 使用板块资金流向API - 使用HTTP而非HTTPS
    url = "http://push2.eastmoney.com/api/qt/clist/get"
    params = {
        'fid': 'f62',  # 按主力净流入排序
        'po': 1,  # 降序
        'pz': 50,
        'pn': 1,
        'np': 1,
        'fltt': 2,
        'invt': 2,
        'fs': 'm:90+t:2',  # 行业板块
        'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87',
        'ut': 'b2884a393a59ad64002292a3e90d46a5',  # 添加token
    }
    
    data = _make_request(url, params)
    
    result = []
    
    if data and 'data' in data and 'diff' in data['data']:
        for item in data['data']['diff']:
            sector_name = item.get('f14', '')
            
            # 如果指定了行业，过滤
            if sector and sector not in sector_name:
                continue
            
            result.append({
                'sector': sector_name,
                'code': item.get('f12', ''),
                'price': float(item.get('f2', 0)) / 100 if item.get('f2') else 0,
                'change_pct': float(item.get('f3', 0)) / 100 if item.get('f3') else 0,
                'main_net_inflow': float(item.get('f62', 0)),
                'main_net_inflow_ratio': float(item.get('f184', 0)) / 100 if item.get('f184') else 0,
                'super_net_inflow': float(item.get('f66', 0)),
                'big_net_inflow': float(item.get('f69', 0)),
                'mid_net_inflow': float(item.get('f72', 0)),
                'small_net_inflow': float(item.get('f75', 0)),
            })
    
    # 如果API失败，返回模拟数据
    if not result:
        print("[!] 行业资金流向API暂时不可用，返回模拟数据")
        mock_sectors = ['银行', '证券', '保险', '房地产', '医药', '汽车', '半导体', '软件', '电子', '通信']
        for i, s in enumerate(mock_sectors[:top_n]):
            result.append({
                'sector': s,
                'code': SECTOR_MAP.get(s, ''),
                'price': 0,
                'change_pct': 0,
                'main_net_inflow': 0,
                'main_net_inflow_ratio': 0,
                'super_net_inflow': 0,
                'big_net_inflow': 0,
                'mid_net_inflow': 0,
                'small_net_inflow': 0,
            })
    
    return result[:top_n] if top_n else result


# ============================================================================
# 批量获取
# ============================================================================

def get_batch_stock_news(symbols: List[str], news_per_stock: int = 5) -> Dict[str, List[Dict]]:
    """
    批量获取多只股票的新闻
    
    Args:
        symbols: 股票代码列表
        news_per_stock: 每只股票的新闻数量
    
    Returns:
        {股票代码: 新闻列表}
    """
    results = {}
    
    for symbol in symbols:
        try:
            news = get_stock_news_em(symbol, page_size=news_per_stock)
            results[symbol] = news
            
            # 随机延时防止被封
            time.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            print(f"[!] 获取 {symbol} 新闻失败: {e}")
            results[symbol] = []
    
    return results


def get_batch_money_flow(symbols: List[str], days: int = 5) -> Dict[str, Dict]:
    """
    批量获取多只股票的资金流向
    
    Args:
        symbols: 股票代码列表
        days: 查询天数
    
    Returns:
        {股票代码: 资金流向数据}
    """
    results = {}
    
    for symbol in symbols:
        try:
            flow = get_money_flow(symbol, days=days)
            results[symbol] = flow
            
            # 随机延时
            time.sleep(random.uniform(0.2, 0.5))
            
        except Exception as e:
            print(f"[!] 获取 {symbol} 资金流向失败: {e}")
            results[symbol] = {}
    
    return results


# ============================================================================
# 数据导出
# ============================================================================

def news_to_dataframe(news_list: List[Dict]) -> pd.DataFrame:
    """
    将新闻列表转换为DataFrame
    
    Args:
        news_list: 新闻列表
    
    Returns:
        DataFrame
    """
    if not news_list:
        return pd.DataFrame()
    
    df = pd.DataFrame(news_list)
    
    if 'publish_time' in df.columns:
        df['publish_time'] = pd.to_datetime(df['publish_time'])
        df = df.sort_values('publish_time', ascending=False)
    
    return df


def money_flow_to_dataframe(flow_data: Dict) -> pd.DataFrame:
    """
    将资金流向数据转换为DataFrame
    
    Args:
        flow_data: 资金流向数据
    
    Returns:
        DataFrame
    """
    history = flow_data.get('history', [])
    
    if not history:
        return pd.DataFrame()
    
    df = pd.DataFrame(history)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=False)
    
    return df


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("东方财富新闻爬虫模块测试")
    print("=" * 70)
    
    # 测试个股新闻
    print("\n📰 测试个股新闻 (贵州茅台 600519):")
    print("-" * 50)
    news = get_stock_news_em("600519", page_size=5)
    for i, n in enumerate(news, 1):
        print(f"\n{i}. {n['title']}")
        print(f"   类型: {n.get('ann_type', '公告')}")
        print(f"   时间: {n['publish_time']}")
        print(f"   链接: {n['url'][:60]}..." if len(n.get('url', '')) > 60 else f"   链接: {n.get('url', 'N/A')}")
    
    # 测试行业新闻
    print("\n\n📊 测试行业新闻 (银行):")
    print("-" * 50)
    sector_news = get_sector_news("银行", page_size=5)
    for i, n in enumerate(sector_news, 1):
        print(f"\n{i}. {n['title']}")
        print(f"   类型: {n.get('ann_type', '公告')}")
    
    # 测试资金流向
    print("\n\n💰 测试资金流向 (贵州茅台 600519):")
    print("-" * 50)
    flow = get_money_flow("600519", days=5)
    print(f"   股票代码: {flow['symbol']}")
    print(f"   股票名称: {flow.get('stock_name', 'N/A')}")
    print(f"   主力净流入: {flow['main_net_inflow']:,.0f} 元")
    print(f"   主力净流入占比: {flow['main_net_inflow_ratio']:.2f}%")
    if flow.get('summary'):
        print(f"   汇总 ({flow['summary']['period_days']}天):")
        print(f"     - 总主力净流入: {flow['summary']['total_main_net_inflow']:,.0f} 元")
        print(f"     - 净流入天数: {flow['summary']['positive_days']}")
        print(f"     - 净流出天数: {flow['summary']['negative_days']}")
    
    # 测试行业资金流向
    print("\n\n📈 测试行业资金流向排行:")
    print("-" * 50)
    sector_flows = get_sector_money_flow(top_n=5)
    for i, sf in enumerate(sector_flows, 1):
        print(f"{i}. {sf['sector']}: 主力净流入 {sf['main_net_inflow']:,.0f} 元 ({sf['change_pct']:+.2f}%)")
    
    # 测试实时资金流向
    print("\n\n⏱️ 测试实时资金流向 (600519):")
    print("-" * 50)
    realtime = get_money_flow_realtime("600519")
    if realtime.get('summary'):
        print(f"   数据点数: {realtime['summary']['data_points']}")
        print(f"   累计主力净流入: {realtime['summary']['total_main_net_inflow']:,.0f} 元")
        print(f"   最新时间: {realtime['summary']['latest_time']}")
    
    print("\n\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)