"""
DSS 风险预警系统
基于中国特殊政治经济环境的风险因子
"""
import datetime

# ============ 春晚赞助商预警 ============

class SpringFestivalWarning:
    """春晚赞助商风险预警"""
    
    # 已知的春晚赞助商及其股票
    SPONSORS = {
        # 2026
        "机器人": ["sz.300024", "sz.300014"],  # 人形机器人
        "AI": ["sh.600031"],  # 三六零
        
        # 2020
        "拼多多": ["PDD"],  # 美股
        
        # 2018-2019
        "淘宝": ["BABA"],  # 阿里巴巴
        "支付宝": ["BABA"],
        
        # 2017
        "美的": ["sz.000333"],
        
        # 2015-2016
        "洋河": ["sz.002304"],
        
        # 2015-2017 (房地产高峰)
        "恒大": ["3333.HK"],
        "碧桂园": ["2007.HK"],
    }
    
    # 行业类型
    INDUSTRY_WARNING = {
        "平台型": "例外 - 网络效应",
        "产品型": "警惕 - 赞助高峰=过剩",
        "技术型": "警惕 - 待验证",
        "房地产": "高风险 - 6年周期",
        "白酒": "中高风险 - 5-6年周期",
        "电商": "中风险 - 2-4年周期",
    }
    
    @classmethod
    def check_sponsor(cls, stock_code, stock_name):
        """检查股票是否与春晚赞助商相关"""
        for sponsor, codes in cls.SPONSORS.items():
            if stock_code in codes or sponsor in stock_name:
                return {
                    "is_sponsor": True,
                    "sponsor": sponsor,
                    "warning": cls.get_warning(sponsor),
                }
        return {"is_sponsor": False}
    
    @classmethod
    def get_warning(cls, sponsor):
        """获取预警信息"""
        warnings = {
            "拼多多": "2020年赞助，电商周期2-4年",
            "美的": "2017年赞助，需观察",
            "洋河": "2015-2016年赞助，白酒周期5-6年",
            "恒大": "2015-2017赞助，房地产6年崩盘",
            "碧桂园": "2015-2017赞助，房地产6年崩盘",
            "机器人": "2026年赞助，需警惕",
        }
        return warnings.get(sponsor, "需关注")


# ============ 机构资金监测 ============

class InstitutionalFlowWarning:
    """机构资金流向预警"""
    
    # 风险信号
    SIGNALS = {
        "机构卖出": "风险信号 - 可能下跌",
        "散户涌入": "风险信号 - 情绪过热",
        "北向资金流出": "警惕信号",
        "主力资金流出": "警惕信号",
    }


# ============ 政治周期预警 ============

class PoliticalCycleWarning:
    """政治周期预警"""
    
    # 关键时间节点
    KEY_DATES = [
        "春晚 (春节)",  # 每年1-2月
        "两会",  # 每年3月
        "十一",  # 每年10月
    ]
    
    # 政策周期规律
    POLICY_CYCLES = {
        "春晚前后": "关注行业赞助信号",
        "两会前后": "政策密集期",
        "十一前后": "维稳期",
    }


# ============ 综合预警 ============

class DSSWarningSystem:
    """DSS综合预警系统"""
    
    def __init__(self):
        self.spring_festival = SpringFestivalWarning()
        self.institutional = InstitutionalFlowWarning()
        self.political = PoliticalCycleWarning()
    
    def analyze(self, stock_code, stock_name):
        """综合分析"""
        results = []
        
        # 1. 春晚赞助商检查
        sponsor_info = self.spring_festival.check_sponsor(stock_code, stock_name)
        if sponsor_info["is_sponsor"]:
            results.append({
                "type": "春晚赞助",
                "level": "⚠️ 高风险",
                "detail": sponsor_info["warning"]
            })
        
        # 2. 返回预警结果
        return results
    
    def get_summary(self):
        """获取预警摘要"""
        return {
            "当前关注": "2026年春晚赞助行业(机器人/AI)",
            "风险周期": "赞助后6-12个月",
            "机构行为": "春晚后机构卖出，散户接盘",
        }


if __name__ == "__main__":
    # 测试
    system = DSSWarningSystem()
    
    print("="*50)
    print("DSS 风险预警系统")
    print("="*50)
    
    # 测试股票
    test_stocks = [
        ("sz.300024", "机器人"),
        ("sz.000333", "美的集团"),
        ("sz.002304", "洋河股份"),
    ]
    
    for code, name in test_stocks:
        result = system.analyze(code, name)
        if result:
            print(f"\n{code} {name}:")
            for r in result:
                print(f"  {r['level']} {r['type']}: {r['detail']}")
        else:
            print(f"\n{code} {name}: ✅ 无明显预警")
    
    print("\n" + "="*50)
    print("预警摘要:")
    print("-"*50)
    summary = system.get_summary()
    for k, v in summary.items():
        print(f"{k}: {v}")
