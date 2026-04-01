"""
新浪财经新闻爬虫模块
从新浪财经获取股票相关新闻和热点财经新闻

API 端点：
- 热点财经新闻: https://feed.mix.sina.com.cn/api/roll/get
- 股票相关新闻: 通过关键词筛选或股票页面获取
"""
import requests
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from functools import lru_cache
import re
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# 新浪财经 API 配置
SINA_FINANCE_BASE = "https://finance.sina.com.cn"
SINA_FEED_BASE = "https://feed.mix.sina.com.cn/api/roll/get"
SINA_STOCK_NEWS_BASE = "https://finance.sina.com.cn/realstock/company"

# 新闻分类 LID 映射
NEWS_CATEGORIES = {
    'hot': 2516,        # 热点财经
    'stock': 2517,      # 股票新闻
    'fund': 2520,       # 基金新闻
    'forex': 2521,      # 外汇新闻
    'futures': 2522,    # 期货新闻
    'bond': 2523,       # 债券新闻
    'usstock': 2518,    # 美股新闻
    'hkstock': 2519,    # 港股新闻
}

# 默认请求头
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://finance.sina.com.cn/',
}

# 缓存配置
CACHE_EXPIRE_SECONDS = 300  # 5分钟缓存

# 股票名称映射（常见A股）
STOCK_NAME_MAP = {
    'sh600519': '贵州茅台',
    'sh600036': '招商银行',
    'sh601318': '中国平安',
    'sh600276': '恒瑞医药',
    'sz000858': '五粮液',
    'sz000333': '美的集团',
    'sz000001': '平安银行',
    'sz002594': '比亚迪',
    'sz300750': '宁德时代',
    'sh600900': '长江电力',
    'sh601166': '兴业银行',
    'sh601288': '农业银行',
    'sh601398': '工商银行',
    'sh601939': '建设银行',
    'sh600030': '中信证券',
    'sh600887': '伊利股份',
    'sz002415': '海康威视',
    'sz002475': '立讯精密',
    'sz300059': '东方财富',
    'sz300015': '爱尔眼科',
    'sh600016': '民生银行',
    'sh601888': '中国中免',
    'sh601012': '隆基绿能',
    'sz002304': '洋河股份',
    'sz000002': '万科A',
    'sz000651': '格力电器',
    'sz002352': '顺丰控股',
    'sh688981': '中芯国际',
    'sz002714': '牧原股份',
    'sh603259': '药明康德',
    'sh600309': '万华化学',
    'sz002475': '立讯精密',
    'sz300124': '汇川技术',
    'sh601899': '紫金矿业',
    'sh601688': '华泰证券',
    'sz002129': 'TCL中环',
    'sz002466': '天齐锂业',
    'sz002493': '荣盛石化',
    'sh600009': '上海机场',
    'sh600585': '海螺水泥',
    'sz000063': '中兴通讯',
    'sh601390': '中国中铁',
    'sh601668': '中国建筑',
    'sz000725': '京东方A',
    'sz002236': '大华股份',
    'sh600019': '宝钢股份',
    'sh601857': '中国石油',
    'sh601088': '中国神华',
    'sh601225': '陕西煤业',
    'sz002410': '广联达',
    'sz300014': '亿纬锂能',
    'sz300274': '阳光电源',
    'sz002129': '中环股份',
    'sh603501': '韦尔股份',
    'sz002415': '海康威视',
}

# 反向映射：名称到代码
NAME_TO_CODE_MAP = {v: k for k, v in STOCK_NAME_MAP.items()}


