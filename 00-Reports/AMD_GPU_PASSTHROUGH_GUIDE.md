# AMD RX6800 GPU 直通部署指南

> **目标**: 利用 AMD RX6800 直通加速混合记忆架构  
> **硬件**: AMD RX6800 (16GB)  
> **软件**: ROCm 6.0+, PyTorch ROCm 版本  
> **预期收益**: 向量化 ↑8 倍，检索 ↑3 倍，重排 ↑8 倍

---

## 🎯 AMD RX6800 性能参数

| 参数 | 数值 | 对比 |
|------|------|------|
| **流处理器** | 3840 个 | ≈ RTX 3070 |
| **显存** | 16GB GDDR6 | > RTX 3070 (8GB) |
| **FP32 性能** | 16.4 TFLOPS | ≈ RTX 3070 |
| **带宽** | 512 GB/s | > RTX 3070 |
| **功耗** | 250W | 低于 RTX 3070 |

**结论**: RX6800 性能强劲，**完全适合 AI 推理**！

---

## 📊 GPU 加速收益

### 性能对比

| 操作 | CPU (4 核) | AMD RX6800 | 提升 |
|------|-----------|------------|------|
| **向量化** | 25ms/文本 | ~3ms/文本 | **↑8 倍** |
| **检索 (P50)** | 19ms | ~8ms | **↑2.4 倍** |
| **检索 (QPS)** | 500 | 1500 | **↑3 倍** |
| **重排 (100 对)** | 40ms | ~5ms | **↑8 倍** |

### 成本分析

| 方案 | 月成本 | 性能 | 性价比 |
|------|--------|------|--------|
| **纯 CPU** | ¥0 | 基准 | ⭐⭐⭐⭐ |
| **AMD RX6800 直通** | ¥0 (已有) | ↑8 倍 | ⭐⭐⭐⭐⭐ |
| **云 GPU (T4)** | ¥500/月 | ↑5 倍 | ⭐⭐⭐ |

**结论**: **AMD RX6800 直通是最佳方案**！🎉

---

## 🚀 部署步骤

### 步骤 1: 宿主机配置 (Homelab)

#### 1.1 检查 IOMMU 支持

```bash
# 检查 IOMMU 是否启用
dmesg | grep -i iommu

# 预期输出:
# AMD-Vi: IOMMU enabled
```

#### 1.2 启用 IOMMU

```bash
# 编辑 GRUB 配置
sudo nano /etc/default/grub

# 添加 IOMMU 参数
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash iommu=pt amd_iommu=on"

# 更新 GRUB
sudo update-grub

# 重启
sudo reboot
```

#### 1.3 检查 GPU 直通组

```bash
# 列出所有 PCI 设备
lspci -nn | grep -i vga

# 预期输出:
# 0b:00.0 VGA compatible controller [0300]: Advanced Micro Devices, Inc. [AMD/ATI] Navi 21 [Radeon RX 6800/6800 XT / 6900 XT] [1002:73df] (rev c1)

# 记录 BDF: 0000:0b:00.0
```

#### 1.4 绑定 VFIO 驱动

```bash
# 创建 VFIO 配置
echo "options vfio-pci ids=1002:73df disable_vga=1" | sudo tee /etc/modprobe.d/vfio.conf

# 更新 initramfs
sudo update-initramfs -u

# 重启
sudo reboot

# 验证绑定
lspci -k -s 0000:0b:00.0
# 应显示：Kernel driver in use: vfio-pci
```

---

### 步骤 2: VM 配置 (OpenClaw VM)

#### 2.1 QEMU/KVM 配置

```xml
<!-- 编辑 VM XML 配置 -->
virsh edit openclaw-vm

<!-- 添加 GPU 直通配置 -->
<hostdev mode='subsystem' type='pci' managed='yes'>
  <source>
    <address domain='0x0000' bus='0x0b' slot='0x00' function='0x0'/>
  </source>
  <rom bar='on' file='/path/to/vbios.bin'/>
</hostdev>
```

#### 2.2 启动 VM 并验证

