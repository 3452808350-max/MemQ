#!/usr/bin/env python3
"""
Seeking Alpha Crawler - 中概股分析文章爬虫 (增强版)

功能：
1. get_seeking_alpha_analysis(symbol) - 获取股票分析文章
2. get_trending_china_stocks() - 获取热门中概股列表
3. 解析文章标题、摘要、作者、日期、评级
4. 处理反爬：随机UA、请求间隔、Session复用

使用方法：
    from seeking_alpha_crawler import SeekingAlphaCrawler
    
    crawler = SeekingAlphaCrawler()
    articles = crawler.get_seeking_alpha_analysis("BABA")
    china_stocks = crawler.get_trending_china_stocks()
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import re
import json
from datetime import datetime
from typing import List, Dict, Optional
import logging
from urllib.parse import urljoin, urlparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 热门中概股列表
CHINA_STOCKS = [
    "BABA",   # 阿里巴巴
    "JD",     # 京东
    "PDD",    # 拼多多
    "NIO",    # 蔚来
    "BIDU",   # 百度
    "TME",    # 腾讯音乐
    "BILI",   # 哔哩哔哩
    "LI",     # 理想汽车
    "XPEV",   # 小鹏汽车
    "FUTU",   # 富途控股
    "TAL",    # 好未来
    "VIPS",   # 唯品会
    "ZTO",    # 中通快递
    "NTES",   # 网易
    "IQ",     # 爱奇艺
]

# 随机User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class SeekingAlphaCrawler:
    """Seeking Alpha 爬虫类"""
    
    def __init__(self, delay_range: tuple = (2, 5), max_retries: int = 3):
        """
        初始化爬虫
        
        Args:
            delay_range: 请求间隔时间范围（秒），默认2-5秒
            max_retries: 最大重试次数
        """
        self.base_url = "https://seekingalpha.com"
        self.session = requests.Session()
        self.delay_range = delay_range
        self.max_retries = max_retries
        self._init_session()
        
    def _init_session(self):
        """初始化Session"""
        self._set_headers()
        # 设置重试适配器
        retry_adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.packages.urllib3.util.Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
        )
        self.session.mount("https://", retry_adapter)
        self.session.mount("http://", retry_adapter)
        
    def _set_headers(self):
        """设置请求头"""
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        })
        
    def _random_delay(self, extra: float = 0):
        """随机延迟"""
        delay = random.uniform(*self.delay_range) + extra
        time.sleep(delay)
        
    def _rotate_user_agent(self):
        """轮换User-Agent"""
        self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
        
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """
        发送HTTP请求，带重试机制
        
        Args:
            url: 请求URL
            
        Returns:
            Response对象或None
        """
        for attempt in range(self.max_retries):
            try:
                self._rotate_user_agent()
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 403:
                    logger.warning(f"403 Forbidden，等待后重试... (尝试 {attempt + 1}/{self.max_retries})")
                    self._random_delay(extra=5)
                    continue
                    
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"请求失败: {e} (尝试 {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    self._random_delay(extra=3)
                else:
                    logger.error(f"请求最终失败: {url}")
                    return None
                    
        return None
        
    def _extract_rating_from_title(self, title: str) -> Optional[str]:
        """
        从标题中提取评级信息
        
        Args:
            title: 文章标题
            
        Returns:
            评级字符串 (Bullish/Bearish/Neutral) 或 None
        """
        title_lower = title.lower()
        
        # 看涨信号
        bullish_keywords = [
            "buy", "strong buy", "bullish", "upgrade", "undervalued",
            "opportunity", "gains", "rally", "bull case", "long",
            "attractive", "compelling", "discount", "gift", "loading up",
            "soar", "rocket", "on sale", "winner", "outperform"
        ]
        
        # 看跌信号
        bearish_keywords = [
            "sell", "strong sell", "bearish", "downgrade", "overvalued",
            "avoid", "short", "risk", "bear case", "value trap",
            "concern", "warning", "bubble", "collapse", "underperform",
            "hazard", "danger"
        ]
        
        bullish_count = sum(1 for kw in bullish_keywords if kw in title_lower)
        bearish_count = sum(1 for kw in bearish_keywords if kw in title_lower)
        
        # 额外检查：标题中的明确评级关键词
        if re.search(r"\b(buy|strong buy|bullish)\b.*\b(upgrade|rating)\b", title_lower):
            return "Bullish"
        if re.search(r"\b(sell|strong sell|bearish)\b.*\b(downgrade|rating)\b", title_lower):
            return "Bearish"
            
        if bullish_count > bearish_count:
            return "Bullish"
        elif bearish_count > bullish_count:
            return "Bearish"
        elif bullish_count > 0 and bullish_count == bearish_count:
            return "Neutral"
        else:
            return None
            
    def _parse_date(self, date_text: str) -> str:
        """规范化日期格式"""
        if not date_text:
            return ""
            
        # 常见日期格式映射
        month_map = {
            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
        }
        
        # 尝试解析 "Mar. 23" 格式
        match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2})", date_text)
        if match:
            month = month_map.get(match.group(1), "01")
            day = match.group(2).zfill(2)
            year = datetime.now().year
            return f"{year}-{month}-{day}"
            
        return date_text.strip()
        
    def get_seeking_alpha_analysis(self, symbol: str, pages: int = 2) -> List[Dict]:
        """
        获取指定股票的分析文章
        
        Args:
            symbol: 股票代码 (如 BABA, JD, PDD)
            pages: 要爬取的页数，默认2页
            
        Returns:
            文章列表
        """
        articles = []
        symbol = symbol.upper()
        
        for page in range(1, pages + 1):
            try:
                url = f"{self.base_url}/symbol/{symbol}/analysis"
                if page > 1:
                    url = f"{url}?page={page}"
                    
                logger.info(f"正在获取 {symbol} 的分析文章 - 第 {page} 页")
                
                response = self._make_request(url)
                if not response:
                    continue
                    
                soup = BeautifulSoup(response.text, "html.parser")
                
                # 方法1: 查找文章链接
                article_links = soup.find_all("a", href=re.compile(r"/article/\d+"))
                
                for link in article_links:
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    
                    # 跳过无效或空标题
                    if not title or len(title) < 10:
                        continue
                    if "Create Free Account" in title or "Continue with" in title:
                        continue
                        
                    # 获取完整URL
                    full_url = urljoin(self.base_url, href)
                    
                    # 查找作者和日期
                    parent = link.find_parent("article") or link.find_parent("div")
                    author = "Unknown"
                    date = ""
                    comments = 0
                    
                    if parent:
                        # 作者
                        author_link = parent.find("a", href=re.compile(r"/author/"))
                        if author_link:
                            author = author_link.get_text(strip=True)
                            
                        # 日期
                        date_text = parent.find(string=re.compile(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?,?\s"))
                        if date_text:
                            date = self._parse_date(str(date_text).strip())
                            
                        # 评论数
                        comments_link = parent.find("a", href=re.compile(r"#scroll_comments"))
                        if comments_link:
                            comments_text = comments_link.get_text(strip=True)
                            match = re.search(r"(\d+)", comments_text)
                            if match:
                                comments = int(match.group(1))
                                
                    # 提取文章ID
                    article_id = ""
                    id_match = re.search(r"/article/(\d+)", href)
                    if id_match:
                        article_id = id_match.group(1)
                        
                    # 从标题推断评级
                    rating = self._extract_rating_from_title(title)
                    
                    articles.append({
                        "article_id": article_id,
                        "title": title,
                        "author": author,
                        "date": date,
                        "comments": comments,
                        "link": full_url,
                        "rating": rating,
                        "symbol": symbol,
                        "crawled_at": datetime.now().isoformat(),
                    })
                    
                logger.info(f"第 {page} 页获取到 {len(article_links)} 个链接")
                
                # 随机延迟
                self._random_delay()
                
            except Exception as e:
                logger.error(f"处理第 {page} 页时出错: {e}")
                continue
                
        # 去重
        seen = set()
        unique_articles = []
        for article in articles:
            article_id = article.get("article_id", "")
            if article_id and article_id not in seen:
                seen.add(article_id)
                unique_articles.append(article)
            elif not article_id:
                # 如果没有ID，用标题去重
                title_key = article.get("title", "")[:50]
                if title_key not in seen:
                    seen.add(title_key)
                    unique_articles.append(article)
                    
        logger.info(f"总共获取到 {len(unique_articles)} 篇唯一文章")
        return unique_articles
        
    def get_article_summary(self, article_url: str) -> Dict:
        """
        获取文章摘要
        
        Args:
            article_url: 文章URL
            
        Returns:
            包含文章摘要的字典
        """
        try:
            response = self._make_request(article_url)
            if not response:
                return {"url": article_url, "summary": "", "error": "请求失败"}
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取摘要
            summary = ""
            
            # 方法1: 查找Summary标题后的列表
            summary_heading = soup.find(["h2", "h3"], string=re.compile(r"Summary", re.I))
            if summary_heading:
                summary_list = summary_heading.find_next("ul")
                if summary_list:
                    items = summary_list.find_all("li")
                    summary = "\n".join([item.get_text(strip=True) for item in items if item.get_text(strip=True)])
                    
            # 方法2: 查找包含摘要的div
            if not summary:
                summary_div = soup.find("div", class_=lambda x: x and "summary" in str(x).lower())
                if summary_div:
                    summary = summary_div.get_text(strip=True)
                    
            self._random_delay()
            
            return {
                "url": article_url,
                "summary": summary[:2000] if summary else "",
                "has_summary": bool(summary),
            }
            
        except Exception as e:
            logger.error(f"获取文章摘要失败: {e}")
            return {
                "url": article_url,
                "summary": "",
                "error": str(e),
            }
            
    def get_trending_china_stocks(self) -> List[Dict]:
        """
        获取热门中概股列表及基本信息
        
        Returns:
            中概股列表
        """
        stocks = []
        
        for i, symbol in enumerate(CHINA_STOCKS[:10]):  # 限制前10个
            try:
                logger.info(f"获取 {symbol} 信息 ({i+1}/10)...")
                
                url = f"{self.base_url}/symbol/{symbol}"
                response = self._make_request(url)
                
                if not response:
                    stocks.append({
                        "symbol": symbol,
                        "name": "",
                        "price": "",
                        "change": "",
                        "url": url,
                        "error": "请求失败",
                    })
                    continue
                    
                soup = BeautifulSoup(response.text, "html.parser")
                
                # 提取股票名称
                name = ""
                title_elem = soup.find("h1")
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    # 移除股票代码
                    name = re.sub(rf"^{symbol}\s*", "", title_text)
                    # 清理多余文字
                    name = re.sub(r"Stock Price.*", "", name).strip()
                    
                # 提取价格 - 查找美元符号
                price = ""
                price_elem = soup.find(string=re.compile(r"\$\d+"))
                if price_elem:
                    match = re.search(r"\$([\d,.]+)", str(price_elem))
                    if match:
                        price = match.group(1).replace(",", "")
                        
                # 提取涨跌幅
                change = ""
                change_elem = soup.find(string=re.compile(r"[+-][\d.]+%"))
                if change_elem:
                    match = re.search(r"([+-][\d.]+%)", str(change_elem))
                    if match:
                        change = match.group(1)
                        
                stocks.append({
                    "symbol": symbol,
                    "name": name[:50] if name else "",
                    "price": price,
                    "change": change,
                    "url": url,
                })
                
                self._random_delay()
                
            except Exception as e:
                logger.error(f"获取 {symbol} 信息失败: {e}")
                stocks.append({
                    "symbol": symbol,
                    "name": "",
                    "price": "",
                    "change": "",
                    "url": f"{self.base_url}/symbol/{symbol}",
                    "error": str(e),
                })
                
        return stocks
        
    def search_articles(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        搜索文章
        
        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            文章列表
        """
        try:
            url = f"{self.base_url}/search?q={keyword}&tab=articles"
            
            response = self._make_request(url)
            if not response:
                return []
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            articles = []
            article_links = soup.find_all("a", href=re.compile(r"/article/\d+"))
            
            for link in article_links[:limit]:
                href = link.get("href", "")
                title = link.get_text(strip=True)
                
                if not title or len(title) < 10:
                    continue
                    
                articles.append({
                    "title": title,
                    "link": urljoin(self.base_url, href),
                    "rating": self._extract_rating_from_title(title),
                })
                
            return articles
            
        except Exception as e:
            logger.error(f"搜索文章失败: {e}")
            return []
            
    def get_stock_rating_summary(self, symbol: str) -> Dict:
        """
        获取股票评级汇总
        
        Args:
            symbol: 股票代码
            
        Returns:
            评级汇总字典
        """
        try:
            url = f"{self.base_url}/symbol/{symbol.upper()}/ratings"
            
            response = self._make_request(url)
            if not response:
                return {"symbol": symbol, "error": "请求失败"}
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取评级信息
            ratings = {
                "symbol": symbol.upper(),
                "sa_rating": "",
                "wall_street_rating": "",
                "quant_rating": "",
                "url": url,
            }
            
            # 查找评级元素
            rating_divs = soup.find_all("div", class_=lambda x: x and "rating" in str(x).lower())
            for div in rating_divs:
                text = div.get_text(strip=True).lower()
                if "sa" in text or "analyst" in text:
                    match = re.search(r"(buy|sell|hold|strong)", text)
                    if match:
                        ratings["sa_rating"] = match.group(1).title()
                elif "wall street" in text:
                    match = re.search(r"(buy|sell|hold|strong)", text)
                    if match:
                        ratings["wall_street_rating"] = match.group(1).title()
                elif "quant" in text:
                    match = re.search(r"(buy|sell|hold|strong)", text)
                    if match:
                        ratings["quant_rating"] = match.group(1).title()
                        
            self._random_delay()
            return ratings
            
        except Exception as e:
            logger.error(f"获取评级汇总失败: {e}")
            return {"symbol": symbol, "error": str(e)}


