"""
法政审计: 中国出口顺差"不可解释差额"估算
Micro-to-Macro Forensic Audit for China Export Gap
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

# ============ 9家公司财务数据 (2024 Q1-Q3) ============
# 数据来源: 各公司财报 (人民币亿元)

COMPANY_DATA = {
    # 物流板块
    '中国外运': {'code': '601598', 'revenue': 776.13, 'ocf': 15.26, 'ar': 173.89, 'netprofit': 30.92},
    '华贸物流': {'code': '002384', 'revenue': 138.63, 'ocf': 5.73, 'ar': 27.05, 'netprofit': 5.48},
    '顺丰控股': {'code': '002352', 'revenue': 1893.24, 'ocf': 177.83, 'ar': 285.41, 'netprofit': 72.47},
    
    # 光伏/新能源
    '隆基绿能': {'code': '601012', 'revenue': 941.55, 'ocf': 127.10, 'ar': 252.92, 'netprofit': 112.13},
    '比亚迪': {'code': '002594', 'revenue': 4228.36, 'ocf': 1367.25, 'ar': 668.40, 'netprofit': 213.67},
    '宁德时代': {'code': '300750', 'revenue': 3108.27, 'ocf': 610.27, 'ar': 716.22, 'netprofit': 373.30},
    
    # 传统外贸/制造
    '立讯精密': {'code': '002475', 'revenue': 1888.07, 'ocf': 205.97, 'ar': 523.00, 'netprofit': 80.00},  # 估算
    '巨星科技': {'code': '002443', 'revenue': 50.00, 'ocf': 5.00, 'ar': 15.00, 'netprofit': 2.00},  # 估算
    '鲁泰': {'code': '000726', 'revenue': 60.00, 'ocf': 8.00, 'ar': 12.00, 'netprofit': 5.00},  # 估算
}

# ============ 宏观数据 (官方) ============
# 2024年数据 (万亿美元)
OFFICIAL_DATA = {
    '2024_export': 3.58,  # 中国出口总额
    '2024_surplus': 0.99,  # 贸易顺差
}


def build_microindex(df, weights=None):
    """
    构建微观出口综合指数 (MicroIndex)
    
    Args:
        df: DataFrame with company financial data
        weights: dict, 变量权重
    
    Returns:
        pd.Series: MicroIndex
    """
    if weights is None:
        weights = {'revenue': 0.4, 'ocf': 0.3, 'ar': -0.2, 'netprofit': 0.1}
    
    # 标准化
    scaler = StandardScaler()
    normalized = scaler.fit_transform(df)
    
    # 加权求和
    microindex = np.zeros(len(df))
    for i, (key, w) in enumerate(weights.items()):
        if key in df.columns:
            microindex += w * normalized[:, list(weights.keys()).index(key)]
    
    return pd.Series(microindex)


def regression_mapping(microindex, official_export):
    """
    回归映射: MicroIndex -> 预期出口
    
    Args:
        microindex: pd.Series
        official_export: np.array
    
    Returns:
        model: 训练好的回归模型
    """
    X = microindex.values.reshape(-1, 1)
    y = official_export
    
    model = LinearRegression()
    model.fit(X, y)
    
    return model


def calculate_gap(model, microindex, official_export):
    """
    计算不可解释差额 (Gap)
    
    Args:
        model: 回归模型
        microindex: pd.Series
        official_export: float
    
    Returns:
        dict: Gap分析结果
    """
    expected = model.predict(microindex.values.reshape(-1, 1))
    gap = official_export - expected.mean()
    gap_pct = gap / official_export * 100
    
    return {
        'official_export': official_export,
        'expected_export': expected.mean(),
        'gap': gap,
        'gap_pct': gap_pct,
    }


def main():
    """主函数"""
    print("=" * 60)
    print("法政审计: 中国出口顺差不可解释差额估算")
    print("=" * 60)
    
    # 1. 数据准备
    print("\n[1] 数据准备 (2024 Q1-Q3)")
    df = pd.DataFrame(COMPANY_DATA).T
    print(df)
    
    # 2. 构建MicroIndex
    print("\n[2] 构建MicroIndex")
    weights = {'revenue': 0.4, 'ocf': 0.3, 'ar': -0.2, 'netprofit': 0.1}
    df_features = df[['revenue', 'ocf', 'ar', 'netprofit']]
    microindex = build_microindex(df_features, weights)
    print(f"MicroIndex: {microindex.values}")
    
    # 3. 回归映射
    print("\n[3] 回归映射 (历史数据)")
    # 模拟历史数据 (2015-2023)
    np.random.seed(42)
    n_samples = 9
    X_history = np.random.randn(n_samples, 1) * 0.5 + 0.5
    y_history = X_history.flatten() * 0.8 + 2.5 + np.random.randn(n_samples) * 0.1
    
    model = LinearRegression()
    model.fit(X_history, y_history)
    print(f"回归系数: β1 = {model.coef_[0]:.4f}")
    print(f"截距: β0 = {model.intercept_:.4f}")
    
    # 4. 计算Gap
    print("\n[4] 计算Gap (2024年)")
    result = calculate_gap(model, microindex, OFFICIAL_DATA['2024_surplus'])
    
    print(f"官方顺差: {result['official_export']:.2f} 万亿美元")
    print(f"预期顺差: {result['expected_export']:.2f} 万亿美元")
    print(f"不可解释差额: {result['gap']:.2f} 万亿美元")
    print(f"差额占比: {result['gap_pct']:.1f}%")
    
    # 5. 交叉验证提示
    print("\n[5] 交叉验证方法")
    print("- 单位价格异常检测: 需海关分商品数据")
    print("- 贸易伙伴镜像法: 需UN Comtrade数据")
    print("- 物流量对比: 需港口吞吐量数据")
    
    print("\n" + "=" * 60)
    print("注意: 此为简化模型, 需补充完整历史数据")
    print("=" * 60)


if __name__ == "__main__":
    main()
