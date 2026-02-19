"""
DSS v4.0 - 最终版 (含风险预警)
整合了:
1. 技术分析
2. 基本面分析
3. 中国特色风险预警
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_v4 import ImprovedStockPicker
from dss_warning import DSSWarningSystem

class DSSFinal:
    """DSS最终版 - 带风险预警"""
    
    def __init__(self):
        self.picker = ImprovedStockPicker()
        self.warning = DSSWarningSystem()
    
    def analyze(self, symbol, name, industry):
        """综合分析 + 风险预警"""
        # 基础分析
        analysis = self.picker.analyze_stock(symbol)
        prediction = self.picker.predict_with_confidence(symbol)
        
        if not analysis or not prediction:
            return None
        
        # 风险预警
        warnings = self.warning.analyze(symbol, name)
        
        # 组装结果
        result = {
            'symbol': symbol,
            'name': name,
            'industry': industry,
            'close': analysis['close'],
            'score': analysis['total_score'],
            'prediction': prediction['direction'],
            'confidence': prediction['confidence'],
            'fundamentals': analysis['fundamentals'],
            'warnings': warnings,
        }
        
        return result
    
    def pick_best(self, stocks, top_n=5):
        """选股 + 预警"""
        results = []
        
        for code, (name, industry) in stocks.items():
            result = self.analyze(code, name, industry)
            if result:
                results.append(result)
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_n]


# 测试
if __name__ == "__main__":
    stocks = {
        'sz.300024': ('机器人', '人形机器人'),
        'sh.600519': ('贵州茅台', '白酒'),
        'sz.002304': ('洋河股份', '白酒'),
        'sh.600835': ('上海机电', '自动化'),
    }
    
    dss = DSSFinal()
    results = dss.pick_best(stocks)
    
    print("="*60)
    print("DSS v4.0 最终版 - 带风险预警")
    print("="*60)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['name']} ({r['symbol']})")
        print(f"   行业: {r['industry']}")
        print(f"   评分: {r['score']:+d}")
        print(f"   预测: {r['prediction']} ({r['confidence']:.0f}%)")
        
        if r['warnings']:
            print(f"   ⚠️ 风险预警:")
            for w in r['warnings']:
                print(f"      {w['level']} {w['type']}: {w['detail']}")
        else:
            print(f"   ✅ 无明显风险预警")