def get_seeking_alpha_analysis(symbol: str, pages: int = 2) -> List[Dict]:
    """
    便捷函数：获取股票分析文章
    
    Args:
        symbol: 股票代码
        pages: 页数
        
    Returns:
        文章列表
    """
    crawler = SeekingAlphaCrawler()
    return crawler.get_seeking_alpha_analysis(symbol, pages)


def get_trending_china_stocks() -> List[Dict]:
    """
    便捷函数：获取热门中概股
    
    Returns:
        中概股列表
    """
    crawler = SeekingAlphaCrawler()
    return crawler.get_trending_china_stocks()


# 测试代码
if __name__ == "__main__":
    print("=" * 70)
    print("Seeking Alpha 爬虫测试")
    print("=" * 70)
    
    crawler = SeekingAlphaCrawler(delay_range=(1, 2))
    
    # 测试1：获取BABA分析文章
    print("\n【测试1】获取 BABA 分析文章...")
    print("-" * 70)
    articles = crawler.get_seeking_alpha_analysis("BABA", pages=1)
    
    if articles:
        print(f"\n✅ 获取到 {len(articles)} 篇文章:\n")
        for i, article in enumerate(articles[:10], 1):
            rating = article.get('rating')
            rating_display = f"[{rating}]" if rating else "[N/A]"
            print(f"{i:2}. {rating_display:10} {article['title'][:60]}...")
            print(f"    作者: {article['author']} | 日期: {article['date']}")
            print(f"    链接: {article['link'][:70]}...")
            print()
    else:
        print("❌ 未获取到文章，可能需要登录或遇到反爬限制")
        
    # 测试2：获取热门中概股
    print("\n" + "=" * 70)
    print("【测试2】获取热门中概股列表...")
    print("-" * 70)
    stocks = crawler.get_trending_china_stocks()
    
    if stocks:
        print(f"\n✅ 获取到 {len(stocks)} 只中概股:\n")
        print(f"{'股票代码':<10} {'公司名称':<35} {'价格':>10} {'涨跌幅':>10}")
        print("-" * 70)
        for stock in stocks:
            name = stock.get('name', '')[:30]
            price = stock.get('price', '-')
            change = stock.get('change', '-')
            error = stock.get('error', '')
            
            if error:
                print(f"{stock['symbol']:<10} {error}")
            else:
                print(f"{stock['symbol']:<10} {name:<35} {price:>10} {change:>10}")
    else:
        print("❌ 未获取到股票信息")
        
    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)
    print("\n使用方法:")
    print("  from seeking_alpha_crawler import SeekingAlphaCrawler")
    print("  crawler = SeekingAlphaCrawler()")
    print("  articles = crawler.get_seeking_alpha_analysis('BABA')")
    print("  stocks = crawler.get_trending_china_stocks()")
    print("=" * 70)