#!/usr/bin/env python3
"""
东方财富选股模块
通过东方财富接口筛选优质A股
"""

import requests
from typing import Dict, List
import json


class EastmoneyFilter:
    """东方财富选股服务"""
    
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {"User-Agent": self.USER_AGENT}
    
    def filter_stocks(
        self,
        pe_max: float = 30,
        roe_min: float = 15,
        revenue_growth_min: float = 10,
        limit: int = 20
    ) -> Dict:
        """
        筛选优质A股
        
        Args:
            pe_max: PE最大值
            roe_min: ROE最小值（百分比）
            revenue_growth_min: 营收增长最小值（百分比）
            limit: 返回数量限制
            
        Returns:
            筛选结果
        """
        try:
            # 东方财富数据中心选股接口
            # 使用数据中心的筛选功能
            url = "http://datacenter-web.eastmoney.com/api/data/v1/get"
            
            # 构建筛选条件
            # PE: f162 (市盈率) < pe_max
            # ROE: f173 (ROE) > roe_min
            # 营收增长: 需要其他字段
            
            params = {
                "reportName": "RPT_LICO_FN_CPD",
                "columns": "ALL",
                "filter": f"(f162<{pe_max})(f173>{roe_min})",
                "pageNumber": 1,
                "pageSize": limit,
                "sortTypes": -1,
                "sortColumns": "f173",  # 按ROE降序
                "source": "WEB",
                "client": "WEB",
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            data = response.json()
            
            if "result" in data and "data" in data["result"]:
                stocks = []
                for item in data["result"]["data"]:
                    stock = {
                        "code": item.get("SECUCODE", "").split(".")[-1] if "." in str(item.get("SECUCODE", "")) else item.get("SECUCODE", ""),
                        "name": item.get("SECURITY_NAME_ABR", ""),
                        "pe": item.get("PE_TTM", 0),
                        "roe": item.get("ROE", 0),
                        "revenue_growth": item.get("OPERATE_INCOME_GROWTH", 0),
                        "industry": item.get("INDUSTRY_NAME", ""),
                    }
                    stocks.append(stock)
                
                return {
                    "success": True,
                    "message": f"筛选成功，共找到{len(stocks)}只股票",
                    "stocks": stocks
                }
            
        except Exception as e:
            print(f"东方财富数据中心接口失败: {e}")
        
        try:
            # 方法2: 使用东方财富股票列表接口 - 获取更多数据再本地筛选
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            
            params = {
                "pn": 1,
                "pz": 200,  # 获取更多数据
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f173",  # 按ROE排序
                "fs": "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23",  # A股市场
                "fields": "f12,f14,f2,f3,f15,f16,f17,f162,f167,f173",
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            data = response.json()
            
            if "data" in data and "diff" in data["data"]:
                stocks = []
                for item in data["data"]["diff"]:
                    pe = item.get("f162", "-")
                    roe = item.get("f173", 0)
                    
                    # 手动筛选 - 处理数据类型
                    try:
                        # PE字段可能是字符串 "-" 或数值
                        pe_val = 0
                        if pe != "-" and pe != "" and pe is not None:
                            pe_val = float(pe)
                        
                        roe_val = float(roe) if roe not in ["-", "", None] else 0
                        
                        # 只筛选 PE有效且在范围内的股票
                        if pe_val > 0 and pe_val < pe_max and roe_val > roe_min:
                            stock = {
                                "code": item.get("f12", ""),
                                "name": item.get("f14", ""),
                                "price": float(item.get("f2", 0)) if item.get("f2") not in ["-", "", None] else 0,
                                "change_pct": float(item.get("f3", 0)) if item.get("f3") not in ["-", "", None] else 0,
                                "high": float(item.get("f15", 0)) if item.get("f15") not in ["-", "", None] else 0,
                                "low": float(item.get("f16", 0)) if item.get("f16") not in ["-", "", None] else 0,
                                "open": float(item.get("f17", 0)) if item.get("f17") not in ["-", "", None] else 0,
                                "pe": pe_val,
                                "pb": float(item.get("f167", 0)) if item.get("f167") not in ["-", "", None] else 0,
                                "roe": roe_val,
                            }
                            stocks.append(stock)
                    except (ValueError, TypeError):
                        pass
                
                return {
                    "success": True,
                    "message": f"筛选成功，共找到{len(stocks)}只符合条件的股票",
                    "stocks": stocks,
                    "source": "eastmoney_clist"
                }
            
        except Exception as e:
            print(f"东方财富clist接口失败: {e}")
        
        try:
            # 方法3: 先获取所有A股数据，再本地筛选
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            
            params = {
                "pn": 1,
                "pz": 100,  # 获取100只ROE最高的股票
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f173",
                "fs": "m:0+t:6,m:0+t:13,m:0+t:80,m:1+t:2,m:1+t:23",  # A股
                "fields": "f12,f14,f2,f3,f15,f16,f17,f162,f167,f173",
            }
            
            response = requests.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            data = response.json()
            
            if "data" in data and "diff" in data["data"]:
                stocks = []
                for item in data["data"]["diff"]:
                    pe = item.get("f162", 0)
                    roe = item.get("f173", 0)
                    
                    # 本地筛选 PE<30, ROE>15
                    try:
                        pe_val = float(pe) if pe not in ["-", "", None] else 0
                        roe_val = float(roe) if roe not in ["-", "", None] else 0
                        
                        if pe_val > 0 and pe_val < pe_max and roe_val > roe_min:
                            stock = {
                                "code": item.get("f12", ""),
                                "name": item.get("f14", ""),
                                "price": float(item.get("f2", 0)) if item.get("f2") not in ["-", "", None] else 0,
                                "change_pct": float(item.get("f3", 0)) if item.get("f3") not in ["-", "", None] else 0,
                                "high": float(item.get("f15", 0)) if item.get("f15") not in ["-", "", None] else 0,
                                "low": float(item.get("f16", 0)) if item.get("f16") not in ["-", "", None] else 0,
                                "open": float(item.get("f17", 0)) if item.get("f17") not in ["-", "", None] else 0,
                                "pe": pe_val,
                                "pb": float(item.get("f167", 0)) if item.get("f167") not in ["-", "", None] else 0,
                                "roe": roe_val,
                            }
                            stocks.append(stock)
                    except (ValueError, TypeError):
                        pass
                
                # 按ROE降序排序
                stocks.sort(key=lambda x: x["roe"], reverse=True)
                
                # 取前limit只
                stocks = stocks[:limit]
                
                return {
                    "success": True,
                    "message": f"筛选成功，共找到{len(stocks)}只符合条件的股票（PE<{pe_max}, ROE>{roe_min}%）",
                    "stocks": stocks,
                    "source": "eastmoney_clist_filtered",
                    "criteria": {
                        "pe_max": pe_max,
                        "roe_min": roe_min,
                    }
                }
            
        except Exception as e3:
            print(f"方法3失败: {e3}")
            return {
                "success": False,
                "message": f"筛选失败: 所有方法都无法获取数据",
                "stocks": []
            }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="东方财富选股工具")
    parser.add_argument("--pe-max", type=float, default=30, help="PE最大值")
    parser.add_argument("--roe-min", type=float, default=15, help="ROE最小值（百分比）")
    parser.add_argument("--limit", type=int, default=20, help="返回数量")
    
    args = parser.parse_args()
    
    filter_service = EastmoneyFilter()
    result = filter_service.filter_stocks(
        pe_max=args.pe_max,
        roe_min=args.roe_min,
        limit=args.limit
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()