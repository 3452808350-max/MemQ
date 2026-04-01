# Denoiser - 金融时间序列去噪模块

独立的去噪工具库，为DSS等系统提供数据预处理接口。

## 安装依赖

```bash
# 基础依赖 (必需)
pip install PyWavelets numpy pandas

# 可选依赖
pip install PyEMD      # EMD方法
pip install vmdpy      # VMD方法
```

## 快速开始

```python
from denoiser import Denoiser

# 单信号去噪
denoiser = Denoiser(method='wavelet')
clean_signal = denoiser.denoise(noisy_signal)

# 返回分解成分
clean, components = denoiser.denoise(signal, return_components=True)

# 批量处理DataFrame
df_denoised = denoiser.denoise_batch(df, columns=['Close', 'Volume'])
```

## 支持的方法

| 方法 | 特点 | 适用场景 |
|------|------|----------|
| `wavelet` | 时频分解，保留突变点 | 通用，首选 |
| `kalman` | 实时性好，可预测 | 实时交易系统 |
| `ssa` | 无参数，保留趋势 | 稳健去噪 |
| `emd` | 自适应，无需预设 | 非平稳信号 |
| `vmd` | 模态分离清晰 | 多周期分析 |

## API

### Denoiser 类

```python
denoiser = Denoiser(method='wavelet', **params)
```

#### 参数
- `method`: 去噪方法 ('wavelet'|'kalman'|'ssa'|'emd'|'vmd')
- `**params`: 方法特定参数

#### 方法
- `denoise(signal, return_components=False)`: 单信号去噪
- `denoise_batch(df, columns=None)`: 批量处理
- `compare_methods(signal)`: 对比多个方法

### 静态方法
```python
Denoiser.evaluate(original, denoised)
# 返回: {'snr': ..., 'mse': ..., 'mae': ..., 'smoothness': ...}
```

## 方法参数

### wavelet
```python
Denoiser(method='wavelet', 
         wavelet='db4',      # 小波基
         level=None,         # 分解层数 (自动)
         threshold_mode='soft',  # 'soft'|'hard'
         threshold_rule='universal')  # 'universal'|'sure'|'minimax'
```

### kalman
```python
Denoiser(method='kalman',
         process_noise=0.01,      # Q: 过程噪声
         measurement_noise=1.0)   # R: 观测噪声
```

### ssa
```python
Denoiser(method='ssa',
         window_length=None,   # 窗口长度 (自动)
         n_components=None)    # 保留成分数 (自动)
```

### emd
```python
Denoiser(method='emd',
         n_imfs_remove=1,   # 去掉的IMF数量
         mode='partial')    # 'remove'|'partial'|'threshold'
```

### vmd
```python
Denoiser(method='vmd',
         n_modes=4,         # 模态数量
         alpha=2000,        # 带宽约束
         n_modes_remove=1)  # 去掉的模态数
```

## DSS 集成

```python
from denoiser.dss_integration import denoise_stock_data, detect_trend_clean

# 去噪价格数据
df_clean = denoise_stock_data(df, method='wavelet')

# 检测趋势
trend = detect_trend_clean(df, method='kalman')
print(trend['trend'])  # 'up'|'down'|'sideways'
```

## 测试

```bash
python denoiser/test_denoiser.py
```

## 项目结构

```
denoiser/
├── __init__.py
├── core.py           # Denoiser类
├── methods/
│   ├── wavelet.py    # 小波去噪
│   ├── emd.py        # EMD
│   ├── vmd.py        # VMD
│   ├── kalman.py     # 卡尔曼滤波
│   └── ssa.py        # 奇异谱分析
├── dss_integration.py # DSS集成示例
└── test_denoiser.py   # 测试脚本
```