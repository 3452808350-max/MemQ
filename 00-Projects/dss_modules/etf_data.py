"""
ETF数据获取模块

支持A股主要ETF的数据获取、历史行情、实时行情和溢价率计算。

数据源：
- Akshare (东方财富/新浪) - 历史数据、ETF列表
- 新浪基金API - 实时行情、净值、溢价率

主要功能：
- get_etf_list() - 获取ETF列表
- get_etf_data(code, days) - 获取ETF历史数据  
- get_etf_realtime(code) - 实时行情
- calculate_etf_premium(code) - 计算溢价率
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union
import re
import time

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[!] akshare未安装，部分功能不可用")

# ============================================================================
# 配置
# ============================================================================

# 新浪基金API
SINA_FUND_API = "https://hq.sinajs.cn/list="

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://finance.sina.com.cn/',
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 主要ETF代码（A股）
MAJOR_ETFS = {
    # 宽基ETF
    '宽基ETF': {
        '510300': '沪深300ETF',
        '510500': '中证500ETF',
        '159915': '创业板ETF',
        '510050': '上证50ETF',
        '159949': '创业板50ETF',
        '512100': '中证1000ETF',
    },
    # 行业ETF
    '行业ETF': {
        '512880': '证券ETF',
        '512760': '芯片ETF',
        '515030': '新能源车ETF',
        '512690': '酒ETF',
        '159996': '家电ETF',
        '512170': '医疗ETF',
        '516160': '新能源ETF',
        '512480': '半导体ETF',
    },
    # 跨境ETF
    '跨境ETF': {
        '513100': '纳指ETF',
        '159920': '恒生ETF',
        '513050': '中概互联网ETF',
        '513060': '恒生医疗ETF',
        '513080': '法国CAC40ETF',
        '513030': '德国ETF',
        '513100': '纳指100ETF',
        '159941': '纳指ETF',
    },
}

# 缓存
_cache = {
    'etf_list': None,
    'etf_list_time': 0,
}

# ============================================================================
# 核心功能
# ============================================================================

def get_etf_list(
    category: Optional[str] = None,
    use_cache: bool = True,
    cache_seconds: int = 300
) -> pd.DataFrame:
    """
    获取ETF列表
    
    Args:
        category: 分类筛选，可选 '宽基ETF', '行业ETF', '跨境ETF'，None返回全部
        use_cache: 是否使用缓存
        cache_seconds: 缓存有效期（秒）
    
    Returns:
        DataFrame包含: 代码, 名称, 最新价, 涨跌额, 涨跌幅, 买入, 卖出, 昨收, 今开, 最高, 最低, 成交量, 成交额
    
    Example:
        >>> df = get_etf_list()
        >>> df = get_etf_list(category='宽基ETF')
    """
    global _cache
    
    # 如果指定了自定义分类，返回预设的主要ETF
    if category and category in MAJOR_ETFS:
        codes = list(MAJOR_ETFS[category].keys())
        return _get_etf_by_codes(codes)
    
    # 使用akshare获取完整ETF列表
    if not AKSHARE_AVAILABLE:
        print("[!] akshare不可用，返回主要ETF列表")
        if category:
            codes = list(MAJOR_ETFS.get(category, {}).keys())
            return _get_etf_by_codes(codes) if codes else pd.DataFrame()
        # 返回所有主要ETF
        all_codes = []
        for cat_codes in MAJOR_ETFS.values():
            all_codes.extend(cat_codes.keys())
        return _get_etf_by_codes(list(set(all_codes)))
    
    # 检查缓存
    now = time.time()
    if use_cache and _cache['etf_list'] is not None:
        if now - _cache['etf_list_time'] < cache_seconds:
            return _cache['etf_list']
    
    try:
        # 使用akshare获取ETF列表
        df = ak.fund_etf_category_sina()
        
        # 缓存结果
        _cache['etf_list'] = df
        _cache['etf_list_time'] = now
        
        return df
    except Exception as e:
        print(f"[!] 获取ETF列表失败: {e}")
        # 返回主要ETF作为备用
        all_codes = []
        for cat_codes in MAJOR_ETFS.values():
            all_codes.extend(cat_codes.keys())
        return _get_etf_by_codes(list(set(all_codes)))


def _get_etf_by_codes(codes: List[str]) -> pd.DataFrame:
    """根据代码列表获取ETF行情数据"""
    results = []
    
    # 分批请求（每批最多20个）
    batch_size = 20
    for i in range(0, len(codes), batch_size):
        batch_codes = codes[i:i+batch_size]
        try:
            url = SINA_FUND_API + ','.join([f'of{c}' for c in batch_codes])
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.encoding = 'gbk'
            
            for line in r.text.strip().split('\n'):
                match = re.match(r'var hq_str_of(\d+)=\"(.*)\";', line.strip())
                if match:
                    code = match.group(1)
                    data = match.group(2).split(',')
                    if len(data) >= 13:
                        results.append({
                            '代码': code,
                            '名称': data[0],
                            '最新价': float(data[3]) if data[3] else 0,
                            '涨跌额': 0,  # 需要计算
                            '涨跌幅': float(data[4]) if data[4] else 0,
                            '买入': float(data[3]) if data[3] else 0,
                            '卖出': float(data[3]) if data[3] else 0,
                            '昨收': float(data[3]) / (1 + float(data[4])/100) if data[3] and data[4] else 0,
                            '今开': 0,
                            '最高': 0,
                            '最低': 0,
                            '成交量': 0,
                            '成交额': 0,
                            '净值': float(data[1]) if data[1] else 0,
                            '累计净值': float(data[2]) if data[2] else 0,
                        })
        except Exception as e:
            print(f"[!] 批量获取ETF数据失败: {e}")
    
    return pd.DataFrame(results)


def get_etf_data(
    code: str,
    days: int = 365,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adjust: str = 'qfq',
    max_retries: int = 3
) -> pd.DataFrame:
    """
    获取ETF历史数据
    
    Args:
        code: ETF代码，如 '510300'
        days: 获取最近N天的数据（与start_date/end_date二选一）
        start_date: 开始日期 'YYYYMMDD'
        end_date: 结束日期 'YYYYMMDD'
        adjust: 复权类型 'qfq'-前复权, 'hfq'-后复权, ''-不复权
        max_retries: 最大重试次数
    
    Returns:
        DataFrame包含: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
    
    Example:
        >>> df = get_etf_data('510300', days=180)
        >>> df = get_etf_data('510300', start_date='20240101', end_date='20241231')
    """
    if not AKSHARE_AVAILABLE:
        raise ImportError("akshare未安装，无法获取历史数据")
    
    # 计算日期范围
    if not start_date or not end_date:
        end = datetime.now()
        start = end - timedelta(days=days)
        start_date = start.strftime('%Y%m%d')
        end_date = end.strftime('%Y%m%d')
    
    # 重试机制
    last_error = None
    for attempt in range(max_retries):
        try:
            df = ak.fund_etf_hist_em(
                symbol=code,
                period='daily',
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if df is not None and not df.empty:
                # 标准化列名
                column_map = {
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'amount',
                    '振幅': 'amplitude',
                    '涨跌幅': 'pct_change',
                    '涨跌额': 'change',
                    '换手率': 'turnover',
                }
                df = df.rename(columns=column_map)
                
                # 添加代码列
                df['code'] = code
                
                return df
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
    
    # 所有重试都失败
    print(f"[!] 获取ETF {code} 历史数据失败 (重试{max_retries}次): {last_error}")
    return pd.DataFrame()


def get_etf_realtime(
    code: Union[str, List[str]],
    include_nav: bool = True
) -> pd.DataFrame:
    """
    获取ETF实时行情
    
    Args:
        code: ETF代码或代码列表，如 '510300' 或 ['510300', '510500']
        include_nav: 是否包含净值信息
    
    Returns:
        DataFrame包含: 代码, 名称, 最新价, 涨跌幅, 净值, 累计净值, 溢价率, 数据日期
    
    Example:
        >>> df = get_etf_realtime('510300')
        >>> df = get_etf_realtime(['510300', '510500', '159915'])
    """
    # 标准化输入
    if isinstance(code, str):
        codes = [code]
    else:
        codes = code
    
    results = []
    
    # 分批请求（每批最多20个）
    batch_size = 20
    for i in range(0, len(codes), batch_size):
        batch_codes = codes[i:i+batch_size]
        
        try:
            url = SINA_FUND_API + ','.join([f'of{c}' for c in batch_codes])
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.encoding = 'gbk'
            
            for line in r.text.strip().split('\n'):
                match = re.match(r'var hq_str_of(\d+)=\"(.*)\";', line.strip())
                if match:
                    code = match.group(1)
                    data = match.group(2).split(',')
                    
                    if len(data) >= 6:
                        name = data[0]
                        nav = float(data[1]) if data[1] else 0
                        acc_nav = float(data[2]) if data[2] else 0
                        price = float(data[3]) if data[3] else 0
                        change_pct = float(data[4]) if data[4] else 0
                        date = data[5] if len(data) > 5 else ''
                        
                        # 计算溢价率
                        premium = (price - nav) / nav * 100 if nav > 0 else 0
                        
                        results.append({
                            '代码': code,
                            '名称': name,
                            '最新价': price,
                            '涨跌幅': change_pct,
                            '净值': nav if include_nav else None,
                            '累计净值': acc_nav if include_nav else None,
                            '溢价率': round(premium, 2) if include_nav else None,
                            '数据日期': date,
                        })
        except Exception as e:
            print(f"[!] 获取ETF实时数据失败: {e}")
    
    return pd.DataFrame(results)


def calculate_etf_premium(
    code: Union[str, List[str]],
    use_realtime: bool = True
) -> pd.DataFrame:
    """
    计算ETF溢价率
    
    溢价率 = (市价 - 净值) / 净值 * 100%
    - 正值表示溢价（市价高于净值）
    - 负值表示折价（市价低于净值）
    
    Args:
        code: ETF代码或代码列表
        use_realtime: 是否使用实时数据（False则使用最新收盘数据）
    
    Returns:
        DataFrame包含: 代码, 名称, 市价, 净值, 溢价率, 溢价额
    
    Example:
        >>> df = calculate_etf_premium('510300')
        >>> df = calculate_etf_premium(['510300', '510500'])
    """
    # 获取实时数据
    df = get_etf_realtime(code, include_nav=True)
    
    if df.empty:
        return df
    
    # 添加溢价额
    df['溢价额'] = df['最新价'] - df['净值']
    
    # 重新排列列
    cols = ['代码', '名称', '最新价', '净值', '溢价额', '溢价率', '数据日期']
    df = df[[c for c in cols if c in df.columns]]
    
    return df


# ============================================================================
# 扩展功能
# ============================================================================

def get_major_etfs_summary() -> pd.DataFrame:
    """
    获取主要ETF概览（宽基、行业、跨境）
    
    Returns:
        DataFrame包含所有主要ETF的实时行情和溢价率
    """
    all_codes = []
    for category, etfs in MAJOR_ETFS.items():
        all_codes.extend(etfs.keys())
    
    # 去重
    all_codes = list(set(all_codes))
    
    # 获取实时数据
    df = get_etf_realtime(all_codes)
    
    if df.empty:
        return df
    
    # 添加分类
    df['分类'] = df['代码'].apply(lambda x: _get_category(x))
    
    # 添加完整名称
    df['完整名称'] = df['代码'].apply(lambda x: _get_full_name(x))
    
    # 重排列
    cols = ['分类', '代码', '完整名称', '名称', '最新价', '涨跌幅', '净值', '溢价率', '数据日期']
    df = df[[c for c in cols if c in df.columns]]
    
    # 按分类排序
    category_order = ['宽基ETF', '行业ETF', '跨境ETF']
    df['分类'] = pd.Categorical(df['分类'], categories=category_order, ordered=True)
    df = df.sort_values('分类').reset_index(drop=True)
    
    return df


def _get_category(code: str) -> str:
    """获取ETF分类"""
    for category, etfs in MAJOR_ETFS.items():
        if code in etfs:
            return category
    return '其他'


def _get_full_name(code: str) -> str:
    """获取ETF完整名称"""
    for category, etfs in MAJOR_ETFS.items():
        if code in etfs:
            return etfs[code]
    return ''


def get_etf_premium_alert(
    threshold: float = 1.0,
    etf_list: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    获取溢价率异常的ETF
    
    Args:
        threshold: 溢价率阈值（绝对值），默认1%
        etf_list: 要检查的ETF列表，默认检查所有主要ETF
    
    Returns:
        超过阈值的ETF列表
    """
    if etf_list is None:
        etf_list = []
        for etfs in MAJOR_ETFS.values():
            etf_list.extend(etfs.keys())
        etf_list = list(set(etf_list))
    
    df = calculate_etf_premium(etf_list)
    
    if df.empty:
        return df
    
    # 筛选超过阈值的
    alert_df = df[df['溢价率'].abs() >= threshold].copy()
    alert_df = alert_df.sort_values('溢价率', key=abs, ascending=False)
    
    return alert_df


