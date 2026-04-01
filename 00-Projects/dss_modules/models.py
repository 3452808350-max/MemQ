"""模型模块"""
import numpy as np
import pandas as pd
from typing import Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# 尝试导入ML库
try:
    import lightgbm as lgb
    HAS_LGBM = True
except:
    HAS_LGBM = False

try:
    import xgboost as xgb
    HAS_XGB = True
except:
    HAS_XGB = False

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

class StockModel:
    """统一模型接口"""
    
    def __init__(self, model_type: str = 'lgbm'):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self._build_model()
    
    def _build_model(self):
        if self.model_type == 'lgbm' and HAS_LGBM:
            self.model = lgb.LGBMClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.05,
                num_leaves=31, random_state=42, verbose=-1
            )
        elif self.model_type == 'xgb' and HAS_XGB:
            self.model = xgb.XGBClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.05,
                random_state=42, use_label_encoder=False, eval_metric='logloss'
            )
        elif self.model_type == 'gb':
            self.model = GradientBoostingClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42
            )
        else:
            self.model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    
    def fit(self, X: np.ndarray, y: np.ndarray):
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)[:, 1]

class ProbabilityCalibrator:
    """概率校准"""
    
    def __init__(self):
        self.calibrator = LogisticRegression()
        self.fitted = False
    
    def fit(self, X: np.ndarray, y: np.ndarray):
        self.calibrator.fit(X, y)
        self.fitted = True
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        if not self.fitted:
            return X
        return self.calibrator.predict_proba(X)[:, 1]

def walk_forward_train(X: np.ndarray, y: np.ndarray, 
                       train_size: int = 70, val_size: int = 15, 
                       test_size: int = 15) -> Tuple[list, list]:
    """Walk Forward训练"""
    predictions, actuals = [], []
    n = len(X)
    
    for i in range(0, n - train_size - val_size - test_size + 1, test_size):
        train_end = i + train_size
        val_end = train_end + val_size
        test_end = min(val_end + test_size, n)
        
        X_train, y_train = X[i:train_end], y[i:train_end]
        X_test, y_test = X[val_end:test_end], y[val_end:test_end]
        
        if len(X_test) < 5:
            continue
        
        model = StockModel('lgbm')
        model.fit(X_train, y_train)
        
        pred = model.predict(X_test)
        predictions.extend(pred)
        actuals.extend(y_test)
    
    return predictions, actuals
