#!/usr/bin/env python3
"""
问财查询模块
负责通过问财API筛选股票
"""

import requests
from typing import Dict, List, Optional
import json
import urllib.parse


class IwencaiService:
    """问财查询服务"""
    
    # 问财API URL
    BASE_URL = "https://www.iwencai.com"
    
    # 浏览器User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def __init__(self, timeout: int = 30):
        """初始化问财服务"""
        self.timeout = timeout
        self.headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    
    def search_quality_stocks(
        self,
        pe_max: float = 30,
        roe_min: float = 15,
        revenue_growth_min: float = 10
    ) -> Dict:
        """
        筛选优质A股
        
        Args:
            pe_max: PE最大值
            roe_min: ROE最小值
            revenue_growth_min: 营收增长最小值
            
        Returns:
            筛选结果
        """
        # 构建查询条件
        query = f"PE<{pe_max} ROE>{roe_min} 营收增长>{revenue_growth_min} A股"
        
        # 尝试不同的问财API接口
        try:
            # 方法1: 使用问财的统一查询接口
            url = "https://www.iwencai.com/unifiedwapwap/home/get_wap_recommend_list"
            params = {
                "query": query,
                "addheader": "",
                "perpage": 20,
                "page": 1,
                "secondaryIntent": "stock",
                "lang": "zh_CN",
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_wap_response(data)
            
        except Exception as e1:
            print(f"方法1失败: {e1}")
        
        try:
            # 方法2: 使用问财的数据接口
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.iwencai.com/data/backtest/info?query={encoded_query}"
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_backtest_response(data)
            
        except Exception as e2:
            print(f"方法2失败: {e2}")
        
        try:
            # 方法3: 使用问财的股票筛选接口
            url = "https://www.iwencai.com/unifiedwapwap/home/search_stocks"
            params = {
                "query": query,
                "lang": "zh_CN",
            }
            
            response = requests.post(
                url,
                data=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_search_response(data)
            
        except Exception as e3:
            print(f"方法3失败: {e3}")
        
        # 如果所有方法都失败，返回空结果并说明原因
        return {
            "success": False,
            "message": "问财API访问失败，请检查网络连接",
            "stocks": []
        }
    
    def _parse_wap_response(self, data: Dict) -> Dict:
        """解析wap接口响应"""
        stocks = []
        
        # 解析股票列表
        if "data" in data and "list" in data["data"]:
            for item in data["data"]["list"]:
                stock = {
                    "code": item.get("code", ""),
                    "name": item.get("name", ""),
                    "pe": item.get("pe", ""),
                    "roe": item.get("roe", ""),
                    "revenue_growth": item.get("revenue_growth", ""),
                    "price": item.get("price", ""),
                    "change": item.get("change", ""),
                }
                stocks.append(stock)
        
        return {
            "success": True,
            "message": f"筛选成功，共找到{len(stocks)}只股票",
            "stocks": stocks
        }
    
    def _parse_backtest_response(self, data: Dict) -> Dict:
        """解析backtest接口响应"""
        stocks = []
        
        # 解析股票列表
        if "data" in data:
            for item in data.get("data", []):
                stock = {
                    "code": item.get("code", ""),
                    "name": item.get("name", ""),
                    "pe": item.get("pe", ""),
                    "roe": item.get("roe", ""),
                    "revenue_growth": item.get("revenue_growth", ""),
                    "price": item.get("price", ""),
                    "change": item.get("change", ""),
                }
                stocks.append(stock)
        
        return {
            "success": True,
            "message": f"筛选成功，共找到{len(stocks)}只股票",
            "stocks": stocks
        }
    
    def _parse_search_response(self, data: Dict) -> Dict:
        """解析search接口响应"""
        stocks = []
        
        # 解析股票列表
        if "data" in data and "items" in data["data"]:
            for item in data["data"]["items"]:
                stock = {
                    "code": item.get("code", ""),
                    "name": item.get("name", ""),
                    "pe": item.get("pe", ""),
                    "roe": item.get("roe", ""),
                    "revenue_growth": item.get("revenue_growth", ""),
                    "price": item.get("price", ""),
                    "change": item.get("change", ""),
                }
                stocks.append(stock)
        
        return {
            "success": True,
            "message": f"筛选成功，共找到{len(stocks)}只股票",
            "stocks": stocks
        }
    
    def get_stock_info(self, stock_code: str) -> Dict:
        """
        获取单只股票的基本面信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            股票信息
        """
        query = f"{stock_code} PE ROE 营收增长"
        
        try:
            url = "https://www.iwencai.com/unifiedwapwap/home/get_single_stock_info"
            params = {
                "code": stock_code,
                "query": query,
                "lang": "zh_CN",
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_single_stock_response(data)
            
        except Exception as e:
            print(f"获取股票信息失败: {e}")
        
        return {
            "success": False,
            "message": f"获取{stock_code}信息失败",
            "info": None
        }
    
    def _parse_single_stock_response(self, data: Dict) -> Dict:
        """解析单只股票信息响应"""
        if "data" in data:
            info = data["data"]
            return {
                "success": True,
                "message": "获取成功",
                "info": {
                    "code": info.get("code", ""),
                    "name": info.get("name", ""),
                    "pe": info.get("pe", ""),
                    "roe": info.get("roe", ""),
                    "revenue_growth": info.get("revenue_growth", ""),
                    "price": info.get("price", ""),
                    "change": info.get("change", ""),
                    "industry": info.get("industry", ""),
                    "market_cap": info.get("market_cap", ""),
                }
            }
        
        return {
            "success": False,
            "message": "解析失败",
            "info": None
        }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="问财查询工具")
    parser.add_argument("--action", type=str, choices=["search", "info"], default="search", help="操作类型")
    parser.add_argument("--pe-max", type=float, default=30, help="PE最大值")
    parser.add_argument("--roe-min", type=float, default=15, help="ROE最小值")
    parser.add_argument("--revenue-growth-min", type=float, default=10, help="营收增长最小值")
    parser.add_argument("--stock-code", type=str, help="股票代码（用于查询单只股票信息）")
    
    args = parser.parse_args()
    
    service = IwencaiService()
    
    if args.action == "search":
        result = service.search_quality_stocks(
            pe_max=args.pe_max,
            roe_min=args.roe_min,
            revenue_growth_min=args.revenue_growth_min
        )
    elif args.action == "info":
        result = service.get_stock_info(args.stock_code)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()