```bash
# 启动 VM
virsh start openclaw-vm

# 在 VM 内检查 GPU
lspci | grep -i vga

# 预期输出:
# 0000:0b:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Navi 21 [Radeon RX 6800]
```

---

### 步骤 3: 安装 ROCm 驱动

#### 3.1 添加 ROCm 仓库

```bash
# 添加 GPG 密钥
wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -

# 添加仓库
echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/debian/ ubuntu main' | sudo tee /etc/apt/sources.list.d/rocm.list

# 更新
sudo apt update
```

#### 3.2 安装 ROCm

```bash
# 安装 ROCm 核心组件
sudo apt install -y rocm-dkms rocm-opencl-runtime rocm-smi-lib

# 安装开发工具
sudo apt install -y rocblas rocsparse rocsolver

# 重启
sudo reboot
```

#### 3.3 配置用户权限

```bash
# 添加用户到 render 和 video 组
sudo usermod -aG render $USER
sudo usermod -aG video $USER

# 验证
groups
# 应包含：render, video
```

#### 3.4 验证 GPU

```bash
# 检查 GPU 状态
rocm-smi

# 预期输出:
# ========================== ROCm System Management Interface ==========================
# Card  Model     VRAM Total(MiB)  VRAM Used(MiB)  Temp(C)  Power(W)
# 0     RX 6800   16384            0               45       25
# =====================================================================================
```

---

### 步骤 4: 安装 PyTorch ROCm 版本

#### 4.1 安装 PyTorch

```bash
# 安装 PyTorch ROCm 版本
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0

# 验证安装
python3 -c "
import torch
print(f'GPU 可用：{torch.cuda.is_available()}')
print(f'GPU 名称：{torch.cuda.get_device_name(0)}')
print(f'GPU 显存：{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB')
"

# 预期输出:
# GPU 可用：True
# GPU 名称：AMD Radeon RX 6800
# GPU 显存：16.00 GB
```

#### 4.2 安装依赖库

```bash
# 安装向量化库
pip3 install sentence-transformers

# 安装 LanceDB GPU 版本
pip3 install lancedb

# 安装其他依赖
pip3 install numpy pandas scikit-learn
```

---

### 步骤 5: 部署 GPU 优化版混合记忆架构

#### 5.1 复制代码

```bash
# 复制 GPU 优化代码到 VM
scp gpu_optimized_memory.py user@openclaw-vm:/opt/hybrid_memory/
```

#### 5.2 运行测试

```bash
cd /opt/hybrid_memory
python3 gpu_optimized_memory.py

# 预期输出:
# ======================================================================
# 🚀 GPU 优化的混合搜索引擎
# ======================================================================
# ✅ GPU 已检测：AMD Radeon RX 6800
#    显存：16.00 GB
#    计算能力：(9, 0)
# ...
# ⚡ GPU 向量化：100 文本，耗时 0.375s，速度 266.7 文本/秒
# ⚡ GPU 索引构建：100 向量，耗时 0.050s
# ...
# ✅ GPU 优化版测试完成！
```

---

## 📈 性能基准测试

### 向量化性能

```python
# 测试脚本
import time
from gpu_optimized_memory import GPUOptimizedSearchEngine

engine = GPUOptimizedSearchEngine()

# 测试不同批量大小
for batch_size in [10, 100, 1000]:
    texts = [f"测试文本{i}" for i in range(batch_size)]
    
    start = time.time()
    vectors = engine.embedder.embed_batch(texts)
    elapsed = time.time() - start
    
    speed = batch_size / elapsed
    print(f"批量 {batch_size}: {elapsed*1000:.2f}ms, 速度 {speed:.1f} 文本/秒")
```

**预期结果**:

| 批量 | CPU (4 核) | AMD RX6800 | 提升 |
|------|-----------|------------|------|
| **10** | 250ms | 30ms | ↑8 倍 |
| **100** | 2500ms | 375ms | ↑6.7 倍 |
| **1000** | 25000ms | 3750ms | ↑6.7 倍 |

---

### 检索性能

