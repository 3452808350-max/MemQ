#!/usr/bin/env python3
"""
股票信息获取模块
从腾讯/东方财富获取股票实时行情和基本面数据
"""

import requests
from typing import Dict, List
import json
import re


class StockInfoFetcher:
    """股票信息获取服务"""
    
    # 腾讯股票数据接口
    TENCENT_URL = "http://qt.gtimg.cn/q="
    
    # 东方财富数据接口
    EASTMONEY_URL = "http://push2.eastmoney.com/api/qt/stock/get"
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.headers = {"User-Agent": self.USER_AGENT}
    
    def get_realtime_quotes(self, stock_codes: List[str]) -> Dict:
        """
        获取实时行情
        
        Args:
            stock_codes: 股票代码列表（如 ['sh601336', 'sz000999']）
            
        Returns:
            股票行情数据
        """
        # 构建腾讯接口URL
        codes_str = ",".join(stock_codes)
        url = f"{self.TENCENT_URL}{codes_str}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.encoding = 'gbk'
            text = response.text
            
            stocks = []
            lines = text.strip().split('\n')
            
            for line in lines:
                if not line.startswith('v_'):
                    continue
                
                # 解析数据
                match = re.match(r'v_([^=]+)="([^"]*)"', line)
                if not match:
                    continue
                
                code_key = match.group(1)
                data_str = match.group(2)
                
                parts = data_str.split('~')
                if len(parts) < 45:
                    continue
                
                # 提取关键数据
                stock = {
                    "code_key": code_key,
                    "code": parts[2] if len(parts) > 2 else "",
                    "name": parts[1] if len(parts) > 1 else "",
                    "price": float(parts[3]) if len(parts) > 3 and parts[3] else 0,
                    "open": float(parts[5]) if len(parts) > 5 and parts[5] else 0,
                    "close_yesterday": float(parts[4]) if len(parts) > 4 and parts[4] else 0,
                    "high": float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                    "low": float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                    "volume": int(parts[6]) if len(parts) > 6 and parts[6] else 0,
                    "amount": float(parts[37]) if len(parts) > 37 and parts[37] else 0,
                    "change": float(parts[31]) if len(parts) > 31 and parts[31] else 0,
                    "change_pct": float(parts[32]) if len(parts) > 32 and parts[32] else 0,
                    "pe": float(parts[39]) if len(parts) > 39 and parts[39] else 0,
                    "market_cap": float(parts[45]) if len(parts) > 45 and parts[45] else 0,
                }
                
                # 计算涨跌幅
                if stock["close_yesterday"] > 0:
                    stock["change_pct_calc"] = (stock["price"] - stock["close_yesterday"]) / stock["close_yesterday"] * 100
                else:
                    stock["change_pct_calc"] = 0
                
                stocks.append(stock)
            
            return {
                "success": True,
                "stocks": stocks,
                "count": len(stocks)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stocks": []
            }
    
    def get_stock_fundamentals(self, stock_code: str) -> Dict:
        """
        获取股票基本面数据（PE、ROE等）
        
        Args:
            stock_code: 股票代码（如 601336）
            
        Returns:
            基本面数据
        """
        # 根据代码判断市场
        if stock_code.startswith('6'):
            secid = f"1.{stock_code}"  # 上海
        else:
            secid = f"0.{stock_code}"  # 深圳
        
        try:
            # 东方财富接口
            url = "http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": secid,
                "fields": "f57,f58,f115,f162,f167,f173,f12,f13,f14,f170,f171",
                "ut": "fa5fd1943b74038b29dcb6d6aafe98f4",
            }
            
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            data = response.json()
            
            if "data" in data and data["data"]:
                d = data["data"]
                return {
                    "success": True,
                    "code": stock_code,
                    "name": d.get("f58", ""),
                    "pe": d.get("f162", 0),  # 市盈率
                    "pb": d.get("f167", 0),  # 市净率
                    "roe": d.get("f173", 0),  # ROE
                    "total_mv": d.get("f115", 0),  # 总市值
                    "circ_mv": d.get("f170", 0),  # 流通市值
                }
            
        except Exception as e:
            print(f"获取基本面失败: {e}")
        
        return {
            "success": False,
            "code": stock_code,
            "error": "获取失败"
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="股票信息获取工具")
    parser.add_argument("--action", type=str, choices=["quotes", "fundamentals"], default="quotes")
    parser.add_argument("--codes", type=str, help="股票代码列表，逗号分隔（如 sh601336,sz000999）")
    parser.add_argument("--code", type=str, help="单只股票代码")
    
    args = parser.parse_args()
    
    fetcher = StockInfoFetcher()
    
    if args.action == "quotes":
        codes = args.codes.split(",") if args.codes else ["sh601336", "sh603596", "sz000999"]
        result = fetcher.get_realtime_quotes(codes)
    elif args.action == "fundamentals":
        result = fetcher.get_stock_fundamentals(args.code)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()