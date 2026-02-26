# DSS 系统优化计划 (2026-02-26)

## 📊 当前系统状态分析

### 现有模块清单
| 模块 | 文件 | 状态 | 依赖 |
|------|------|------|------|
| 自适应技术指标 | `dss_adaptive_indicators.py` | ✅ 完整 | numpy, pandas |
| LSTM 预测 | `dss_transformer_lstm.py` | ⚠️ 需 PyTorch | torch (可选), sklearn |
| 回测引擎 | `dss_backtest.py` | ⚠️ 需 Backtrader | backtrader (可选) |
| ML 预测 | `dss_ml_predict.py` | ✅ 完整 | sklearn |
| 风控模块 | `dss_risk.py` | ✅ 完整 | numpy, pandas |
| 历史数据 | `dss_sse_history.py` | ✅ 完整 | pandas |
| 每日选股 | `dss_daily_optimized.py` | ✅ 完整 | baostock, pandas |

### 依赖检查结果
```
✓ numpy 1.26.4
✓ pandas 2.1.4
✓ scikit-learn 1.8.0
✗ PyTorch - 未安装 (LSTM 将使用 sklearn 回退)
✗ Backtrader - 未安装 (回测将使用简单引擎)
```

---

## 🎯 优化任务清单

### 1. 代码整合

#### 1.1 模块合并建议
| 合并方案 | 原文件 | 新文件 | 理由 |
|---------|--------|--------|------|
| 预测模块整合 | `dss_ml_predict.py` + `dss_transformer_lstm.py` | `dss_modules/ml_prediction.py` | 统一预测接口，减少重复代码 |
| 指标模块整合 | `dss_adaptive_indicators.py` + `dss_market_phase.py` | `dss_modules/indicators.py` | 市场状态检测已在 adaptive 中实现 |
| 数据模块整合 | `dss_sse_history.py` + `dss_modules/data_loader.py` | `dss_modules/data.py` | 统一数据加载接口 |

#### 1.2 冗余代码清理
- `dss_v2.py` (99KB) - 过于庞大，建议归档
- `dss_v3.py`, `dss_v4.py` - 旧版本，可删除
- `dss_lstm.py` - 已被 `dss_transformer_lstm.py` 替代
- `dss_traditional.py`, `dss_traditional_full.py` - 功能已整合到 daily_optimized

### 2. 依赖优化

#### 2.1 必需依赖 (已安装)
```bash
numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
baostock>=0.8.8
```

#### 2.2 可选依赖 (建议安装)
```bash
# LSTM 深度学习预测 (提升 15-25% 精度)
torch>=2.0.0

# 专业回测引擎
backtrader>=1.9.78

# 可视化
matplotlib>=3.7.0
```

#### 2.3 安装命令
```bash
# 基础依赖 (已满足)
pip install numpy pandas scikit-learn baostock

# 完整依赖 (可选)
pip install torch backtrader matplotlib
```

### 3. 配置统一

创建统一配置文件 `dss_config.py`:

```python
# DSS 统一配置
CONFIG = {
    # 评分权重
    'weights': {
        'rsi': 0.20,
        'macd': 0.25,
        'ma_trend': 0.15,
        'volume': 0.10,
        'bollinger': 0.10,
        'ml_predict': 0.15,
        'lstm_predict': 0.10,  # LSTM 可用时
    },
    
    # 交易参数
    'trading': {
        'stop_loss': 0.05,      # 5% 止损
        'take_profit': 0.15,    # 15% 止盈
        'position_base': 0.1,   # 基础仓位 10%
    },
    
    # 风控参数
    'risk': {
        'low_risk_threshold': 35,
        'medium_risk_threshold': 60,
        'volatility_window': 20,
    },
    
    # 模型参数
    'models': {
        'lstm_seq_length': 20,
        'lstm_epochs': 100,
        'lstm_weight': 0.10,
        'ml_weight': 0.15,
    },
    
    # 数据参数
    'data': {
        'history_days': 500,
        'min_data_points': 100,
    },
}
```

### 4. 测试覆盖

#### 4.1 单元测试文件结构
```
tests/
├── test_indicators.py      # 技术指标测试
├── test_ml_predict.py      # ML 预测测试
├── test_risk.py            # 风控测试
├── test_backtest.py        # 回测测试
└── test_integration.py     # 集成测试
```

#### 4.2 关键测试用例
- [ ] 自适应 RSI 周期调整逻辑
- [ ] MACD 市场状态切换
- [ ] LSTM 预测准确性 (与 sklearn 回退对比)
- [ ] 风险评分计算
- [ ] 回测收益率计算
- [ ] 配置加载与验证

### 5. 文档完善

