"""
DSS Swarm - 轻度集成方案 (简化版)
直接使用DSS模块，通过Agent调用
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_modules.data_loader import get_stock_data, fetch_baostock
from dss_modules.features import add_technical_indicators
from dss_modules.models import StockModel
import numpy as np

# ============ 工具函数 ============

def get_stock_price(symbol: str) -> str:
    """获取股票价格"""
    df = get_stock_data(symbol, 10, 'baostock')
    if df is None or len(df) == 0:
        return f"无法获取 {symbol} 的数据"
    latest = df.iloc[-1]
    return f"{symbol}: 收盘价 {latest['Close']:.2f}, 近{len(df)}天数据"

def analyze_technical(symbol: str) -> str:
    """技术分析"""
    df = get_stock_data(symbol, 60, 'baostock')
    if df is None or len(df) < 30:
        return f"数据不足 {symbol}"
    
    df = add_technical_indicators(df)
    df = df.dropna()
    if len(df) < 1:
        return f"数据不足 {symbol}"
    
    latest = df.iloc[-1]
    signals = []
    
    rsi = latest.get('RSI', 50)
    if rsi < 30:
        signals.append("RSI超卖(买入信号)")
    elif rsi > 70:
        signals.append("RSI超买(卖出信号)")
    
    macd = latest.get('MACD', 0)
    if macd > 0:
        signals.append("MACD金叉(看涨)")
    else:
        signals.append("MACD死叉(看跌)")
    
    # 均线
    ma5 = latest.get('MA5', 0)
    ma20 = latest.get('MA20', 0)
    if ma5 > ma20:
        signals.append("MA5>MA20(多头)")
    else:
        signals.append("MA5<MA20(空头)")
    
    return f"{symbol} 技术信号:\\n  " + "\\n  ".join(signals)

def predict_stock(symbol: str) -> str:
    """DSS预测"""
    df = get_stock_data(symbol, 150, 'baostock')
    if df is None or len(df) < 50:
        return f"数据不足无法预测 {symbol}"
    
    df = add_technical_indicators(df)
    df = df.dropna()
    
    df['label'] = (df['Close'].shift(-5) / df['Close'] > 1.02).astype(int)
    df = df.dropna()
    
    feature_cols = [c for c in df.columns if c not in ['Open', 'High', 'Low', 'Close', 'Volume', 'label']]
    X = df[feature_cols].values
    y = df['label'].values
    
    valid = ~np.isnan(X).any(axis=1)
    X, y = X[valid], y[valid]
    
    if len(X) < 20:
        return f"有效数据不足 {symbol}"
    
    split = len(X) - 10
    model = StockModel('lgbm')
    model.fit(X[:split], y[:split])
    proba = model.predict_proba(X[split:])
    
    direction = "上涨 📈" if proba[0] > 0.5 else "下跌 📉"
    confidence = abs(proba[0] - 0.5) * 2 * 100
    
    return f"{symbol} 5天后预测:\\n  方向: {direction}\\n  置信度: {confidence:.0f}%"

def create_report(symbol: str) -> str:
    """生成分析报告"""
    price = get_stock_price(symbol)
    tech = analyze_technical(symbol)
    pred = predict_stock(symbol)
    
    return f"""
╔══════════════════════════════════════╗
║     📊 {symbol} 分析报告             ║
╠══════════════════════════════════════╣
║                                      ║
║ 💰 价格信息:                         ║
║   {price}              ║
║                                      ║
║ 📈 技术分析:                         ║
║   {tech}                  ║
║                                      ║
║ 🔮 预测:                             ║
║   {pred}                   ║
║                                      ║
╚══════════════════════════════════════╝
生成时间: 2026-02-17
"""

# ============ Agent模拟 ============

class DSSAgent:
    """简单的DSS Agent (模拟Swarms Agent)"""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
    
    def run(self, task: str) -> str:
        """执行任务"""
        if "价格" in task:
            symbol = self.extract_symbol(task)
            return get_stock_price(symbol)
        elif "分析" in task or "技术" in task:
            symbol = self.extract_symbol(task)
            return analyze_technical(symbol)
        elif "预测" in task:
            symbol = self.extract_symbol(task)
            return predict_stock(symbol)
        elif "报告" in task:
            symbol = self.extract_symbol(task)
            return create_report(symbol)
        else:
            return f"无法理解任务: {task}"
    
    def extract_symbol(self, text: str) -> str:
        """提取股票代码"""
        # 简单提取
        if "茅台" in text or "600519" in text:
            return "sh.600519"
        elif "平安" in text or "601318" in text:
            return "sh.601318"
        elif "苹果" in text or "AAPL" in text:
            return "AAPL"
        return "sh.600519"  # 默认

# ============ 测试 ============

if __name__ == "__main__":
    print("🚀 DSS Swarm 测试")
    print("=" * 50)
    
    # 创建Agent
    agent = DSSAgent("DSSAssistant", "金融分析")
    
    # 测试任务
    tasks = [
        "获取茅台价格",
        "分析茅台技术面",
        "预测茅台走势",
        "生成茅台分析报告"
    ]
    
    for task in tasks:
        print(f"\n📌 任务: {task}")
        print("-" * 40)
        result = agent.run(task)
        print(result)
    
    print("\n✅ 测试完成!")