def get_etf_pair_spread(
    code1: str,
    code2: str,
    days: int = 30
) -> pd.DataFrame:
    """
    获取两个ETF的价差/比率（用于配对交易）
    
    Args:
        code1: 第一个ETF代码
        code2: 第二个ETF代码
        days: 历史天数
    
    Returns:
        DataFrame包含两个ETF的收盘价和价差/比率
    """
    # 获取历史数据
    df1 = get_etf_data(code1, days=days)
    df2 = get_etf_data(code2, days=days)
    
    if df1.empty or df2.empty:
        print("[!] 获取历史数据失败")
        return pd.DataFrame()
    
    # 合并
    df = pd.merge(
        df1[['date', 'close']],
        df2[['date', 'close']],
        on='date',
        suffixes=(f'_{code1}', f'_{code2}')
    )
    
    # 计算价差和比率
    df['spread'] = df[f'close_{code1}'] - df[f'close_{code2}']
    df['ratio'] = df[f'close_{code1}'] / df[f'close_{code2}']
    
    # 计算均值和标准差
    df['spread_mean'] = df['spread'].rolling(20).mean()
    df['spread_std'] = df['spread'].rolling(20).std()
    df['zscore'] = (df['spread'] - df['spread_mean']) / df['spread_std']
    
    return df