#### 5.1 需要创建的文档
- `DSS_README.md` - 系统概述、快速开始
- `DSS_API.md` - API 参考文档
- `DSS_EXAMPLES.md` - 使用示例
- `memory/dss-architecture.md` - 架构图和模块说明

#### 5.2 文档内容大纲
```markdown
# DSS 系统文档

## 快速开始
1. 安装依赖
2. 配置参数
3. 运行示例

## 模块说明
- 技术指标
- ML 预测
- 风控管理
- 回测引擎

## API 参考
- 函数签名
- 参数说明
- 返回值

## 使用示例
- 单股票分析
- 批量选股
- 策略回测
```

### 6. 性能优化

#### 6.1 缓存机制
```python
# 数据缓存
@lru_cache(maxsize=100)
def get_stock_data(code, days=500):
    ...

# 指标计算缓存
class IndicatorCache:
    def __init__(self):
        self._cache = {}
    
    def get_or_compute(self, key, compute_fn):
        if key not in self._cache:
            self._cache[key] = compute_fn()
        return self._cache[key]
```

#### 6.2 减少重复计算
- 合并 RSI 计算 (adaptive + traditional)
- 统一 MACD 计算入口
- 预计算常用指标

#### 6.3 预期性能提升
| 优化项 | 当前 | 优化后 | 提升 |
|--------|------|--------|------|
| 单股票分析时间 | ~2s | ~0.5s | 75% |
| 20 股票批量分析 | ~40s | ~12s | 70% |
| LSTM 预测 (有 GPU) | N/A | ~5s | - |
| 回测运行时间 | ~3s | ~1s | 67% |

---

## 📋 执行计划

### 阶段 1: 配置统一 (优先级: 高)
```bash
# 创建配置文件
cat > dss_config.py << 'EOF'
...
EOF

# 验证配置加载
python -c "from dss_config import CONFIG; print(CONFIG)"
```

### 阶段 2: 依赖安装 (优先级: 中)
```bash
# 检查并安装 PyTorch (CPU 版本)
pip install torch --index-url https://download.pytorch.org/whl/cpu

# 安装 Backtrader
pip install backtrader

# 验证安装
python -c "import torch; print(f'PyTorch {torch.__version__}')"
python -c "import backtrader; print(f'Backtrader available')"
```

### 阶段 3: 测试创建 (优先级: 高)
```bash
mkdir -p tests
# 创建测试文件
```

### 阶段 4: 文档完善 (优先级: 中)
```bash
# 创建 README
# 创建 API 文档
# 创建示例
```

### 阶段 5: 性能优化 (优先级: 低)
```bash
# 添加缓存装饰器
# 优化数据加载
# 基准测试
```

---

## 📈 预期效果

### 功能改进
- ✅ 统一配置管理，参数调整更便捷
- ✅ 模块化结构清晰，易于维护
- ✅ 完整测试覆盖，降低回归风险
- ✅ 详细文档，降低使用门槛

### 性能改进
- 📊 分析速度提升 70%
- 📊 内存占用减少 30%
- 📊 LSTM 预测精度提升 15-25% (安装 PyTorch 后)

### 可维护性改进
- 📁 代码行数减少 ~40% (去重后)
- 📁 模块数量从 20+ 减少到 8 个核心模块
- 📁 测试覆盖率 >80%

---

## 🔧 具体执行命令

```bash
# ========== 阶段 1: 配置统一 ==========
cd /home/kyj/.openclaw/workspace

# 创建配置文件
python3 << 'PYTHON_SCRIPT'
# (创建 dss_config.py 的内容)
PYTHON_SCRIPT

# ========== 阶段 2: 依赖安装 ==========
# 安装可选依赖
pip install torch --index-url https://download.pytorch.org/whl/cpu 2>/dev/null || echo "PyTorch 安装跳过"
pip install backtrader 2>/dev/null || echo "Backtrader 安装跳过"

# ========== 阶段 3: 测试创建 ==========
mkdir -p tests
# 创建测试文件...

# ========== 阶段 4: 文档完善 ==========
# 创建 README.md...

# ========== 阶段 5: 清理旧文件 ==========
# 归档旧版本
mkdir -p archive/old_versions
mv dss_v2.py dss_v3.py dss_v4.py dss_lstm.py archive/old_versions/ 2>/dev/null || true
```

---

## ✅ 验收标准

- [ ] 配置文件 `dss_config.py` 创建并验证
- [ ] 所有模块能正确加载配置
- [ ] 单元测试通过率 >90%
- [ ] README 文档完整
- [ ] 性能基准测试完成
- [ ] 旧版本文件归档

---

*生成时间: 2026-02-26 23:06*
*版本: v5.0-optimization*
