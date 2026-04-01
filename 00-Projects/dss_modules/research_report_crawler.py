"""
研报摘要爬虫模块
从东方财富获取股票研报摘要、评级和目标价

数据来源：
- 东方财富研报中心: https://data.eastmoney.com/report/
- API: https://reportapi.eastmoney.com/report/list

功能：
- get_research_reports(symbol) - 获取研报摘要
- parse_rating() - 解析评级(买入/增持/中性)
- parse_target_price() - 解析目标价
- get_rating_summary() - 获取评级汇总统计
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union, Tuple
import time
import random
import re
import json
from collections import Counter

# ============================================================================
# 配置
# ============================================================================

# 东方财富研报API
EM_REPORT_API = "https://reportapi.eastmoney.com/report/list"
EM_REPORT_DETAIL_API = "https://data.eastmoney.com/report/zw_macresearch"

# 反爬虫配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'https://data.eastmoney.com/',
}

# 评级映射
RATING_MAP = {
    '007': {'name': '买入', 'value': 3, 'direction': 'positive'},
    '006': {'name': '增持', 'value': 2, 'direction': 'positive'},
    '005': {'name': '持有', 'value': 1, 'direction': 'neutral'},
    '004': {'name': '中性', 'value': 1, 'direction': 'neutral'},
    '003': {'name': '减持', 'value': -1, 'direction': 'negative'},
    '002': {'name': '卖出', 'value': -2, 'direction': 'negative'},
    '001': {'name': '强卖', 'value': -3, 'direction': 'negative'},
}

# 评级名称标准化映射
RATING_NORMALIZE_MAP = {
    '买入': '买入',
    '强推': '买入',
    '推荐': '买入',
    '增持': '增持',
    '优于大市': '增持',
    '跑赢大市': '增持',
    '持有': '持有',
    '中性': '中性',
    '减持': '减持',
    '卖出': '卖出',
    '区间操作': '持有',
    '观望': '中性',
    '谨慎增持': '增持',
    '谨慎推荐': '增持',
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


def _format_stock_code(symbol: str) -> Tuple[str, str]:
    """
    格式化股票代码
    
    Args:
        symbol: 股票代码 (如 '600519', 'SH600519', '贵州茅台')
    
    Returns:
        (市场代码, 纯股票代码)
    """
    symbol = str(symbol).upper().strip()
    
    # 已经带前缀
    if symbol.startswith('SH'):
        return 'SH', symbol[2:]
    elif symbol.startswith('SZ'):
        return 'SZ', symbol[2:]
    elif symbol.startswith('BJ'):
        return 'BJ', symbol[2:]
    
    # 判断市场
    if symbol.startswith(('6', '9')):
        return 'SH', symbol
    elif symbol.startswith(('0', '1', '2', '3')):
        return 'SZ', symbol
    elif symbol.startswith(('4', '8')):
        return 'BJ', symbol
    else:
        return 'SH', symbol  # 默认上海


def _parse_publish_date(date_str: str) -> datetime:
    """
    解析发布日期
    
    Args:
        date_str: 日期字符串
    
    Returns:
        datetime对象
    """
    if not date_str:
        return datetime.now()
    
    # 尝试多种格式
    formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str[:26] if 'f' in fmt else date_str[:19], fmt)
        except ValueError:
            continue
    
    return datetime.now()


# ============================================================================
# 核心功能
# ============================================================================

def get_research_reports(
    symbol: str,
    page_size: int = 20,
    days: int = None,
    rating_filter: str = None
) -> List[Dict]:
    """
    获取股票研报摘要
    
    Args:
        symbol: 股票代码 (如 '600519', 'SH600519', '比亚迪')
        page_size: 返回研报数量 (默认20)
        days: 限制天数 (如30表示最近30天)
        rating_filter: 评级过滤 ('买入', '增持', '中性', '减持', '卖出')
    
    Returns:
        研报列表，每条研报包含:
        - title: 标题
        - stock_name: 股票名称
        - stock_code: 股票代码
        - broker: 券商名称
        - broker_short: 券商简称
        - publish_date: 发布日期
        - rating: 评级 (买入/增持/中性/减持/卖出)
        - rating_value: 评级值 (3=买入, 2=增持, 1=中性, -1=减持, -2=卖出)
        - target_price: 目标价
        - target_price_low: 目标价下限
        - eps_next_year: 预测明年EPS
        - pe_next_year: 预测明年PE
        - researcher: 研究员
        - report_type: 研报类型
        - pages: 页数
        - pdf_url: PDF下载链接
    """
    # 格式化股票代码
    market, pure_code = _format_stock_code(symbol)
    
    # 构建请求参数
    params = {
        'cb': '',  # JSONP回调（留空则返回JSON）
        'pageNo': 1,
        'pageSize': min(page_size * 2, 100),  # 获取更多数据用于过滤
        'code': pure_code,
        'codeType': 1,  # 1=股票代码
        'qType': 0,  # 0=全部
        'beginTime': '',
        'endTime': '',
        'lastUpdateTime': '',
    }
    
    # 如果指定了天数，设置时间范围
    if days:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        params['beginTime'] = start_date
        params['endTime'] = end_date
    
    data = _make_request(EM_REPORT_API, params)
    
    reports = []
    
    if data and 'data' in data and data['data']:
        for item in data['data']:
            # 解析评级
            rating_code = item.get('emRatingCode', '')
            rating_info = RATING_MAP.get(rating_code, {})
            rating_name = rating_info.get('name', item.get('emRatingName', '未评级'))
            
            # 评级过滤
            if rating_filter:
                filter_normalized = RATING_NORMALIZE_MAP.get(rating_filter, rating_filter)
                rating_normalized = RATING_NORMALIZE_MAP.get(rating_name, rating_name)
                if filter_normalized != rating_normalized:
                    continue
            
            # 解析目标价
            target_price = item.get('indvAimPriceT', '')
            target_price = float(target_price) if target_price else None
            
            target_price_low = item.get('indvAimPriceL', '')
            target_price_low = float(target_price_low) if target_price_low else None
            
            # 解析EPS和PE
            eps_next_year = item.get('predictNextYearEps', '')
            eps_next_year = float(eps_next_year) if eps_next_year else None
            
            pe_next_year = item.get('predictNextYearPe', '')
            pe_next_year = float(pe_next_year) if pe_next_year else None
            
            # 构建PDF下载URL
            encode_url = item.get('encodeUrl', '')
            pdf_url = f"https://data.eastmoney.com/report/zw_macresearch?code={encode_url}" if encode_url else ''
            
            # 发布日期
            publish_date = _parse_publish_date(item.get('publishDate', ''))
            
            # 时间过滤
            if days:
                days_ago = datetime.now() - timedelta(days=days)
                if publish_date < days_ago:
                    continue
            
            report = {
                'title': item.get('title', ''),
                'stock_name': item.get('stockName', ''),
                'stock_code': item.get('stockCode', ''),
                'broker': item.get('orgName', ''),
                'broker_short': item.get('orgSName', ''),
                'publish_date': publish_date,
                'publish_date_str': publish_date.strftime('%Y-%m-%d'),
                'rating': rating_name,
                'rating_value': rating_info.get('value', 0),
                'rating_direction': rating_info.get('direction', 'neutral'),
                'target_price': target_price,
                'target_price_low': target_price_low,
                'eps_next_year': eps_next_year,
                'pe_next_year': pe_next_year,
                'researcher': item.get('researcher', ''),
                'report_type': '深度报告' if item.get('column', '') == '002004001002' else '研究报告',
                'pages': item.get('attachPages', 0),
                'file_size': item.get('attachSize', 0),
                'pdf_url': pdf_url,
                'info_code': item.get('infoCode', ''),
            }
            
            reports.append(report)
            
            # 达到请求数量就停止
            if len(reports) >= page_size:
                break
    
    return reports


def parse_rating(rating_str: str) -> Dict:
    """
    解析评级字符串
    
    Args:
        rating_str: 评级字符串 (如 '买入', '增持', '中性')
    
    Returns:
        标准化的评级信息:
        - name: 标准化名称 (买入/增持/中性/减持/卖出)
        - value: 数值 (3=买入, 2=增持, 1=中性, -1=减持, -2=卖出)
        - direction: 方向 ('positive', 'neutral', 'negative')
        - description: 描述
    """
    # 标准化评级名称
    normalized = RATING_NORMALIZE_MAP.get(rating_str, rating_str)
    
    # 根据标准化名称确定值
    rating_values = {
        '买入': {'value': 3, 'direction': 'positive', 'description': '强烈推荐买入'},
        '增持': {'value': 2, 'direction': 'positive', 'description': '建议增持'},
        '持有': {'value': 1, 'direction': 'neutral', 'description': '建议持有'},
        '中性': {'value': 1, 'direction': 'neutral', 'description': '评级中性'},
        '减持': {'value': -1, 'direction': 'negative', 'description': '建议减持'},
        '卖出': {'value': -2, 'direction': 'negative', 'description': '建议卖出'},
    }
    
    info = rating_values.get(normalized, {'value': 0, 'direction': 'unknown', 'description': '未评级'})
    
    return {
        'name': normalized,
        'value': info['value'],
        'direction': info['direction'],
        'description': info['description'],
    }


def parse_target_price(report: Dict) -> Dict:
    """
    解析目标价信息
    
    Args:
        report: 研报字典
    
    Returns:
        目标价信息:
        - target_price: 目标价
        - target_price_low: 目标价下限
        - price_range: 价格区间 (如有上下限)
        - has_target: 是否有目标价
        - upside: 上涨空间 (需要当前价格)
    """
    target_price = report.get('target_price')
    target_price_low = report.get('target_price_low')
    
    result = {
        'target_price': target_price,
        'target_price_low': target_price_low,
        'price_range': None,
        'has_target': target_price is not None or target_price_low is not None,
        'upside': None,
        'upside_pct': None,
    }
    
    # 如果有价格区间
    if target_price and target_price_low and target_price != target_price_low:
        result['price_range'] = f"{target_price_low:.2f} - {target_price:.2f}"
    
    return result


def get_rating_summary(symbol: str, days: int = 90) -> Dict:
    """
    获取评级汇总统计
    
    Args:
        symbol: 股票代码
        days: 统计天数 (默认90天)
    
    Returns:
        评级汇总:
        - total_reports: 研报总数
        - buy_count: 买入数量
        - overweight_count: 增持数量
        - neutral_count: 中性数量
        - sell_count: 卖出数量
        - avg_rating: 平均评级值
        - consensus: 综合评级 (强烈推荐/推荐/中性/谨慎/回避)
        - target_price_avg: 平均目标价
        - target_price_median: 目标价中位数
        - latest_reports: 最近研报列表
    """
    # 获取最近N天的研报
    reports = get_research_reports(symbol, page_size=50, days=days)
    
    if not reports:
        return {
            'total_reports': 0,
            'buy_count': 0,
            'overweight_count': 0,
            'neutral_count': 0,
            'sell_count': 0,
            'avg_rating': 0,
            'consensus': '无数据',
            'target_price_avg': None,
            'target_price_median': None,
            'latest_reports': [],
        }
    
    # 统计评级分布
    rating_counter = Counter(r['rating'] for r in reports)
    
    # 计算各类型数量
    buy_count = rating_counter.get('买入', 0)
    overweight_count = rating_counter.get('增持', 0)
    neutral_count = rating_counter.get('中性', 0) + rating_counter.get('持有', 0)
    sell_count = rating_counter.get('减持', 0) + rating_counter.get('卖出', 0)
    
    # 计算平均评级
    rating_values = [r['rating_value'] for r in reports if r['rating_value'] != 0]
    avg_rating = sum(rating_values) / len(rating_values) if rating_values else 0
    
    # 确定综合评级
    if avg_rating >= 2.5:
        consensus = '强烈推荐'
    elif avg_rating >= 1.5:
        consensus = '推荐'
    elif avg_rating >= 0.5:
        consensus = '中性偏多'
    elif avg_rating >= -0.5:
        consensus = '中性'
    elif avg_rating >= -1.5:
        consensus = '谨慎'
    else:
        consensus = '回避'
    
    # 计算目标价统计
    target_prices = [r['target_price'] for r in reports if r['target_price']]
    target_price_avg = sum(target_prices) / len(target_prices) if target_prices else None
    target_price_median = sorted(target_prices)[len(target_prices)//2] if target_prices else None
    
    return {
        'total_reports': len(reports),
        'buy_count': buy_count,
        'overweight_count': overweight_count,
        'neutral_count': neutral_count,
        'sell_count': sell_count,
        'avg_rating': round(avg_rating, 2),
        'consensus': consensus,
        'target_price_avg': round(target_price_avg, 2) if target_price_avg else None,
        'target_price_median': round(target_price_median, 2) if target_price_median else None,
        'rating_distribution': dict(rating_counter),
        'latest_reports': reports[:5],  # 最近5条研报
        'period_days': days,
    }


def get_hot_reports(page_size: int = 20) -> List[Dict]:
    """
    获取热门研报（全市场）
    
    Args:
        page_size: 返回数量
    
    Returns:
        热门研报列表
    """
    params = {
        'cb': '',
        'pageNo': 1,
        'pageSize': page_size,
        'code': '',
        'codeType': '',
        'qType': 0,
        'beginTime': '',
        'endTime': '',
        'lastUpdateTime': '',
    }
    
    data = _make_request(EM_REPORT_API, params)
    
    reports = []
    
    if data and 'data' in data and data['data']:
        for item in data['data']:
            rating_code = item.get('emRatingCode', '')
            rating_info = RATING_MAP.get(rating_code, {})
            
            target_price = item.get('indvAimPriceT', '')
            target_price = float(target_price) if target_price else None
            
            publish_date = _parse_publish_date(item.get('publishDate', ''))
            
            encode_url = item.get('encodeUrl', '')
            pdf_url = f"https://data.eastmoney.com/report/zw_macresearch?code={encode_url}" if encode_url else ''
            
            report = {
                'title': item.get('title', ''),
                'stock_name': item.get('stockName', ''),
                'stock_code': item.get('stockCode', ''),
                'broker': item.get('orgName', ''),
                'broker_short': item.get('orgSName', ''),
                'publish_date': publish_date,
                'publish_date_str': publish_date.strftime('%Y-%m-%d'),
                'rating': rating_info.get('name', item.get('emRatingName', '未评级')),
                'rating_value': rating_info.get('value', 0),
                'target_price': target_price,
                'researcher': item.get('researcher', ''),
                'pdf_url': pdf_url,
            }
            
            reports.append(report)
    
    return reports


def search_reports_by_keyword(keyword: str, page_size: int = 20) -> List[Dict]:
    """
    按关键词搜索研报
    
    Args:
        keyword: 搜索关键词
        page_size: 返回数量
    
    Returns:
        匹配的研报列表
    """
    # 先获取热门研报，再在本地过滤
    # 注：东方财富研报API不支持直接关键词搜索
    all_reports = get_hot_reports(page_size=100)
    
    # 过滤包含关键词的研报
    keyword_lower = keyword.lower()
    matched = []
    
    for report in all_reports:
        title = report.get('title', '').lower()
        stock_name = report.get('stock_name', '').lower()
        
        if keyword_lower in title or keyword_lower in stock_name:
            matched.append(report)
            
            if len(matched) >= page_size:
                break
    
    return matched


# ============================================================================
# 批量获取
# ============================================================================

def get_batch_reports(
    symbols: List[str],
    reports_per_stock: int = 5
) -> Dict[str, List[Dict]]:
    """
    批量获取多只股票的研报
    
    Args:
        symbols: 股票代码列表
        reports_per_stock: 每只股票的研报数量
    
    Returns:
        {股票代码: 研报列表}
    """
    results = {}
    
    for symbol in symbols:
        try:
            reports = get_research_reports(symbol, page_size=reports_per_stock)
            results[symbol] = reports
            
            # 随机延时防止被封
            time.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            print(f"[!] 获取 {symbol} 研报失败: {e}")
            results[symbol] = []
    
    return results


def get_batch_rating_summary(
    symbols: List[str],
    days: int = 90
) -> Dict[str, Dict]:
    """
    批量获取多只股票的评级汇总
    
    Args:
        symbols: 股票代码列表
        days: 统计天数
    
    Returns:
        {股票代码: 评级汇总}
    """
    results = {}
    
    for symbol in symbols:
        try:
            summary = get_rating_summary(symbol, days=days)
            results[symbol] = summary
            
            # 随机延时
            time.sleep(random.uniform(0.3, 0.8))
            
        except Exception as e:
            print(f"[!] 获取 {symbol} 评级汇总失败: {e}")
            results[symbol] = {}
    
    return results


# ============================================================================
# 数据导出
# ============================================================================

def reports_to_dataframe(reports: List[Dict]) -> pd.DataFrame:
    """
    将研报列表转换为DataFrame
    
    Args:
        reports: 研报列表
    
    Returns:
        DataFrame
    """
    if not reports:
        return pd.DataFrame()
    
    df = pd.DataFrame(reports)
    
    if 'publish_date' in df.columns:
        df['publish_date'] = pd.to_datetime(df['publish_date'])
        df = df.sort_values('publish_date', ascending=False)
    
    # 选择关键列
    columns = [
        'stock_name', 'stock_code', 'title', 'broker_short',
        'rating', 'target_price', 'publish_date_str', 'researcher'
    ]
    
    available_cols = [c for c in columns if c in df.columns]
    
    return df[available_cols]


def summary_to_dataframe(summaries: Dict[str, Dict]) -> pd.DataFrame:
    """
    将评级汇总字典转换为DataFrame
    
    Args:
        summaries: {股票代码: 评级汇总}
    
    Returns:
        DataFrame
    """
    rows = []
    
    for symbol, summary in summaries.items():
        if summary:
            rows.append({
                'stock_code': symbol,
                'total_reports': summary.get('total_reports', 0),
                'buy_count': summary.get('buy_count', 0),
                'overweight_count': summary.get('overweight_count', 0),
                'neutral_count': summary.get('neutral_count', 0),
                'sell_count': summary.get('sell_count', 0),
                'avg_rating': summary.get('avg_rating', 0),
                'consensus': summary.get('consensus', ''),
                'target_price_avg': summary.get('target_price_avg'),
                'target_price_median': summary.get('target_price_median'),
            })
    
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    df = df.sort_values('avg_rating', ascending=False)
    
    return df


# ============================================================================
# 格式化输出
# ============================================================================

def format_report_brief(report: Dict) -> str:
    """
    格式化单条研报摘要
    
    Args:
        report: 研报字典
    
    Returns:
        格式化的文本
    """
    lines = [
        f"📄 {report.get('title', 'N/A')}",
        f"   股票: {report.get('stock_name', 'N/A')} ({report.get('stock_code', 'N/A')})",
        f"   券商: {report.get('broker_short', 'N/A')}",
        f"   评级: {report.get('rating', 'N/A')}",
    ]
    
    if report.get('target_price'):
        lines.append(f"   目标价: {report['target_price']:.2f}元")
    
    lines.append(f"   发布: {report.get('publish_date_str', 'N/A')}")
    
    if report.get('researcher'):
        lines.append(f"   研究员: {report['researcher']}")
    
    return '\n'.join(lines)


def format_summary_brief(summary: Dict, symbol: str = '') -> str:
    """
    格式化评级汇总摘要
    
    Args:
        summary: 评级汇总字典
        symbol: 股票代码
    
    Returns:
        格式化的文本
    """
    if not summary or summary.get('total_reports', 0) == 0:
        return f"📊 {symbol} 研报统计: 无数据"
    
    lines = [
        f"📊 {symbol} 研报统计 (最近{summary.get('period_days', 90)}天)",
        f"   研报总数: {summary.get('total_reports', 0)}",
        f"   评级分布: 买入{summary.get('buy_count', 0)} | 增持{summary.get('overweight_count', 0)} | 中性{summary.get('neutral_count', 0)} | 卖出{summary.get('sell_count', 0)}",
        f"   平均评级: {summary.get('avg_rating', 0):.2f}",
        f"   综合评价: {summary.get('consensus', 'N/A')}",
    ]
    
    if summary.get('target_price_avg'):
        lines.append(f"   平均目标价: {summary['target_price_avg']:.2f}元")
    
    if summary.get('target_price_median'):
        lines.append(f"   目标价中位数: {summary['target_price_median']:.2f}元")
    
    return '\n'.join(lines)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("研报摘要爬虫模块测试")
    print("=" * 70)
    
    # 测试获取研报
    print("\n📰 测试获取研报 (贵州茅台 600519):")
    print("-" * 50)
    reports = get_research_reports("600519", page_size=5)
    for i, r in enumerate(reports, 1):
        print(f"\n{i}. {format_report_brief(r)}")
    
    # 测试评级汇总
    print("\n\n📊 测试评级汇总 (贵州茅台 600519):")
    print("-" * 50)
    summary = get_rating_summary("600519", days=180)
    print(format_summary_brief(summary, "贵州茅台"))
    
    # 测试比亚迪
    print("\n\n📰 测试获取研报 (比亚迪 002594):")
    print("-" * 50)
    reports_byd = get_research_reports("002594", page_size=5)
    for i, r in enumerate(reports_byd, 1):
        print(f"\n{i}. {r['title']}")
        print(f"   券商: {r['broker_short']} | 评级: {r['rating']}", end='')
        if r.get('target_price'):
            print(f" | 目标价: {r['target_price']:.2f}")
        else:
            print()
    
    # 测试评级解析
    print("\n\n🔧 测试评级解析:")
    print("-" * 50)
    test_ratings = ['买入', '增持', '中性', '减持', '卖出', '优于大市']
    for rating in test_ratings:
        parsed = parse_rating(rating)
        print(f"   {rating} -> {parsed['name']} (值:{parsed['value']}, 方向:{parsed['direction']})")
    
    # 测试热门研报
    print("\n\n🔥 测试热门研报:")
    print("-" * 50)
    hot = get_hot_reports(page_size=5)
    for i, r in enumerate(hot, 1):
        print(f"\n{i}. {r['title']}")
        print(f"   {r['stock_name']} ({r['stock_code']}) - {r['broker_short']} - {r['rating']}")
    
    # 测试DataFrame导出
    print("\n\n📋 测试DataFrame导出:")
    print("-" * 50)
    df = reports_to_dataframe(reports)
    print(df.to_string())
    
    print("\n\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)