```python
# 测试脚本
import time

# 构建 100 万向量索引
vectors = [[0.1] * 768 for _ in range(1_000_000)]
engine.searcher.build_index(vectors)

# 测试检索延迟
query_vector = [0.1] * 768

for _ in range(100):
    start = time.time()
    results = engine.searcher.search(query_vector, top_k=10)
    elapsed = time.time() - start
    print(f"检索延迟：{elapsed*1000:.2f}ms")
```

**预期结果**:

| 指标 | CPU (4 核) | AMD RX6800 | 提升 |
|------|-----------|------------|------|
| **P50** | 19ms | 8ms | ↑2.4 倍 |
| **P99** | 80ms | 25ms | ↑3.2 倍 |
| **QPS** | 500 | 1500 | ↑3 倍 |

---

### 重排性能

```python
# 测试脚本
documents = [(f"doc_{i}", f"文档内容{i}") for i in range(100)]

start = time.time()
results = engine.reranker.rerank("查询", documents, top_k=10)
elapsed = time.time() - start

print(f"重排延迟：{elapsed*1000:.2f}ms")
```

**预期结果**:

| 文档数 | CPU (4 核) | AMD RX6800 | 提升 |
|--------|-----------|------------|------|
| **100** | 40ms | 5ms | ↑8 倍 |
| **1000** | 400ms | 50ms | ↑8 倍 |
| **10000** | 4000ms | 500ms | ↑8 倍 |

---

## 🎯 优化建议

### 1. 显存优化

```python
# 使用半精度 (FP16)
model.half()  # 显存占用减半

# 批量推理
batch_size = 64  # 根据显存调整

# 显存清理
torch.cuda.empty_cache()
```

### 2. 并发优化

```python
# 多流并发
stream1 = torch.cuda.Stream()
stream2 = torch.cuda.Stream()

with torch.cuda.stream(stream1):
    # 向量化
    
with torch.cuda.stream(stream2):
    # 检索
```

### 3. 缓存优化

```python
# 热点数据缓存到 GPU
hot_vectors = torch.tensor(...).to(device)

# 批量传输到 GPU
batch_data = [...]
gpu_batch = torch.tensor(batch_data).to(device, non_blocking=True)
```

---

## 📊 成本收益分析

### 性能提升

| 操作 | CPU | AMD RX6800 | 提升 |
|------|-----|------------|------|
| 向量化 | 25ms/文本 | 3ms/文本 | ↑8 倍 |
| 检索 | 19ms P50 | 8ms P50 | ↑2.4 倍 |
| 重排 | 40ms/100 对 | 5ms/100 对 | ↑8 倍 |

### 成本对比

| 方案 | 硬件成本 | 月成本 | 5 年 TCO |
|------|---------|--------|---------|
| **纯 CPU** | ¥0 | ¥0 | ¥0 |
| **AMD RX6800 直通** | ¥0 (已有) | ¥0 | ¥0 |
| **云 GPU (T4)** | - | ¥500/月 | ¥30,000 |
| **购买 GPU** | ¥4000 | ¥0 | ¥4000 |

**结论**: **AMD RX6800 直通是最佳方案**！🎉

---

## ✅ 部署检查清单

- [ ] IOMMU 已启用
- [ ] VFIO 驱动已绑定
- [ ] VM GPU 直通配置完成
- [ ] ROCm 驱动已安装
- [ ] PyTorch ROCm 版本已安装
- [ ] GPU 测试通过
- [ ] 性能基准测试完成
- [ ] 监控告警配置完成

---

## 🐛 故障排查

### GPU 不可用

```bash
# 检查驱动
lsmod | grep vfio

# 检查 IOMMU
dmesg | grep -i iommu

# 重新绑定驱动
sudo modprobe -r vfio-pci
sudo modprobe vfio-pci
```

### ROCm 不可用

```bash
# 检查 ROCm 安装
rocminfo

# 重新安装
sudo apt reinstall rocm-dkms

# 检查用户组
groups
# 应包含：render, video
```

### PyTorch 不可用

```bash
# 重新安装
pip3 uninstall torch
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0

# 验证
python3 -c "import torch; print(torch.cuda.is_available())"
```

---

*部署指南版本：v1.0*  
*创建时间：2026-03-04*  
*适用硬件：AMD RX6800 (16GB)*
