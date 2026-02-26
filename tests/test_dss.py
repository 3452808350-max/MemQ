#!/usr/bin/env python3
"""DSS 单元测试"""
import sys
sys.path.insert(0, "/home/kyj/.openclaw/workspace")

def test_config():
    """测试配置模块"""
    from dss_config import WEIGHTS, RSI, MACD
    
    assert sum(WEIGHTS.values()) == 1.0, "权重总和不等于 1"
    assert RSI["period"] == 14
    assert "trend" in MACD
    assert "range" in MACD
    print("✓ 配置测试通过")

def test_adaptive_rsi():
    """测试自适应 RSI"""
    from dss_adaptive_indicators import adaptive_rsi
    import pandas as pd
    import numpy as np
    
    prices = pd.Series(np.random.randn(100).cumsum() + 100)
    rsi, info = adaptive_rsi(prices)
    
    assert len(rsi) == len(prices)
    assert info["period"] in [10, 14, 21]
    print("✓ 自适应 RSI 测试通过")

def test_ml_predict():
    """测试 ML 预测"""
    from dss_ml_predict import get_ml_score
    import pandas as pd
    import numpy as np
    
    df = pd.DataFrame({
        "close": np.random.randn(100).cumsum() + 100,
        "volume": np.random.randn(100).cumsum() + 1000
    })
    
    score, info = get_ml_score(df)
    assert -25 <= score <= 25
    assert "direction" in info
    print("✓ ML 预测测试通过")

if __name__ == "__main__":
    test_config()
    test_adaptive_rsi()
    test_ml_predict()
    print("
✅ 所有测试通过!")
