#!/usr/bin/env python3
"""
DSS 配置管理模块
集中管理所有评分权重和参数
"""

# ==================== 评分权重 ====================
WEIGHTS = {
    'technical': 0.40,      # 技术指标 (RSI/MACD/均线/布林带)
    'ml_predict': 0.15,     # ML 预测
    'lstm_predict': 0.10,   # LSTM 预测
    'trend': 0.10,          # 趋势预测
    'risk': 0.15,           # 风控评估
    'market_regime': 0.10,  # 市场状态
}

# ==================== 技术指标参数 ====================
RSI = {
    'period': 14,
    'oversold': 30,
    'overbought': 70,
    'adaptive_periods': [10, 14, 21],  # 自适应周期选项
}

MACD = {
    'trend': {'fast': 12, 'slow': 26, 'signal': 9},    # 趋势市场
    'range': {'fast': 5, 'slow': 13, 'signal': 7},     # 震荡市场
}

MA = {
    'short': 5,
    'medium': 20,
    'long': 60,
}

BB = {
    'period': 20,
    'std': 2.0,
}

# ==================== 风控参数 ====================
RISK = {
    'stop_loss': 0.05,        # 止损 5%
    'take_profit': 0.15,      # 止盈 15%
    'position_size': 0.1,     # 单次仓位 10%
    'max_position': 0.3,      # 最大仓位 30%
}

# ==================== LSTM 参数 ====================
LSTM = {
    'seq_length': 20,         # 序列长度
    'epochs': 50,             # 训练轮数
    'hidden_size': 64,        # 隐藏层大小
    'dropout': 0.2,           # Dropout 比例
}

# ==================== 回测参数 ====================
BACKTEST = {
    'initial_cash': 1000000,  # 初始资金 100 万
    'commission': 0.001,      # 手续费 0.1%
}

# ==================== 数据参数 ====================
DATA = {
    'cache_dir': '/home/kyj/.openclaw/workspace/data',
    'predictions_dir': '/home/kyj/.openclaw/workspace/data/predictions',
    'validation_days': 5,     # 验证周期 5 个工作日
}

# ==================== 股票池 ====================
CORE_STOCKS = {
    'sh.601398': ('工商银行', '银行'),
    'sh.600036': ('招商银行', '银行'),
    'sh.601318': ('中国平安', '保险'),
    'sh.601857': ('中国石油', '能源'),
    'sh.600028': ('中国石化', '能源'),
    'sh.600519': ('贵州茅台', '白酒'),
    'sz.000858': ('五粮液', '白酒'),
    'sh.000002': ('万科 A', '地产'),
    'sh.600048': ('保利地产', '地产'),
    'sh.600104': ('上汽集团', '汽车'),
    'sh.600900': ('长江电力', '电力'),
    'sh.600276': ('恒瑞医药', '医药'),
    'sh.601668': ('中国建筑', '基建'),
    'sh.603986': ('兆易创新', '芯片'),
    'sh.600570': ('恒生电子', '软件'),
    'sz.002594': ('比亚迪', '新能源车'),
    'sz.300750': ('宁德时代', '电池'),
    'sh.601012': ('隆基绿能', '光伏'),
    'sz.002415': ('海康威视', '安防'),
}

# ==================== 辅助函数 ====================

def get_weight(name):
    """获取权重"""
    return WEIGHTS.get(name, 0)

def get_rsi_params():
    """获取 RSI 参数"""
    return RSI

def get_macd_params(market_regime='range'):
    """获取 MACD 参数"""
    return MACD.get(market_regime, MACD['range'])

def get_risk_params():
    """获取风控参数"""
    return RISK

def get_lstm_params():
    """获取 LSTM 参数"""
    return LSTM

# ==================== 验证配置 ====================
if __name__ == "__main__":
    print("DSS 配置验证")
    print("="*50)
    print(f"权重总和：{sum(WEIGHTS.values()):.2f}")
    print(f"RSI 周期：{RSI['period']}")
    print(f"MACD 趋势参数：{MACD['trend']}")
    print(f"MACD 震荡参数：{MACD['range']}")
    print(f"风控止损：{RISK['stop_loss']*100}%")
    print(f"风控止盈：{RISK['take_profit']*100}%")
    print(f"LSTM 序列长度：{LSTM['seq_length']}")
    print(f"股票池数量：{len(CORE_STOCKS)}")