# ============================================================================
# 工具函数
# ============================================================================

def search_etf(keyword: str) -> pd.DataFrame:
    """
    搜索ETF
    
    Args:
        keyword: 搜索关键词（名称或代码）
    
    Returns:
        匹配的ETF列表
    """
    df = get_etf_list()
    
    if df.empty:
        return df
    
    # 搜索
    mask = (
        df['名称'].str.contains(keyword, case=False, na=False) |
        df['代码'].str.contains(keyword, case=False, na=False)
    )
    
    return df[mask]


def get_etf_info(code: str) -> Dict:
    """
    获取单个ETF详细信息
    
    Args:
        code: ETF代码
    
    Returns:
        ETF详细信息字典
    """
    # 获取实时数据
    df = get_etf_realtime(code)
    
    if df.empty:
        return {}
    
    row = df.iloc[0]
    
    # 获取分类和完整名称
    category = _get_category(code)
    full_name = _get_full_name(code)
    
    info = {
        '代码': code,
        '名称': row['名称'],
        '完整名称': full_name,
        '分类': category,
        '最新价': row['最新价'],
        '涨跌幅': row['涨跌幅'],
        '净值': row['净值'],
        '累计净值': row['累计净值'],
        '溢价率': row['溢价率'],
        '数据日期': row['数据日期'],
    }
    
    return info


# ============================================================================
# 测试
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ETF数据模块测试")
    print("=" * 60)
    
    # 1. 获取主要ETF概览
    print("\n1. 主要ETF概览:")
    df = get_major_etfs_summary()
    if not df.empty:
        print(df.to_string(index=False))
    
    # 2. 获取历史数据
    print("\n2. 沪深300ETF历史数据(最近5天):")
    df = get_etf_data('510300', days=30)
    if not df.empty:
        print(df.tail(5).to_string(index=False))
    
    # 3. 计算溢价率
    print("\n3. 溢价率计算:")
    df = calculate_etf_premium(['510300', '510500', '159915'])
    if not df.empty:
        print(df.to_string(index=False))
    
    # 4. 溢价率异常提醒
    print("\n4. 溢价率异常(>0.5%):")
    df = get_etf_premium_alert(threshold=0.5)
    if not df.empty:
        print(df.to_string(index=False))
    else:
        print("无异常")