"""
上海证券交易所DSS模型训练示例代码
使用说明：
1. 确保已安装必要的库: pip install pandas numpy scikit-learn xgboost
2. 将本代码与数据文件放在同一目录下
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import classification_report, mean_squared_error, r2_score
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

# ==================== 1. 数据加载 ====================
def load_data():
    """加载DSS训练数据"""
    # 加载特征矩阵
    X = pd.read_csv('SSE_DSS特征矩阵.csv')

    # 加载目标变量
    y_binary = pd.read_csv('SSE_DSS目标_二分类.csv')
    y_trend = pd.read_csv('SSE_DSS目标_三分类.csv')
    y_regression = pd.read_csv('SSE_DSS目标_回归.csv')

    return X, y_binary, y_trend, y_regression

# ==================== 2. 特征选择 ====================
def select_features(X, feature_type='all'):
    """
    选择特征子集
    feature_type: 'all', 'core', 'lag', 'ratio', 'technical'
    """
    if feature_type == 'all':
        return X
    elif feature_type == 'core':
        # 核心特征
        cols = ['统计年份', '平均市盈率(A股)', '上证综合指数(收盘)', 
                '股票成交金额(亿元)', '投资者户数(万户)']
        return X[cols]
    elif feature_type == 'lag':
        # 滞后特征
        cols = [c for c in X.columns if '_lag' in c or c in ['统计年份']]
        return X[cols]
    elif feature_type == 'technical':
        # 技术指标
        cols = ['统计年份', '平均市盈率(A股)', '上证综合指数(收盘)',
                '上证综合指数(收盘)_MA3', '指数波动率', '市盈率历史分位']
        return X[cols]
    else:
        return X

# ==================== 3. 模型训练 ====================
def train_classification_model(X, y, model_type='rf'):
    """
    训练分类模型
    model_type: 'rf'(随机森林), 'xgb'(XGBoost), 'lr'(逻辑回归)
    """
    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X.drop('统计年份', axis=1))

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.3, random_state=42, stratify=y
    )

    # 选择模型
    if model_type == 'rf':
        model = RandomForestClassifier(n_estimators=100, random_state=42)
    elif model_type == 'xgb':
        model = xgb.XGBClassifier(n_estimators=100, random_state=42)
    elif model_type == 'lr':
        model = LogisticRegression(random_state=42)

    # 训练
    model.fit(X_train, y_train)

    # 预测
    y_pred = model.predict(X_test)

    # 评估
    print(f"\n=== {model_type.upper()} 分类结果 ===")
    print(classification_report(y_test, y_pred))

    # 交叉验证
    cv_scores = cross_val_score(model, X_scaled, y, cv=5)
    print(f"交叉验证准确率: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")

    return model, scaler

def train_regression_model(X, y, model_type='rf'):
    """
    训练回归模型
    model_type: 'rf'(随机森林), 'xgb'(XGBoost), 'lr'(线性回归)
    """
    # 数据标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X.drop('统计年份', axis=1))

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.3, random_state=42
    )

    # 选择模型
    if model_type == 'rf':
        model = RandomForestRegressor(n_estimators=100, random_state=42)
    elif model_type == 'xgb':
        model = xgb.XGBRegressor(n_estimators=100, random_state=42)
    elif model_type == 'lr':
        model = LinearRegression()

    # 训练
    model.fit(X_train, y_train)

    # 预测
    y_pred = model.predict(X_test)

    # 评估
    print(f"\n=== {model_type.upper()} 回归结果 ===")
    print(f"MSE: {mean_squared_error(y_test, y_pred):.3f}")
    print(f"R²: {r2_score(y_test, y_pred):.3f}")

    return model, scaler

# ==================== 4. 特征重要性 ====================
def get_feature_importance(model, feature_names):
    """获取特征重要性"""
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importance = np.abs(model.coef_)
    else:
        return None

    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)

    return importance_df

# ==================== 5. 预测示例 ====================
def predict_next_year(model, scaler, current_year_data):
    """预测下一年市场走势"""
    current_scaled = scaler.transform(current_year_data)
    prediction = model.predict(current_scaled)
    probability = model.predict_proba(current_scaled) if hasattr(model, 'predict_proba') else None
    return prediction, probability

# ==================== 主程序 ====================
if __name__ == '__main__':
    # 加载数据
    X, y_binary, y_trend, y_regression = load_data()

    print("数据加载完成")
    print(f"特征矩阵形状: {X.shape}")
    print(f"样本数: {len(y_binary)}")

    # 选择特征
    X_selected = select_features(X, 'core')
    print(f"\n选择特征数: {X_selected.shape[1]}")

    # 训练二分类模型（涨跌预测）
    print("\n" + "="*50)
    print("二分类模型：预测下年涨跌")
    print("="*50)
    model_clf, scaler_clf = train_classification_model(X_selected, y_binary, 'rf')

    # 训练回归模型（涨跌幅预测）
    print("\n" + "="*50)
    print("回归模型：预测下年涨跌幅")
    print("="*50)
    model_reg, scaler_reg = train_regression_model(X_selected, y_regression, 'rf')

    # 特征重要性
    print("\n" + "="*50)
    print("特征重要性（Top 10）")
    print("="*50)
    feature_names = X_selected.drop('统计年份', axis=1).columns
    importance_df = get_feature_importance(model_clf, feature_names)
    print(importance_df.head(10))

    print("\n训练完成！")
