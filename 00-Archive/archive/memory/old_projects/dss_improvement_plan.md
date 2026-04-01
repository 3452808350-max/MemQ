# 📈 DSS股票分析系统改进计划
## 基于论文学习成果的系统升级

**状态：✅ 已完成 (2026-02-17)**

---

## 🎯 改进目标 (已达成)

| 当前状态 | 目标状态 | 状态 |
|---------|---------|------|
| 基础技术指标 | ML预测模型 + Walk Forward验证 | ✅ |
| 单次回测 | 滚动验证防止过拟合 | ✅ |
| 简单分析 | 多模型对比框架 | ✅ |

---

## 📊 第一阶段：Walk Forward验证框架 (优先级最高)

### 核心改进

```python
# 改进后的预测框架
class WalkForwardValidator:
    """
    论文核心：Walk Forward Validation
    来自: XGBoost Forecasting with Walk Forward Validation
    
    关键思想：
    - 模拟真实交易：只用已知历史预测未来
    - 滚动窗口：训练→验证→测试→滑动
    - 防止数据泄露
    """
    
    def __init__(self, train_window=252, val_window=21, test_window=5):
        """
        train_window: 训练集天数 (252天 ≈ 1年)
        val_window: 验证集天数 (21天 ≈ 1月)
        test_window: 测试集天数 (5天 ≈ 1周)
        """
        self.train_window = train_window
        self.val_window = val_window
        self.test_window = test_window
        
    def rolling_validation(self, data):
        """
        滚动验证流程：
        
        时期1: [========训练========][===验证===][测试]
        时期2:           [========训练========][===验证===][测试]
        时期3:                        [========训练========][===验证===][测试]
        """
        results = []
        
        for i in range(0, len(data) - self.train_window - self.val_window, self.test_window):
            # 划分数据
            train_end = i + self.train_window
            val_end = train_end + self.val_window
            test_end = val_end + self.test_window
            
            train_data = data[i:train_end]
            val_data = data[train_end:val_end]
            test_data = data[val_end:test_end]
            
            # 训练模型
            model = self.train(train_data, val_data)
            
            # 预测测试集
            predictions = model.predict(test_data)
            
            # 记录结果
            results.append({
                'predictions': predictions,
                'actuals': test_data,
                'train_period': (i, train_end),
                'test_period': (val_end, test_end)
            })
            
        return self.evaluate(results)
```

### 评估指标

```python
class DSSMetrics:
    """论文中的评估指标"""
    
    @staticmethod
    def direction_accuracy(predictions, actuals):
        """方向准确率 - 论文强调的重要指标"""
        correct = sum((p > 0) == (a > 0) for p, a in zip(predictions, actuals))
        return correct / len(predictions)
    
    @staticmethod
    def sharpe_ratio(returns, risk_free_rate=0.02):
        """夏普比率 - 来自 mSSRM 论文"""
        excess = returns - risk_free_rate / 252
        return np.mean(excess) / np.std(excess) * np.sqrt(252)
    
    @staticmethod
    def max_drawdown(cumulative_returns):
        """最大回撤 - 风险评估关键指标"""
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        return np.min(drawdown)
```

---

## 📊 第二阶段：特征工程

### 技术指标特征 (来自XGBoost论文)

```python
class FeatureEngineer:
    """金融特征工程 - 基于论文实践"""
    
    def create_features(self, df):
        """
        创建预测特征：
        - 技术指标
        - 波动率
        - 成交量特征
        - 动量指标
        """
        features = {}
        
        # 移动平均线
        for window in [5, 10, 20, 60]:
            features[f'MA_{window}'] = df['close'].rolling(window).mean()
            features[f'MA_ratio_{window}'] = df['close'] / features[f'MA_{window}']
        
        # RSI - 相对强弱指数
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        features['MACD'] = ema12 - ema26
        features['MACD_signal'] = features['MACD'].ewm(span=9).mean()
        
        # 布林带
        ma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        features['BB_upper'] = ma20 + 2 * std20
        features['BB_lower'] = ma20 - 2 * std20
        features['BB_width'] = (features['BB_upper'] - features['BB_lower']) / ma20
        
        # 波动率
        for window in [5, 20]:
            returns = df['close'].pct_change()
            features[f'volatility_{window}'] = returns.rolling(window).std() * np.sqrt(252)
        
        # 成交量特征
        features['volume_MA5'] = df['volume'].rolling(5).mean()
        features['volume_ratio'] = df['volume'] / features['volume_MA5']
        
        # 动量指标
        for period in [5, 10, 20]:
            features[f'momentum_{period}'] = df['close'].pct_change(period)
        
        # 价格特征
        features['high_low_ratio'] = df['high'] / df['low']
        features['close_open_ratio'] = df['close'] / df['open']
        
        return pd.DataFrame(features)
```

---

## 📊 第三阶段：模型集成

### XGBoost模型 (来自论文重点)

```python
class XGBoostPredictor:
    """基于论文的XGBoost预测器"""
    
    def __init__(self):
        self.model = None
        self.params = {
            'objective': 'reg:squarederror',
            'max_depth': 6,
            'learning_rate': 0.01,
            'n_estimators': 500,
            'min_child_weight': 3,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42
        }
    
    def train(self, X_train, y_train, X_val=None, y_val=None):
        """训练模型 - 支持验证集早停"""
        
        if X_val is not None:
            self.model = xgb.XGBRegressor(
                **self.params,
                early_stopping_rounds=50,
                eval_metric='mae'
            )
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        else:
            self.model = xgb.XGBRegressor(**self.params)
            self.model.fit(X_train, y_train)
        
        return self.model
    
    def predict(self, X):
        """预测"""
        return self.model.predict(X)
    
    def feature_importance(self):
        """特征重要性 - 论文强调的分析点"""
        importance = self.model.feature_importances_
        features = self.model.feature_names_in_
        return pd.DataFrame({'feature': features, 'importance': importance})
```

