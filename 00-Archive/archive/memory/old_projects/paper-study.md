# 📚 金融预测论文学习笔记 - 完整版

## 🔥 重要发现：stock-top-papers 资源库

**GitHub**: marcuswang6/stock-top-papers
- 收录KDD, WWW, AAAI, IJCAI, ACL, EMNLP等顶会论文
- 大部分附带代码实现
- 按年份和方法分类

---

## 一、Walk Forward验证 (优先级最高)

### 核心概念

**为什么传统交叉验证不行？**
```
金融数据特点：
- 非平稳（分布随时间变化）
- 时间依赖（不能打乱顺序）
- 未来数据泄露（用未来预测过去是作弊）

Walk Forward方法：
[训练] [验证] [测试]
   └─滚动─→ [训练] [验证] [测试]
```

### 实现步骤

```python
# 伪代码
def walk_forward_validation(data, train_size, step):
    results = []
    for i in range(0, len(data) - train_size, step):
        train = data[i:i+train_size]
        test = data[i+train_size:i+train_size+step]
        
        model = train_model(train)
        pred = model.predict(test)
        results.append((pred, test))
    
    return evaluate(results)
```

### 评估指标

| 指标 | 含义 |
|------|------|
| MSE/MAE | 预测误差 |
| Direction Accuracy | 涨跌方向准确率 |
| Sharpe Ratio | 风险调整收益 |
| Max Drawdown | 最大回撤 |

---

## 二、XGBoost金融预测 (第二优先)

### 论文：XGBoost Forecasting with Walk Forward Validation

**核心亮点**：
- Nepal股票市场 (NEPSE) 应用
- Walk Forward验证防止过拟合
- 特征：技术指标 + 基本面

### 特征工程

```python
# 常用金融特征
features = {
    # 技术指标
    'MA5': '5日均线',
    'MA20': '20日均线',
    'RSI': '相对强弱指数',
    'MACD': '异同移动平均线',
    'BB_upper': '布林带上轨',
    'BB_lower': '布林带下轨',
    
    # 波动率
    'volatility_5': '5日波动率',
    'volatility_20': '20日波动率',
    
    # 成交量
    'volume_MA5': '5日均量',
    'volume_ratio': '量比',
    
    # 基本面 (如果可得)
    'PE': '市盈率',
    'PB': '市净率',
}
```

### XGBoost参数调优

```python
params = {
    'objective': 'reg:squarederror',  # 或 'binary:logistic'
    'max_depth': 6,
    'learning_rate': 0.01,
    'n_estimators': 500,
    'min_child_weight': 3,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
}
```

---

## 三、KAN vs LSTM (第三优先)

### KAN (Kolmogorov-Arnold Networks)

**论文**: KAN vs LSTM Performance in Time Series Forecasting (2025)

**核心思想**：
- 源自Kolmogorov-Arnold表示定理
- 任何连续函数 = 一元函数叠加
- 2024年新架构，可解释性更强

### 对比

| 特性 | LSTM | KAN |
|------|------|-----|
| 长期依赖 | ✅ 优秀 | 待验证 |
| 可解释性 | ❌ 差 | ✅ 好 |
| 计算效率 | ✅ | ⚠️ 较慢 |
| 金融数据 | 成熟 | 新兴 |

### 金融适用性

**LSTM更适合**：
- 高频交易
- 短期预测
-已有成熟框架

**KAN可能更适合**：
- 解释性要求高的场景
- 因子挖掘
- 理论研究

---

## 四、2024-2025最新顶会论文

### KDD 2025
1. **Multi-period Learning** - 多周期学习
2. **MERA** - 专家混合 + 检索增强
3. **SAMBA** - Mamba + 图神经网络

### NeurIPS 2024
1. **m-Sparse Sharpe Ratio** - 投资组合优化
2. **ROIDICE** - 离线强化学习

### AAAI 2024
1. **MASTER** - 市场引导的Stock Transformer
2. **StockMixer** - 简单有效的MLP架构

### WWW 2024
1. **MERA** - 多样化股票模式建模
2. **FinReport** - 可解释收益预测

---

## 五、实用代码资源

| 仓库 | 描述 | 链接 |
|------|------|------|
| huseinzol05/Stock-Prediction-Models | 多种模型集合 | ⭐12k |
| lilianweng/stock-rnn | RNN/LSTM股票预测 | ⭐4k |
| Personae | 深度强化学习交易 | ⭐3k |
| DeepConvStock | CNN技术分析 | ⭐1k |
| FinGPT | 金融大语言模型 | ⭐8k |
| AlphaFin | 金融分析基准 | ⭐2k |

---

## 六、我们的DSS系统应用

### 短期目标（1-2周）
1. ✅ 论文学习框架建立
2. ⏳ 实现Walk Forward验证
3. ⏳ 集成XGBoost模型
4. ⏳ 对接真实数据回测

### 中期目标（1个月）
1. 添加LSTM/Transformer支持
2. 添加技术指标自动计算
3. 实现多模型对比
4. 添加回测报告生成

### 长期目标
1. 强化学习交易代理
2. 大语言模型基本面分析
3. 实时预测与预警

---

## 七、学习路径建议

### Week 1: 基础
- [x] 论文收集与筛选
- [ ] Walk Forward验证原理
- [ ] XGBoost金融应用

### Week 2: 实践
- [ ] 搭建基础预测框架
- [ ] 实现Walk Forward
- [ ] 真实数据回测

### Week 3-4: 进阶
- [ ] LSTM/Transformer
- [ ] 多模型对比
- [ ] 策略开发

---

*最后更新: 2026-02-17*
