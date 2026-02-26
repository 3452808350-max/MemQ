#!/usr/bin/env python3
"""
简易爬虫 - 读取网页信息
"""

import requests
from bs4 import BeautifulSoup
import json
import sys
from urllib.parse import urljoin, urlparse

# 配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_page(url, encoding=None):
    """获取网页内容"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = encoding or r.apparent_encoding
        return r.text
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return None

def parse_html(html, parser='html.parser'):
    """解析HTML"""
    return BeautifulSoup(html, parser)

def extract_text(soup, selector=None):
    """提取文本"""
    if selector:
        elements = soup.select(selector)
        return [e.get_text(strip=True) for e in elements]
    return soup.get_text(strip=True)

def extract_links(soup, base_url=None):
    """提取所有链接"""
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if base_url:
            href = urljoin(base_url, href)
        links.append(href)
    return links

def extract_images(soup):
    """提取所有图片"""
    return [img.get('src') for img in soup.find_all('img', src=True)]

def extract_table(soup, table_index=0):
    """提取表格数据"""
    tables = soup.find_all('table')
    if table_index >= len(tables):
        return None
    
    rows = []
    for row in tables[table_index].find_all('tr'):
        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
        if cells:
            rows.append(cells)
    return rows

# ========== 预设功能 ==========

def crawl_links(url):
    """爬取页面所有链接"""
    html = get_page(url)
    if not html:
        return
    
    soup = parse_html(html)
    links = extract_links(soup, url)
    
    print(f"🔗 共找到 {len(links)} 个链接:\n")
    for i, link in enumerate(links[:20], 1):
        print(f"{i}. {link}")
    if len(links) > 20:
        print(f"... 还有 {len(links)-20} 个链接")

def crawl_images(url):
    """爬取页面所有图片"""
    html = get_page(url)
    if not html:
        return
    
    soup = parse_html(html)
    images = extract_images(soup)
    
    print(f"🖼️ 共找到 {len(images)} 张图片:\n")
    for i, img in enumerate(images[:15], 1):
        print(f"{i}. {img}")

def crawl_table(url, table_index=0):
    """爬取页面表格"""
    html = get_page(url)
    if not html:
        return
    
    soup = parse_html(html)
    table = extract_table(soup, table_index)
    
    if not table:
        print("❌ 未找到表格")
        return
    
    print(f"📊 表格数据 (共{len(table)}行):\n")
    for row in table:
        print(" | ".join(row))

def crawl_article(url, title_selector='h1', content_selector='p'):
    """爬取文章内容"""
    html = get_page(url)
    if not html:
        return
    
    soup = parse_html(html)
    
    # 标题
    title = soup.select_one(title_selector)
    title = title.get_text(strip=True) if title else "无标题"
    
    # 内容
    paragraphs = soup.select(content_selector)
    content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
    
    print(f"📄 {title}\n")
    print(content[:2000])
    if len(content) > 2000:
        print(f"\n... (还有 {len(content)-2000} 字符)")

def crawl_json_api(url):
    """爬取JSON API"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
    except Exception as e:
        print(f"❌ JSON解析失败: {e}")

# ========== 命令行 ==========

def main():
    if len(sys.argv) < 3:
        print("""
📜 简易爬虫用法:

  python3 crawler.py links <url>        # 获取所有链接
  python3 crawler.py images <url>       # 获取所有图片
  python3 crawler.py table <url>       # 获取表格
  python3 crawler.py article <url>     # 获取文章内容
  python3 crawler.py json <url>        # 获取JSON API

示例:
  python3 crawler.py links https://news.ycombinator.com/
  python3 crawler.py images https://www.example.com/
  python3 crawler.py article https://example.com/blog
        """)
        sys.exit(1)
    
    mode = sys.argv[1]
    url = sys.argv[2]
    
    if mode == 'links':
        crawl_links(url)
    elif mode == 'images':
        crawl_images(url)
    elif mode == 'table':
        crawl_table(url)
    elif mode == 'article':
        crawl_article(url)
    elif mode == 'json':
        crawl_json_api(url)
    else:
        print(f"❌ 未知模式: {mode}")

if __name__ == '__main__':
    main()