class SinaNewsCrawler:
    """新浪财经新闻爬虫类"""
    
    def __init__(self, cache_enabled: bool = True, cache_expire: int = CACHE_EXPIRE_SECONDS):
        """
        初始化爬虫
        
        Args:
            cache_enabled: 是否启用缓存
            cache_expire: 缓存过期时间（秒）
        """
        self.cache_enabled = cache_enabled
        self.cache_expire = cache_expire
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 最小请求间隔（秒）
    
    def _get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.cache_enabled:
            return None
        
        cache_item = self._cache.get(key)
        if cache_item is None:
            return None
        
        # 检查是否过期
        if time.time() - cache_item['timestamp'] > self.cache_expire:
            del self._cache[key]
            return None
        
        return cache_item['data']
    
    def _save_to_cache(self, key: str, data: Any) -> None:
        """保存数据到缓存"""
        if not self.cache_enabled:
            return
        
        self._cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def _rate_limit(self) -> None:
        """请求频率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _make_request(self, url: str, params: Dict = None, headers: Dict = None) -> Optional[Dict]:
        """
        发送HTTP请求
        
        Args:
            url: 请求URL
            params: 请求参数
            headers: 请求头
        
        Returns:
            JSON响应数据或None
        """
        self._rate_limit()
        
        req_headers = {**DEFAULT_HEADERS, **(headers or {})}
        
        try:
            response = requests.get(
                url,
                params=params,
                headers=req_headers,
                timeout=15
            )
            response.raise_for_status()
            
            # 尝试解析JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[SinaNews] 请求错误: {e}")
            return None
    
    def _parse_news_item(self, item: Dict) -> Dict:
        """
        解析新闻条目
        
        Args:
            item: 原始新闻数据
        
        Returns:
            标准化的新闻字典
        """
        # 解析时间戳
        timestamp = int(item.get('ctime', 0))
        pub_time = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
        
        # 获取图片
        img_url = ''
        if isinstance(item.get('img'), dict):
            img_url = item['img'].get('u', '')
        elif isinstance(item.get('images'), list) and item['images']:
            img_url = item['images'][0].get('u', '')
        
        return {
            'docid': item.get('docid', ''),
            'title': item.get('title', ''),
            'summary': item.get('intro', '') or item.get('summary', ''),
            'url': item.get('url', ''),
            'wap_url': item.get('wapurl', ''),
            'source': item.get('media_name', '新浪财经'),
            'author': item.get('author', ''),
            'published_at': pub_time.strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': timestamp,
            'image': img_url,
            'keywords': item.get('keywords', ''),
        }
    
    def get_hot_news(self, limit: int = 20, category: str = 'hot') -> List[Dict]:
        """
        获取热点财经新闻
        
        Args:
            limit: 返回数量（默认20，最大50）
            category: 新闻分类 ('hot', 'stock', 'fund', 'forex', 'futures', 'bond', 'usstock', 'hkstock')
        
        Returns:
            新闻列表
        """
        cache_key = self._get_cache_key('get_hot_news', limit, category=category)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        lid = NEWS_CATEGORIES.get(category, NEWS_CATEGORIES['hot'])
        
        params = {
            'pageid': 153,
            'lid': lid,
            'num': min(limit, 50),
            'page': 1,
        }
        
        data = self._make_request(SINA_FEED_BASE, params)
        
        if not data:
            return []
        
        result = data.get('result', {})
        if result.get('status', {}).get('code', -1) != 0:
            print(f"[SinaNews] API错误: {result.get('status', {}).get('msg', 'Unknown error')}")
            return []
        
        news_list = []
        for item in result.get('data', [])[:limit]:
            try:
                news_list.append(self._parse_news_item(item))
            except Exception as e:
                print(f"[SinaNews] 解析新闻错误: {e}")
                continue
        
        self._save_to_cache(cache_key, news_list)
        return news_list
    
    def get_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
        """
        获取股票相关新闻
        
        Args:
            symbol: 股票代码 (如 'sh600519', 'sz000858' 或 '贵州茅台')
            limit: 返回数量（默认10）
        
        Returns:
            新闻列表
        """
        cache_key = self._get_cache_key('get_stock_news', symbol, limit=limit)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)
        
        # 获取股票名称
        stock_name = STOCK_NAME_MAP.get(symbol, '')
        
        # 策略1: 从热点新闻中筛选相关新闻
        all_news = self.get_hot_news(limit=50, category='stock')
        
        # 筛选与该股票相关的新闻
        related_news = []
        for news in all_news:
            title = news.get('title', '')
            summary = news.get('summary', '')
            keywords = news.get('keywords', '')
            
            # 检查是否包含股票名称或代码
            content = f"{title} {summary} {keywords}"
            
            if stock_name and stock_name in content:
                related_news.append(news)
            elif symbol in content:
                related_news.append(news)
            # 也检查股票代码后4位
            elif symbol[-6:] in content:
                related_news.append(news)
        
        # 如果找到足够的相关新闻，返回
        if len(related_news) >= limit:
            result = related_news[:limit]
            self._save_to_cache(cache_key, result)
            return result
        
        # 策略2: 如果筛选结果不足，尝试从股票页面获取新闻
        page_news = self._get_stock_page_news(symbol)
        if page_news:
            # 合并结果，去重
            seen_docids = {n['docid'] for n in related_news}
            for news in page_news:
                if news['docid'] not in seen_docids:
                    related_news.append(news)
                    seen_docids.add(news['docid'])
        
        # 策略3: 如果仍然不足，尝试从HTML页面解析
        if len(related_news) < limit and HAS_BS4:
            html_news = self._parse_stock_html_news(symbol)
            if html_news:
                seen_docids = {n['docid'] for n in related_news}
                for news in html_news:
                    if news['docid'] not in seen_docids:
                        related_news.append(news)
                        seen_docids.add(news['docid'])
        
        result = related_news[:limit]
        self._save_to_cache(cache_key, result)
        return result
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码
        
        Args:
            symbol: 原始股票代码或名称
        
        Returns:
            标准化的股票代码 (如 'sh600519')
        """
        if not symbol:
            return symbol
            
        symbol = symbol.lower().strip()
        
        # 如果已经是标准格式
        if symbol.startswith(('sh', 'sz')):
            return symbol
        
        # 如果是纯数字
        if symbol.isdigit():
            if len(symbol) == 6:
                # 判断交易所
                if symbol.startswith(('6', '9', '5')):
                    return f'sh{symbol}'
                else:
                    return f'sz{symbol}'
            elif len(symbol) == 4:
                # 可能是简写代码
                for code in STOCK_NAME_MAP.keys():
                    if code.endswith(symbol):
                        return code
        
        # 尝试从名称查找（完整匹配）
        if symbol in NAME_TO_CODE_MAP:
            return NAME_TO_CODE_MAP[symbol]
        
        # 尝试部分匹配
        for name, code in NAME_TO_CODE_MAP.items():
            if symbol in name or name in symbol:
                return code
        
        # 尝试股票代码后6位匹配
        for code in STOCK_NAME_MAP.keys():
            if symbol in code:
                return code
        
        return symbol
    
    def _get_stock_page_news(self, symbol: str) -> List[Dict]:
        """
        从股票详情页获取相关新闻
        
        Args:
            symbol: 股票代码
        
        Returns:
            新闻列表
        """
        # 新浪财经有一个专门的股票新闻API
        # URL格式: https://news.sina.com.cn/stock/relnews/股票代码/
        # 但这个API需要解析HTML，比较复杂
        
        # 尝试使用另一个API端点
        # 该端点返回特定股票的相关新闻
        try:
            # 构建股票代码（去掉前缀）
            code = symbol.replace('sh', '').replace('sz', '')
            market = 'sh' if symbol.startswith('sh') else 'sz'
            
            # 使用新浪财经的股票新闻接口
            # 这个接口在股票详情页的新闻列表中使用
            url = f"https://feed.mix.sina.com.cn/api/roll/get"
            params = {
                'pageid': 153,
                'lid': 2517,  # 股票新闻分类
                'num': 20,
                'page': 1,
            }
            
            data = self._make_request(url, params)
            
            if not data:
                return []
            
            result = data.get('result', {})
            if result.get('status', {}).get('code', -1) != 0:
                return []
            
            news_list = []
            stock_name = STOCK_NAME_MAP.get(symbol, '')
            stock_code_simple = symbol[-6:] if len(symbol) >= 6 else symbol
            
            for item in result.get('data', []):
                title = item.get('title', '')
                intro = item.get('intro', '')
                keywords = item.get('keywords', '')
                content = f"{title} {intro} {keywords}"
                
                # 检查是否包含股票相关信息
                if stock_name and stock_name in content:
                    news_list.append(self._parse_news_item(item))
                elif stock_code_simple in content:
                    news_list.append(self._parse_news_item(item))
                elif code in content:
                    news_list.append(self._parse_news_item(item))
            
            return news_list
            
        except Exception as e:
            print(f"[SinaNews] 获取股票页面新闻错误: {e}")
            return []
    
    def get_market_news(self, market: str = 'cn', limit: int = 20) -> List[Dict]:
        """
        获取市场新闻
        
        Args:
            market: 市场类型 ('cn'=A股, 'us'=美股, 'hk'=港股)
            limit: 返回数量
        
        Returns:
            新闻列表
        """
        category_map = {
            'cn': 'stock',
            'us': 'usstock',
            'hk': 'hkstock',
        }
        
        category = category_map.get(market, 'stock')
        return self.get_hot_news(limit=limit, category=category)
    
    def search_news(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        搜索新闻（通过关键词筛选）
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量
        
        Returns:
            新闻列表
        """
        cache_key = self._get_cache_key('search_news', keyword, limit=limit)
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # 获取全部热点新闻
        all_news = self.get_hot_news(limit=50, category='hot')
        
        # 筛选包含关键词的新闻
        results = []
        for news in all_news:
            title = news.get('title', '')
            summary = news.get('summary', '')
            content = f"{title} {summary}".lower()
            
            if keyword.lower() in content:
                results.append(news)
        
        result = results[:limit]
        self._save_to_cache(cache_key, result)
        return result
    
    def get_news_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime = None,
        category: str = 'hot',
        limit: int = 50
    ) -> List[Dict]:
        """
        获取指定时间范围的新闻
        
        Args:
            start_time: 开始时间
            end_time: 结束时间（默认为当前时间）
            category: 新闻分类
            limit: 返回数量
        
        Returns:
            新闻列表
        """
        if end_time is None:
            end_time = datetime.now()
        
        # 获取新闻
        all_news = self.get_hot_news(limit=100, category=category)
        
        # 筛选时间范围
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        results = []
        for news in all_news:
            news_ts = news.get('timestamp', 0)
            if start_ts <= news_ts <= end_ts:
                results.append(news)
        
        return results[:limit]
    
    def _parse_stock_html_news(self, symbol: str) -> List[Dict]:
        """
        从股票页面HTML解析新闻（备用方法）
        
        Args:
            symbol: 股票代码
        
        Returns:
            新闻列表
        """
        if not HAS_BS4:
            return []
        
        try:
            # 构建股票页面URL
            code = symbol.replace('sh', '').replace('sz', '')
            market = 'sh' if symbol.startswith('sh') else 'sz'
            
            # 新浪财经股票页面
            url = f"{SINA_STOCK_NEWS_BASE}/{market}{code}/nc.shtml"
            
            headers = {
                **DEFAULT_HEADERS,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            self._rate_limit()
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'gbk'  # 新浪财经使用GBK编码
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_list = []
            
            # 查找新闻列表（新浪财经页面结构）
            # 新闻通常在 class="newslist" 或类似的容器中
            news_items = soup.find_all('li', class_=lambda x: x and 'news' in str(x).lower())
            
            for item in news_items[:15]:
                try:
                    link = item.find('a')
                    if link:
                        title = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        if title and href:
                            news_list.append({
                                'docid': hashlib.md5(href.encode()).hexdigest()[:16],
                                'title': title,
                                'summary': '',
                                'url': href if href.startswith('http') else f"https://finance.sina.com.cn{href}",
                                'wap_url': '',
                                'source': '新浪财经',
                                'author': '',
                                'published_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'timestamp': int(time.time()),
                                'image': '',
                                'keywords': '',
                            })
                except Exception:
                    continue
            
            return news_list
            
        except Exception as e:
            print(f"[SinaNews] HTML解析错误: {e}")
            return []
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()


# 创建默认实例
_default_crawler = SinaNewsCrawler()


def get_hot_news(limit: int = 20) -> List[Dict]:
    """
    获取热点财经新闻（便捷函数）
    
    Args:
        limit: 返回数量
    
    Returns:
        新闻列表
    """
    return _default_crawler.get_hot_news(limit=limit, category='hot')


def get_stock_news(symbol: str, limit: int = 10) -> List[Dict]:
    """
    获取股票相关新闻（便捷函数）
    
    Args:
        symbol: 股票代码或名称 (如 'sh600519', '贵州茅台', '茅台')
        limit: 返回数量
    
    Returns:
        新闻列表
    """
    return _default_crawler.get_stock_news(symbol, limit=limit)


def get_us_stock_news(limit: int = 20) -> List[Dict]:
    """获取美股新闻"""
    return _default_crawler.get_hot_news(limit=limit, category='usstock')


def get_hk_stock_news(limit: int = 20) -> List[Dict]:
    """获取港股新闻"""
    return _default_crawler.get_hot_news(limit=limit, category='hkstock')


def search_news(keyword: str, limit: int = 20) -> List[Dict]:
    """
    搜索新闻
    
    Args:
        keyword: 搜索关键词
        limit: 返回数量
    
    Returns:
        新闻列表
    """
    return _default_crawler.search_news(keyword, limit=limit)


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("新浪财经新闻爬虫测试")
    print("=" * 60)
    
    # 测试热点新闻
    print("\n📰 热点财经新闻:")
    hot_news = get_hot_news(limit=5)
    for i, news in enumerate(hot_news, 1):
        print(f"\n{i}. {news['title']}")
        print(f"   来源: {news['source']}")
        print(f"   时间: {news['published_at']}")
        if news['summary']:
            print(f"   摘要: {news['summary'][:80]}...")
    
    # 测试股票新闻
    print("\n\n📈 测试股票新闻（比亚迪）:")
    stock_news = get_stock_news('比亚迪', limit=5)
    if stock_news:
        for i, news in enumerate(stock_news, 1):
            print(f"\n{i}. {news['title']}")
            print(f"   来源: {news['source']}")
            print(f"   时间: {news['published_at']}")
    else:
        print("   未找到相关新闻（当前热点新闻中没有该股票相关内容）")
    
    # 测试美股新闻
    print("\n\n🇺🇸 美股新闻:")
    us_news = get_us_stock_news(limit=3)
    for i, news in enumerate(us_news, 1):
        print(f"\n{i}. {news['title']}")
        print(f"   时间: {news['published_at']}")
    
    # 测试港股新闻
    print("\n\n🇭🇰 港股新闻:")
    hk_news = get_hk_stock_news(limit=3)
    for i, news in enumerate(hk_news, 1):
        print(f"\n{i}. {news['title']}")
        print(f"   时间: {news['published_at']}")
    
    # 测试搜索 - 使用更常见的关键词
    print("\n\n🔍 搜索'油价'相关新闻:")
    search_results = search_news('油价', limit=3)
    for i, news in enumerate(search_results, 1):
        print(f"\n{i}. {news['title']}")
        print(f"   时间: {news['published_at']}")
    
    # 测试基金新闻
    print("\n\n💰 基金新闻:")
    crawler = SinaNewsCrawler()
    fund_news = crawler.get_hot_news(limit=3, category='fund')
    for i, news in enumerate(fund_news, 1):
        print(f"\n{i}. {news['title']}")
        print(f"   时间: {news['published_at']}")
    
    # 测试股票代码标准化
    print("\n\n🔧 股票代码标准化测试:")
    test_codes = ['600519', 'sh600519', '茅台', '贵州茅台', '000001', '平安银行']
    for code in test_codes:
        normalized = crawler._normalize_symbol(code)
        name = STOCK_NAME_MAP.get(normalized, '未知')
        print(f"   {code} -> {normalized} ({name})")
    
    print("\n" + "=" * 60)
    print("测试完成！")