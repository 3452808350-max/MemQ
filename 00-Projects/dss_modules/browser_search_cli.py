#!/usr/bin/env python3
"""
Browser Search CLI - DSS浏览器自动化搜索工具 (优化版 v2.0)

功能：
1. search-seeking-alpha <symbol> - 搜索Seeking Alpha分析文章
2. search-yahoo-finance <symbol> - 搜索Yahoo Finance数据
3. search-google-finance <symbol> - 搜索Google Finance数据
4. search-news <keyword> - 搜索财经新闻

优化特性：
- 并行搜索多个来源
- 浏览器实例复用
- 智能缓存（TTL 5分钟）
- 精简等待策略

使用Playwright进行浏览器自动化，具有反爬措施：
- 真实浏览器行为模拟
- 用户代理轮换
- 请求头伪装

安装：
    pip install playwright click
    playwright install chromium

使用方法：
    # 命令行
    python browser_search_cli.py seeking-alpha BABA
    python browser_search_cli.py yahoo-finance AAPL --json
    python browser_search_cli.py news "中概股" --limit 10
    python browser_search_cli.py all AAPL --parallel  # 并行搜索所有来源

    # 作为模块
    from browser_search_cli import BrowserSearchCLI
    cli = BrowserSearchCLI()
    result = await cli.search_seeking_alpha("BABA")
"""

import asyncio
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from functools import wraps
import logging

import click
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 检查Playwright是否可用
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")

# 随机User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# 常见浏览器语言和时区
BROWSER_LOCALES = ["en-US", "en-GB", "zh-CN", "zh-TW"]
BROWSER_TIMEZONES = ["America/New_York", "America/Los_Angeles", "Asia/Shanghai", "Europe/London"]

# 默认缓存TTL（秒）
DEFAULT_CACHE_TTL = 300  # 5分钟


class SearchCache:
    """简单的内存缓存，带TTL"""

    def __init__(self, ttl: int = DEFAULT_CACHE_TTL):
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}  # key -> (value, timestamp)

    def _make_key(self, source: str, query: str) -> str:
        return f"{source}:{query}"

    def get(self, source: str, query: str):  # -> Optional[SearchResponse]
        key = self._make_key(source, query)
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"Cache hit: {key}")
                return value
            else:
                del self._cache[key]
        return None

    def set(self, source: str, query: str, value):  # value: SearchResponse
        key = self._make_key(source, query)
        self._cache[key] = (value, time.time())

    def clear(self):
        self._cache.clear()


@dataclass
class SearchResult:
    """搜索结果数据结构"""
    title: str
    url: str
    source: str
    snippet: Optional[str] = None
    date: Optional[str] = None
    author: Optional[str] = None
    rating: Optional[str] = None  # 用于分析师评级
    price: Optional[float] = None  # 用于股价
    change: Optional[float] = None  # 用于涨跌幅
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResponse:
    """搜索响应数据结构"""
    query: str
    source: str
    timestamp: str
    results: List[SearchResult]
    total: int
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "source": self.source,
            "timestamp": self.timestamp,
            "results": [r.to_dict() for r in self.results],
            "total": self.total,
            "success": self.success,
            "error": self.error
        }


