#!/usr/bin/env python3
"""用 Scrapling 爬取 AMZN 股票数据"""

from scrapling.fetchers import StealthyFetcher
import pandas as pd
from datetime import datetime

def fetch_amzn_from_yahoo():
    """从 Yahoo Finance 爬取 AMZN 数据"""
    
    url = "https://finance.yahoo.com/quote/AMZN/history"
    
    print(f"🕷️ 正在爬取 {url}...")
    
    # 使用 StealthyFetcher 绕过反爬
    StealthyFetcher.adaptive = True
    page = StealthyFetcher.fetch(
        url, 
        headless=True, 
        network_idle=True,
        timeout=30000
    )
    
    # 查找历史数据表格
    table = page.css('table', adaptive=True)
    
    if not table:
        print("❌ 没找到数据表格")
        # 尝试获取页面内容调试
        print(f"页面标题：{page.title}")
        print(f"页面内容前 500 字符：{page.text[:500]}")
        return None
    
    print(f"✅ 找到 {len(table)} 个表格")
    
    # 解析表格数据
    data = []
    rows = page.css('tr', adaptive=True)
    
    for row in rows:
        cells = row.css('td')
        if len(cells) >= 6:
            try:
                date_str = cells[0].text.strip()
                close = cells[4].text.strip().replace(',', '')
                
                # 简单验证
                if date_str and close:
                    data.append({
                        'date': date_str,
                        'close': float(close)
                    })
            except Exception as e:
                continue
    
    if data:
        print(f"✅ 爬取到 {len(data)} 条数据")
        df = pd.DataFrame(data)
        print(df.head())
        return df
    else:
        print("❌ 没解析到数据")
        return None

if __name__ == "__main__":
    fetch_amzn_from_yahoo()