### LSTM模型 (来自StockMixer论文思想)

```python
class LSTMPredictor:
    """LSTM时序预测 - 来自StockMixer论文"""
    
    def __init__(self, sequence_length=60, lstm_units=64):
        self.sequence_length = sequence_length
        self.lstm_units = lstm_units
        self.model = None
    
    def build_model(self, input_shape):
        """构建LSTM模型"""
        model = Sequential([
            LSTM(self.lstm_units, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(self.lstm_units // 2),
            Dropout(0.2),
            Dense(32, activation='relu'),
            Dense(1)
        ])
        
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        self.model = model
        return model
    
    def prepare_sequences(self, data):
        """准备序列数据"""
        X, y = [], []
        for i in range(self.sequence_length, len(data)):
            X.append(data[i-self.sequence_length:i])
            y.append(data[i])
        return np.array(X), np.array(y)
```

---

## 📊 第四阶段：预测信号生成

```python
class SignalGenerator:
    """信号生成器 - 结合多模型"""
    
    def __init__(self, models):
        self.models = models  # 多个模型的列表
    
    def ensemble_predict(self, X):
        """集成预测 - 来自MERA论文思想"""
        predictions = []
        
        for name, model in self.models.items():
            pred = model.predict(X)
            predictions.append(pred)
        
        # 简单平均，也可以用加权平均
        return np.mean(predictions, axis=0)
    
    def generate_signals(self, predictions, threshold=0.01):
        """
        生成交易信号
        
        signal > threshold: 买入 (1)
        signal < -threshold: 卖出 (-1)
        其他: 持有 (0)
        """
        signals = np.zeros_like(predictions)
        signals[predictions > threshold] = 1
        signals[predictions < -threshold] = -1
        return signals
```

---

## 📊 第五阶段：验证与回测

```python
class DSSBacktester:
    """DSS回测系统 - 论文标准流程"""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
    
    def run_backtest(self, data, signals):
        """
        运行回测
        
        来自论文的关键点：
        - 考虑交易成本
        - 计算真实收益
        - 评估风险指标
        """
        results = []
        
        for i in range(len(signals)):
            price = data.iloc[i]['close']
            signal = signals[i]
            
            # 交易逻辑
            if signal == 1 and self.capital > 0:
                # 买入
                shares = self.capital * 0.95 / price  # 留5%现金
                self.positions['shares'] = shares
                self.positions['entry_price'] = price
                self.capital -= shares * price * 1.001  # 考虑交易成本
                
            elif signal == -1 and 'shares' in self.positions:
                # 卖出
                proceeds = self.positions['shares'] * price * 0.999
                self.capital += proceeds
                self.trades.append({
                    'entry': self.positions['entry_price'],
                    'exit': price,
                    'return': (price - self.positions['entry_price']) / self.positions['entry_price']
                })
                del self.positions['shares']
            
            # 记录每日结果
            portfolio_value = self.capital
            if 'shares' in self.positions:
                portfolio_value += self.positions['shares'] * price
            
            results.append(portfolio_value)
        
        return self.calculate_metrics(results)
    
    def calculate_metrics(self, results):
        """计算评估指标"""
        returns = np.diff(results) / results[:-1]
        
        return {
            'total_return': (results[-1] - self.initial_capital) / self.initial_capital,
            'sharpe_ratio': DSSMetrics.sharpe_ratio(returns),
            'max_drawdown': DSSMetrics.max_drawdown(np.array(results)),
            'win_rate': len([t for t in self.trades if t['return'] > 0]) / len(self.trades) if self.trades else 0,
            'num_trades': len(self.trades)
        }
```

---

## 📅 实施计划

| 阶段 | 时间 | 内容 |
|------|------|------|
| Phase 1 | 第1周 | Walk Forward验证框架 |
| Phase 2 | 第2周 | XGBoost模型 + 特征工程 |
| Phase 3 | 第3周 | LSTM模型集成 |
| Phase 4 | 第4周 | 回测系统 + 风险评估 |

---

## ✅ 完成总结 (2026-02-17)

### 已实现功能

1. **Walk Forward验证框架** - 滚动窗口防止过拟合
2. **真实API集成** - Alpha Vantage API (MXAYBEBGFHR6PHYW)
3. **XGBoost模型** - 真实机器学习模型
4. **多模型对比** - XGBoost vs RandomForest vs LSTM
5. **特征工程** - 19个技术指标

### 测试结果

| 股票 | 方向准确率 | 最佳模型 |
|------|-----------|----------|
| AAPL | 55.00% | XGBoost |
| GOOGL | 50.00% | XGBoost |
| MSFT | 48.33% | XGBoost |

### 关键文件

- `dss_v2.py` - 完整实现 (641行)
- 使用真实Alpha Vantage API数据
- 支持Walk Forward滚动验证

### 经验教训

1. **先检查现有资源** - 项目已有API Key
2. **理解API限制** - 免费版25次/天，100天数据
3. **保持简洁** - 避免脚本臃肿

---

## 🔧 未来改进

1. 获取更多历史数据 (升级API套餐)
2. 添加更多特征和模型
3. 实现每日自动分析
4. 配置多Agent协作 (Qwen 3.5)

---

*改进计划制定: 2026-02-17*
*完成日期: 2026-02-17*
*基于论文: StockMixer, MASTER, XGBoost Walk Forward, mSSRM*