class BrowserSearchCLI:
    """浏览器搜索CLI类"""

    # 目标网站配置
    SITES = {
        "seeking_alpha": {
            "base_url": "https://seekingalpha.com",
            "search_url": "https://seekingalpha.com/symbol/{symbol}",
            "article_url": "https://seekingalpha.com/article/{id}",
            "type": "analysis"
        },
        "yahoo_finance": {
            "base_url": "https://finance.yahoo.com",
            "quote_url": "https://finance.yahoo.com/quote/{symbol}",
            "news_url": "https://finance.yahoo.com/quote/{symbol}/news",
            "type": "quote"
        },
        "google_finance": {
            "base_url": "https://www.google.com/finance",
            "quote_url": "https://www.google.com/finance/quote/{symbol}:NASDAQ",
            "type": "quote"
        },
        "news": {
            "google_news": "https://news.google.com/search?q={keyword}&hl=en-US&gl=US&ceid=US:en",
            "bing_news": "https://www.bing.com/news/search?q={keyword}",
            "type": "news"
        }
    }

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        delay_range: tuple = (0.5, 1.5),  # 优化：减少延迟范围
        max_results: int = 10,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        fast_mode: bool = True  # 快速模式：跳过人类模拟
    ):
        """
        初始化浏览器搜索CLI

        Args:
            headless: 是否无头模式运行
            timeout: 页面加载超时时间（毫秒）
            delay_range: 请求间隔时间范围（秒）
            max_results: 最大返回结果数
            cache_ttl: 缓存有效期（秒）
            fast_mode: 快速模式，跳过人类行为模拟
        """
        if not HAS_PLAYWRIGHT:
            raise ImportError("Playwright not installed. Run: pip install playwright && playwright install chromium")

        self.headless = headless
        self.timeout = timeout
        self.delay_range = delay_range
        self.max_results = max_results
        self.fast_mode = fast_mode
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._playwright = None
        self._cache = SearchCache(cache_ttl) if cache_ttl > 0 else None

    async def _init_browser(self) -> Browser:
        """初始化浏览器"""
        if self._browser and self._context:
            return self._browser

        self._playwright = await async_playwright().start()

        # 随机选择用户代理和语言设置
        user_agent = random.choice(USER_AGENTS)
        locale = random.choice(BROWSER_LOCALES)
        timezone = random.choice(BROWSER_TIMEZONES)

        browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                f'--lang={locale}',
            ]
        )

        # 创建上下文时设置反检测参数
        self._context = await browser.new_context(
            user_agent=user_agent,
            locale=locale,
            timezone_id=timezone,
            viewport={'width': 1920, 'height': 1080},
            screen={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            has_touch=False,
            java_script_enabled=True,
            ignore_https_errors=True,
        )

        # 添加反检测脚本
        await self._context.add_init_script("""
            // 隐藏webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 模拟真实的plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // 模拟真实的languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'zh-CN']
            });

            // 模拟Chrome属性
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // 覆盖权限查询
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        self._browser = browser
        return browser

    async def _get_page(self) -> Page:
        """获取新页面"""
        if not self._context:
            await self._init_browser()
        page = await self._context.new_page()

        # 设置额外的请求头
        await page.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })

        return page

    async def _random_delay(self):
        """随机延迟"""
        if self.fast_mode:
            return
        delay = random.uniform(*self.delay_range)
        await asyncio.sleep(delay)

    async def _human_like_wait(self, page: Page):
        """模拟人类等待行为（快速模式下跳过）"""
        if self.fast_mode:
            # 快速模式：只等待关键元素
            await asyncio.sleep(0.2)
            return

        # 随机滚动
        for _ in range(random.randint(1, 3)):
            scroll_amount = random.randint(100, 500)
            await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            await asyncio.sleep(random.uniform(0.3, 0.8))

        # 随机鼠标移动
        try:
            x = random.randint(100, 1800)
            y = random.randint(100, 900)
            await page.mouse.move(x, y)
        except Exception:
            pass

        await asyncio.sleep(random.uniform(0.5, 1.5))

    async def search_seeking_alpha(self, symbol: str) -> SearchResponse:
        """
        搜索Seeking Alpha分析文章

        Args:
            symbol: 股票代码（如 BABA, AAPL）

        Returns:
            SearchResponse对象包含搜索结果
        """
        symbol = symbol.upper()

        # 检查缓存
        if self._cache:
            cached = self._cache.get("seeking_alpha", symbol)
            if cached:
                return cached

        results = []
        timestamp = datetime.now().isoformat()

        try:
            page = await self._get_page()
            url = self.SITES["seeking_alpha"]["search_url"].format(symbol=symbol)

            logger.info(f"Searching Seeking Alpha for: {symbol}")
            await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)

            # 优化：使用更快的等待策略
            try:
                await page.wait_for_selector('article, [data-test-id], a[href*="/article/"]', timeout=5000)
            except Exception:
                pass

            # 模拟人类行为
            await self._human_like_wait(page)

            # 检查是否有验证码或登录要求
            if await page.locator('text=verify you are human').count() > 0:
                logger.warning("Seeking Alpha requires verification. Waiting...")
                await asyncio.sleep(5)

            # 解析文章列表
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # 尝试多种选择器
            article_selectors = [
                'article[data-test-id="article-card"]',
                'div[data-test-id="article-list-item"]',
                'a[href*="/article/"]',
                '.article-card',
                '[data-item-id]'
            ]

            articles = []
            for selector in article_selectors:
                found = soup.select(selector)
                if found:
                    articles = found[:self.max_results]
                    break

            for article in articles:
                try:
                    # 提取标题
                    title_elem = article.select_one('h3, h4, [data-test-id="article-title"], a[href*="/article/"]')
                    title = title_elem.get_text(strip=True) if title_elem else None

                    # 提取链接
                    link_elem = article.select_one('a[href*="/article/"]') or article.get('href')
                    if link_elem:
                        href = link_elem.get('href', '') if hasattr(link_elem, 'get') else link_elem
                        if href and not href.startswith('http'):
                            href = f"https://seekingalpha.com{href}"
                    else:
                        href = None

                    # 提取摘要
                    snippet_elem = article.select_one('p, [data-test-id="article-snippet"]')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else None

                    # 提取日期
                    date_elem = article.select_one('time, [data-test-id="article-date"], .article-date')
                    date = date_elem.get_text(strip=True) if date_elem else None
                    if date_elem and date_elem.get('datetime'):
                        date = date_elem.get('datetime')

                    # 提取作者
                    author_elem = article.select_one('[data-test-id="article-author"], .author-name')
                    author = author_elem.get_text(strip=True) if author_elem else None

                    # 提取评级（如果有）
                    rating_elem = article.select_one('[data-test-id="rating"], .rating')
                    rating = rating_elem.get_text(strip=True) if rating_elem else None

                    if title and href:
                        results.append(SearchResult(
                            title=title,
                            url=href,
                            source="Seeking Alpha",
                            snippet=snippet,
                            date=date,
                            author=author,
                            rating=rating
                        ))
                except Exception as e:
                    logger.debug(f"Error parsing article: {e}")
                    continue

            await page.close()

        except Exception as e:
            logger.error(f"Seeking Alpha search error: {e}")
            return SearchResponse(
                query=symbol,
                source="Seeking Alpha",
                timestamp=timestamp,
                results=[],
                total=0,
                success=False,
                error=str(e)
            )

        await self._random_delay()

        response = SearchResponse(
            query=symbol,
            source="Seeking Alpha",
            timestamp=timestamp,
            results=results,
            total=len(results),
            success=True
        )

        # 存入缓存
        if self._cache:
            self._cache.set("seeking_alpha", symbol, response)

        return response

    async def search_yahoo_finance(self, symbol: str) -> SearchResponse:
        """
        搜索Yahoo Finance股票数据

        Args:
            symbol: 股票代码（如 AAPL, TSLA）

        Returns:
            SearchResponse对象包含股票数据和新闻
        """
        symbol = symbol.upper()

        # 检查缓存
        if self._cache:
            cached = self._cache.get("yahoo_finance", symbol)
            if cached:
                return cached

        results = []
        timestamp = datetime.now().isoformat()

        try:
            page = await self._get_page()
            url = self.SITES["yahoo_finance"]["quote_url"].format(symbol=symbol)

            logger.info(f"Searching Yahoo Finance for: {symbol}")
            await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)

            # 优化：使用更快的等待策略
            try:
                await page.wait_for_selector('[data-symbol], h1, [data-field]', timeout=5000)
            except Exception:
                pass
            await self._human_like_wait(page)

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # 提取股票基本信息
            quote_data = {}

            # 股票名称
            name_elem = soup.select_one('h1')
            quote_data['name'] = name_elem.get_text(strip=True) if name_elem else symbol

            # 当前价格
            price_elem = soup.select_one('[data-field="regularMarketPrice"], .Fw\\(b\\).Fz\\(36px\\)')
            if price_elem:
                try:
                    quote_data['price'] = float(price_elem.get_text(strip=True).replace(',', ''))
                except ValueError:
                    pass

            # 涨跌幅
            change_elem = soup.select_one('[data-field="regularMarketChangePercent"], .C\\(\\$c\\-txt\\-percent\\)')
            if change_elem:
                change_text = change_elem.get_text(strip=True)
                try:
                    # 解析类似 "+1.23%" 的格式
                    match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                    if match:
                        quote_data['change_percent'] = float(match.group(1))
                except ValueError:
                    pass

            # 其他数据点
            data_fields = {
                'regularMarketOpen': 'open',
                'regularMarketDayHigh': 'day_high',
                'regularMarketDayLow': 'day_low',
                'fiftyTwoWeekHigh': '52week_high',
                'fiftyTwoWeekLow': '52week_low',
                'regularMarketVolume': 'volume',
                'marketCap': 'market_cap',
                'trailingPE': 'pe_ratio',
                'dividendYield': 'dividend_yield',
            }

            for field, label in data_fields.items():
                elem = soup.select_one(f'[data-field="{field}"]')
                if elem:
                    text = elem.get_text(strip=True).replace(',', '')
                    try:
                        quote_data[label] = float(text) if '.' in text else int(text)
                    except ValueError:
                        quote_data[label] = text

            # 添加主结果
            if quote_data.get('price'):
                results.append(SearchResult(
                    title=f"{symbol} - {quote_data.get('name', symbol)}",
                    url=url,
                    source="Yahoo Finance",
                    price=quote_data.get('price'),
                    change=quote_data.get('change_percent'),
                    extra=quote_data
                ))

            # 提取新闻
            news_url = self.SITES["yahoo_finance"]["news_url"].format(symbol=symbol)
            await page.goto(news_url, wait_until='domcontentloaded', timeout=self.timeout)
            await page.wait_for_load_state('networkidle', timeout=self.timeout)
            await asyncio.sleep(1)

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # 解析新闻列表
            news_selectors = [
                'li.js-stream-content',
                'div[data-testid="news-item"]',
                'a[href*="/news/"]'
            ]

            news_items = []
            for selector in news_selectors:
                found = soup.select(selector)
                if found:
                    news_items = found[:min(self.max_results - 1, 5)]
                    break

            for item in news_items:
                try:
                    title_elem = item.select_one('h3, h4, a')
                    title = title_elem.get_text(strip=True) if title_elem else None

                    link_elem = item.select_one('a') or item
                    href = link_elem.get('href', '') if hasattr(link_elem, 'get') else None
                    if href and not href.startswith('http'):
                        href = f"https://finance.yahoo.com{href}"

                    date_elem = item.select_one('time, .C\\(\\$c\\-date\\)')
                    date = date_elem.get_text(strip=True) if date_elem else None

                    source_elem = item.select_one('.C\\(\\$c\\-source\\), .publisher')
                    news_source = source_elem.get_text(strip=True) if source_elem else "Yahoo Finance"

                    if title and href:
                        results.append(SearchResult(
                            title=title,
                            url=href,
                            source=news_source,
                            date=date
                        ))
                except Exception as e:
                    logger.debug(f"Error parsing news item: {e}")
                    continue

            await page.close()

        except Exception as e:
            logger.error(f"Yahoo Finance search error: {e}")
            return SearchResponse(
                query=symbol,
                source="Yahoo Finance",
                timestamp=timestamp,
                results=results,
                total=len(results),
                success=False,
                error=str(e)
            )

        await self._random_delay()

        response = SearchResponse(
            query=symbol,
            source="Yahoo Finance",
            timestamp=timestamp,
            results=results,
            total=len(results),
            success=True
        )

        # 存入缓存
        if self._cache:
            self._cache.set("yahoo_finance", symbol, response)

        return response

    async def search_google_finance(self, symbol: str) -> SearchResponse:
        """
        搜索Google Finance股票数据

        Args:
            symbol: 股票代码

        Returns:
            SearchResponse对象包含股票数据
        """
        symbol = symbol.upper()

        # 检查缓存
        if self._cache:
            cached = self._cache.get("google_finance", symbol)
            if cached:
                return cached

        results = []
        timestamp = datetime.now().isoformat()

        try:
            page = await self._get_page()

            # 尝试NASDAQ交易所
            url = self.SITES["google_finance"]["quote_url"].format(symbol=symbol)

            logger.info(f"Searching Google Finance for: {symbol}")
            await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)

            try:
                await page.wait_for_selector('[data-last-price], .kf1nC', timeout=self.timeout)
            except Exception:
                pass

            await page.wait_for_load_state('networkidle', timeout=self.timeout)
            await self._human_like_wait(page)

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            quote_data = {}

            # 提取股票名称
            name_elem = soup.select_one('h1, .zzDege')
            quote_data['name'] = name_elem.get_text(strip=True) if name_elem else symbol

            # 提取价格 - Google Finance使用data-last-price属性
            price_elem = soup.select_one('[data-last-price]')
            if price_elem:
                try:
                    price_str = price_elem.get('data-last-price', '0')
                    # Google存储的可能是美元或分，取决于数据源
                    price_val = float(price_str)
                    # 如果价格看起来太小（如<100的股票显示为小数），可能是分
                    if price_val < 100 and price_val > 0:
                        # 检查是否已经是正确价格
                        text_price = price_elem.get_text(strip=True)
                        if text_price and '$' in text_price:
                            match = re.search(r'\$?([\d,]+\.?\d*)', text_price)
                            if match:
                                quote_data['price'] = float(match.group(1).replace(',', ''))
                            else:
                                quote_data['price'] = price_val
                        else:
                            quote_data['price'] = price_val
                    else:
                        quote_data['price'] = price_val
                except ValueError:
                    pass

            # 如果上面没找到，尝试其他选择器
            if not quote_data.get('price'):
                price_elem = soup.select_one('.kf1nC, .YMlKec')
                if price_elem:
                    try:
                        quote_data['price'] = float(price_elem.get_text(strip=True).replace(',', '').replace('$', ''))
                    except ValueError:
                        pass

            # 涨跌幅
            change_elem = soup.select_one('.BAftt, [data-last-percent-change]')
            if change_elem:
                change_text = change_elem.get_text(strip=True)
                try:
                    match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                    if match:
                        quote_data['change_percent'] = float(match.group(1))
                except ValueError:
                    pass

            # 如果上面没找到
            if not quote_data.get('change_percent'):
                change_elem = soup.select_one('.JwB6zf, .P2Luy.Ez2Ioe')
                if change_elem:
                    change_text = change_elem.get_text(strip=True)
                    try:
                        match = re.search(r'([+-]?\d+\.?\d*)%', change_text)
                        if match:
                            quote_data['change_percent'] = float(match.group(1))
                    except ValueError:
                        pass

            # 提取其他数据点
            for row in soup.select('div.gyFHrc, tr'):
                label_elem = row.select_one('div.nvmPse, td:first-child')
                value_elem = row.select_one('div.P6K39c, td:last-child')
                if label_elem and value_elem:
                    label = label_elem.get_text(strip=True).lower()
                    value = value_elem.get_text(strip=True)
                    if 'market cap' in label:
                        quote_data['market_cap'] = value
                    elif 'p/e ratio' in label:
                        quote_data['pe_ratio'] = value
                    elif 'dividend yield' in label:
                        quote_data['dividend_yield'] = value
                    elif '52 week' in label:
                        quote_data['52week_range'] = value
                    elif 'volume' in label:
                        quote_data['volume'] = value

            if quote_data.get('price'):
                results.append(SearchResult(
                    title=f"{symbol} - {quote_data.get('name', symbol)}",
                    url=url,
                    source="Google Finance",
                    price=quote_data.get('price'),
                    change=quote_data.get('change_percent'),
                    extra=quote_data
                ))

            # 提取相关新闻
            news_items = soup.select('div.z4rs2b, article')
            for item in news_items[:5]:
                try:
                    title_elem = item.select_one('a, .z4rs2b')
                    title = title_elem.get_text(strip=True) if title_elem else None

                    link_elem = item.select_one('a')
                    href = link_elem.get('href', '') if link_elem else None
                    if href and not href.startswith('http'):
                        href = f"https://www.google.com{href}"

                    date_elem = item.select_one('div.Adend, time')
                    date = date_elem.get_text(strip=True) if date_elem else None

                    source_elem = item.select_one('.sfyWed, .lBwEkb')
                    news_source = source_elem.get_text(strip=True) if source_elem else "Google Finance"

                    if title:
                        results.append(SearchResult(
                            title=title,
                            url=href or "",
                            source=news_source,
                            date=date
                        ))
                except Exception as e:
                    logger.debug(f"Error parsing news item: {e}")
                    continue

            await page.close()

        except Exception as e:
            logger.error(f"Google Finance search error: {e}")
            return SearchResponse(
                query=symbol,
                source="Google Finance",
                timestamp=timestamp,
                results=results,
                total=len(results),
                success=False,
                error=str(e)
            )

        await self._random_delay()

        response = SearchResponse(
            query=symbol,
            source="Google Finance",
            timestamp=timestamp,
            results=results,
            total=len(results),
            success=True
        )

        # 存入缓存
        if self._cache:
            self._cache.set("google_finance", symbol, response)

        return response

    async def search_news(self, keyword: str, source: str = "google") -> SearchResponse:
        """
        搜索财经新闻

        Args:
            keyword: 搜索关键词
            source: 新闻源（google 或 bing）

        Returns:
            SearchResponse对象包含新闻结果
        """
        # 检查缓存
        cache_key = f"{source}:{keyword}"
        if self._cache:
            cached = self._cache.get("news", cache_key)
            if cached:
                return cached

        results = []
        timestamp = datetime.now().isoformat()

        try:
            page = await self._get_page()

            if source == "google":
                url = self.SITES["news"]["google_news"].format(
                    keyword=keyword.replace(' ', '+')
                )
            else:
                url = self.SITES["news"]["bing_news"].format(
                    keyword=keyword.replace(' ', '+')
                )

            logger.info(f"Searching {source} news for: {keyword}")
            await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)

            try:
                await page.wait_for_selector('article, [data-n-q], .newsitem', timeout=self.timeout)
            except Exception:
                pass

            await page.wait_for_load_state('networkidle', timeout=self.timeout)
            await self._human_like_wait(page)

            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Google News 选择器
            if source == "google":
                # 多种新闻选择器
                news_items = soup.select('article, div[jsname="SC7lYd"], div.SOvZab, div.H0Wff, div.SbNwzf')
                if not news_items:
                    # 尝试更多选择器
                    news_items = soup.select('div[role="listitem"], a[href*="./article/"]')
                for item in news_items[:self.max_results]:
                    try:
                        # 标题 - 多种选择器
                        title_elem = (
                            item.select_one('h4, h3') or
                            item.select_one('a[href*="./article/"]') or
                            item.select_one('.n0jphosphorus, .JtKRv')
                        )
                        if not title_elem:
                            # 如果item本身是链接
                            if item.name == 'a' and item.get('href', '').startswith('./article'):
                                title_elem = item
                        title = title_elem.get_text(strip=True) if title_elem else None

                        # 链接
                        link_elem = item.select_one('a[href*="./article"]')
                        if link_elem:
                            href = link_elem.get('href', '')
                            if href.startswith('./article'):
                                href = f"https://news.google.com{href[1:]}"
                        else:
                            href = None

                        # 来源
                        source_elem = item.select_one('time[data-n-t], .vr1Oe, .wEwyrc')
                        news_source = source_elem.get_text(strip=True) if source_elem else "Google News"

                        # 日期
                        date_elem = item.select_one('time, .UOVFe')
                        date = date_elem.get('datetime') or date_elem.get_text(strip=True) if date_elem else None

                        # 摘要
                        snippet_elem = item.select_one('.xbPIIb, p')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else None

                        if title:
                            results.append(SearchResult(
                                title=title,
                                url=href or "",
                                source=news_source,
                                snippet=snippet,
                                date=date
                            ))
                    except Exception as e:
                        logger.debug(f"Error parsing news item: {e}")
                        continue
            else:
                # Bing News 选择器
                news_items = soup.select('.newsitem, .algoclickable')
                for item in news_items[:self.max_results]:
                    try:
                        title_elem = item.select_one('a.title, h2 a, .caption')
                        title = title_elem.get_text(strip=True) if title_elem else None

                        href = title_elem.get('href', '') if title_elem else None

                        source_elem = item.select_one('.source, .newsagency')
                        news_source = source_elem.get_text(strip=True) if source_elem else "Bing News"

                        date_elem = item.select_one('.date, .timeago')
                        date = date_elem.get_text(strip=True) if date_elem else None

                        snippet_elem = item.select_one('.snippet, .caption + p')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else None

                        if title and href:
                            results.append(SearchResult(
                                title=title,
                                url=href,
                                source=news_source,
                                snippet=snippet,
                                date=date
                            ))
                    except Exception as e:
                        logger.debug(f"Error parsing news item: {e}")
                        continue

            await page.close()

        except Exception as e:
            logger.error(f"News search error: {e}")
            return SearchResponse(
                query=keyword,
                source=f"{source.capitalize()} News",
                timestamp=timestamp,
                results=results,
                total=len(results),
                success=False,
                error=str(e)
            )

        await self._random_delay()

        response = SearchResponse(
            query=keyword,
            source=f"{source.capitalize()} News",
            timestamp=timestamp,
            results=results,
            total=len(results),
            success=True
        )

        # 存入缓存
        cache_key = f"{source}:{keyword}"
        if self._cache:
            self._cache.set("news", cache_key, response)

        return response

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.debug(f"Browser close error: {e}")
            finally:
                self._browser = None
                self._context = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            finally:
                self._playwright = None

    async def search_all_parallel(self, symbol: str) -> Dict[str, SearchResponse]:
        """
        并行搜索所有来源

        Args:
            symbol: 股票代码

        Returns:
            字典，包含所有来源的搜索结果
        """
        logger.info(f"并行搜索 {symbol}...")

        # 并行执行所有搜索
        results = await asyncio.gather(
            self.search_yahoo_finance(symbol),
            self.search_google_finance(symbol),
            self.search_seeking_alpha(symbol),
            return_exceptions=True
        )

        return {
            "yahoo_finance": results[0] if not isinstance(results[0], Exception) else SearchResponse(
                query=symbol, source="Yahoo Finance", timestamp=datetime.now().isoformat(),
                results=[], total=0, success=False, error=str(results[0])
            ),
            "google_finance": results[1] if not isinstance(results[1], Exception) else SearchResponse(
                query=symbol, source="Google Finance", timestamp=datetime.now().isoformat(),
                results=[], total=0, success=False, error=str(results[1])
            ),
            "seeking_alpha": results[2] if not isinstance(results[2], Exception) else SearchResponse(
                query=symbol, source="Seeking Alpha", timestamp=datetime.now().isoformat(),
                results=[], total=0, success=False, error=str(results[2])
            )
        }


# ── CLI 接口 ──────────────────────────────────────────────────────

def async_command(f):
    """装饰器：将异步命令转换为同步Click命令"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(f(*args, **kwargs))
            return result
        finally:
            # 清理pending tasks
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            finally:
                loop.close()
    return wrapper


@click.group(invoke_without_command=True)
@click.option('--json', 'output_json', is_flag=True, help='输出JSON格式')
@click.option('--limit', default=10, help='最大结果数')
@click.option('--headful', is_flag=True, help='显示浏览器窗口（调试用）')
@click.option('--timeout', default=30000, help='页面加载超时（毫秒）')
@click.option('--no-cache', is_flag=True, help='禁用缓存')
@click.pass_context
def cli(ctx, output_json, limit, headful, timeout, no_cache):
    """DSS浏览器搜索CLI (优化版 v2.0)

    使用Playwright进行浏览器自动化搜索，支持：
    - Seeking Alpha 分析文章
    - Yahoo Finance 股票数据
    - Google Finance 股票数据
    - 财经新闻搜索

    优化特性：
    - 并行搜索（all 命令）
    - 智能缓存（TTL 5分钟）
    - 快速模式（跳过人类行为模拟）

    示例：
        browser-search seeking-alpha BABA
        browser-search yahoo-finance AAPL --json
        browser-search news "中概股" --limit 5
        browser-search all AAPL  # 并行搜索所有来源
    """
    ctx.ensure_object(dict)
    ctx.obj['output_json'] = output_json
    ctx.obj['limit'] = limit
    ctx.obj['headless'] = not headful
    ctx.obj['timeout'] = timeout
    ctx.obj['no_cache'] = no_cache


@cli.command('seeking-alpha')
@click.argument('symbol')
@click.pass_context
@async_command
async def search_seeking_alpha_cmd(ctx, symbol):
    """搜索Seeking Alpha分析文章

    SYMBOL: 股票代码（如 BABA, AAPL）
    """
    cli_instance = BrowserSearchCLI(
        headless=ctx.obj['headless'],
        timeout=ctx.obj['timeout'],
        max_results=ctx.obj['limit'],
        cache_ttl=0 if ctx.obj['no_cache'] else DEFAULT_CACHE_TTL,
        fast_mode=True
    )

    try:
        result = await cli_instance.search_seeking_alpha(symbol)
        output_json = ctx.obj['output_json']

        if output_json:
            click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            click.echo(f"\n{'='*60}")
            click.echo(f"Seeking Alpha 分析文章: {symbol.upper()}")
            click.echo(f"{'='*60}\n")

            if not result.success:
                click.echo(f"❌ 错误: {result.error}")
                return

            if not result.results:
                click.echo("未找到相关文章")
                return

            for i, item in enumerate(result.results, 1):
                click.echo(f"【{i}】{item.title}")
                if item.author:
                    click.echo(f"    作者: {item.author}")
                if item.rating:
                    click.echo(f"    评级: {item.rating}")
                if item.date:
                    click.echo(f"    日期: {item.date}")
                if item.snippet:
                    click.echo(f"    摘要: {item.snippet[:100]}...")
                click.echo(f"    链接: {item.url}")
                click.echo()
    finally:
        await cli_instance.close()


@cli.command('yahoo-finance')
@click.argument('symbol')
@click.pass_context
@async_command
async def search_yahoo_finance_cmd(ctx, symbol):
    """搜索Yahoo Finance股票数据

    SYMBOL: 股票代码（如 AAPL, TSLA）
    """
    cli_instance = BrowserSearchCLI(
        headless=ctx.obj['headless'],
        timeout=ctx.obj['timeout'],
        max_results=ctx.obj['limit'],
        cache_ttl=0 if ctx.obj['no_cache'] else DEFAULT_CACHE_TTL,
        fast_mode=True
    )

    try:
        result = await cli_instance.search_yahoo_finance(symbol)
        output_json = ctx.obj['output_json']

        if output_json:
            click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            click.echo(f"\n{'='*60}")
            click.echo(f"Yahoo Finance: {symbol.upper()}")
            click.echo(f"{'='*60}\n")

            if not result.success:
                click.echo(f"❌ 错误: {result.error}")
                return

            if not result.results:
                click.echo("未找到股票数据")
                return

            # 第一个结果是股票报价
            quote = result.results[0]
            click.echo(f"📈 {quote.title}")

            if quote.price:
                change_str = ""
                if quote.change is not None:
                    sign = "+" if quote.change >= 0 else ""
                    change_str = f" ({sign}{quote.change}%)"
                click.echo(f"    价格: ${quote.price:.2f}{change_str}")

            if quote.extra:
                extra = quote.extra
                if 'market_cap' in extra:
                    click.echo(f"    市值: {extra['market_cap']}")
                if 'pe_ratio' in extra:
                    click.echo(f"    P/E: {extra['pe_ratio']}")
                if 'volume' in extra:
                    click.echo(f"    成交量: {extra['volume']}")
                if '52week_high' in extra and '52week_low' in extra:
                    click.echo(f"    52周区间: {extra.get('52week_low', '-')} - {extra.get('52week_high', '-')}")

            click.echo(f"\n📰 相关新闻:")

            for i, item in enumerate(result.results[1:], 1):
                click.echo(f"\n  【{i}】{item.title}")
                if item.date:
                    click.echo(f"      日期: {item.date}")
                click.echo(f"      来源: {item.source}")
                click.echo(f"      链接: {item.url}")
    finally:
        await cli_instance.close()


@cli.command('google-finance')
@click.argument('symbol')
@click.pass_context
@async_command
async def search_google_finance_cmd(ctx, symbol):
    """搜索Google Finance股票数据

    SYMBOL: 股票代码（如 AAPL, GOOGL）
    """
    cli_instance = BrowserSearchCLI(
        headless=ctx.obj['headless'],
        timeout=ctx.obj['timeout'],
        max_results=ctx.obj['limit'],
        cache_ttl=0 if ctx.obj['no_cache'] else DEFAULT_CACHE_TTL,
        fast_mode=True
    )

    try:
        result = await cli_instance.search_google_finance(symbol)
        output_json = ctx.obj['output_json']

        if output_json:
            click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            click.echo(f"\n{'='*60}")
            click.echo(f"Google Finance: {symbol.upper()}")
            click.echo(f"{'='*60}\n")

            if not result.success:
                click.echo(f"❌ 错误: {result.error}")
                return

            if not result.results:
                click.echo("未找到股票数据")
                return

            # 第一个结果是股票报价
            quote = result.results[0]
            click.echo(f"📈 {quote.title}")

            if quote.price:
                change_str = ""
                if quote.change is not None:
                    sign = "+" if quote.change >= 0 else ""
                    change_str = f" ({sign}{quote.change}%)"
                click.echo(f"    价格: ${quote.price:.2f}{change_str}")

            if quote.extra:
                extra = quote.extra
                if 'market_cap' in extra:
                    click.echo(f"    市值: {extra['market_cap']}")
                if 'pe_ratio' in extra:
                    click.echo(f"    P/E: {extra['pe_ratio']}")
                if 'volume' in extra:
                    click.echo(f"    成交量: {extra['volume']}")

            click.echo(f"\n📰 相关新闻:")

            for i, item in enumerate(result.results[1:], 1):
                click.echo(f"\n  【{i}】{item.title}")
                if item.date:
                    click.echo(f"      日期: {item.date}")
                click.echo(f"      来源: {item.source}")
                click.echo(f"      链接: {item.url}")
    finally:
        await cli_instance.close()


@cli.command('news')
@click.argument('keyword')
@click.option('--source', type=click.Choice(['google', 'bing']), default='google', help='新闻源')
@click.pass_context
@async_command
async def search_news_cmd(ctx, keyword, source):
    """搜索财经新闻

    KEYWORD: 搜索关键词（如 "中概股", "AAPL", "美联储"）
    """
    cli_instance = BrowserSearchCLI(
        headless=ctx.obj['headless'],
        timeout=ctx.obj['timeout'],
        max_results=ctx.obj['limit'],
        cache_ttl=0 if ctx.obj['no_cache'] else DEFAULT_CACHE_TTL,
        fast_mode=True
    )

    try:
        result = await cli_instance.search_news(keyword, source)
        output_json = ctx.obj['output_json']

        if output_json:
            click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            click.echo(f"\n{'='*60}")
            click.echo(f"📰 {source.capitalize()} 新闻搜索: {keyword}")
            click.echo(f"{'='*60}\n")

            if not result.success:
                click.echo(f"❌ 错误: {result.error}")
                return

            if not result.results:
                click.echo("未找到相关新闻")
                return

            for i, item in enumerate(result.results, 1):
                click.echo(f"【{i}】{item.title}")
                if item.snippet:
                    click.echo(f"    摘要: {item.snippet[:150]}...")
                if item.date:
                    click.echo(f"    日期: {item.date}")
                click.echo(f"    来源: {item.source}")
                click.echo(f"    链接: {item.url}")
                click.echo()
    finally:
        await cli_instance.close()


@cli.command('all')
@click.argument('symbol')
@click.pass_context
@async_command
async def search_all_cmd(ctx, symbol):
    """搜索所有来源（综合搜索）

    SYMBOL: 股票代码
    """
    cli_instance = BrowserSearchCLI(
        headless=ctx.obj['headless'],
        timeout=ctx.obj['timeout'],
        max_results=ctx.obj['limit'],
        cache_ttl=0 if ctx.obj['no_cache'] else DEFAULT_CACHE_TTL,
        fast_mode=True  # 使用快速模式
    )
    output_json = ctx.obj['output_json']

    try:
        click.echo(f"\n🔍 正在并行搜索 {symbol.upper()} 的相关信息...\n")

        # 并行搜索所有来源
        results = await cli_instance.search_all_parallel(symbol)

        click.echo("\n✅ 搜索完成!\n")

        # 转换为字典
        results_dict = {k: v.to_dict() for k, v in results.items()}

        if output_json:
            click.echo(json.dumps(results_dict, indent=2, ensure_ascii=False))
        else:
            # 格式化输出
            click.echo("=" * 60)
            click.echo(f"综合搜索结果: {symbol.upper()}")
            click.echo("=" * 60)

            for source, data in results_dict.items():
                click.echo(f"\n{'─' * 40}")
                click.echo(f"📍 {source.upper().replace('_', ' ')}")
                click.echo(f"{'─' * 40}")

                if not data.get('success'):
                    click.echo(f"   ❌ 错误: {data.get('error', 'Unknown')}")
                    continue

                if not data.get('results'):
                    click.echo("   无结果")
                    continue

                for item in data['results'][:5]:
                    click.echo(f"\n   • {item['title']}")
                    if item.get('price'):
                        change = item.get('change', 0) or 0
                        sign = "+" if change >= 0 else ""
                        click.echo(f"     💰 ${item['price']:.2f} ({sign}{change}%)")
                    if item.get('snippet'):
                        click.echo(f"     📝 {item['snippet'][:80]}...")
                    if item.get('url'):
                        click.echo(f"     🔗 {item['url']}")
    finally:
        await cli_instance.close()


def main():
    """入口点"""
    if not HAS_PLAYWRIGHT:
        click.echo("❌ 错误: Playwright 未安装")
        click.echo("\n请运行以下命令安装:")
        click.echo("  pip install playwright")
        click.echo("  playwright install chromium")
        sys.exit(1)

    cli()


if __name__ == '__main__':
    main()