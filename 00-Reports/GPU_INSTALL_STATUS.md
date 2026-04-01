# GPU 安装状态报告

> **时间**: 2026-03-04 20:45  
> **GPU**: AMD RX6800 ✅ 已确认  
> **状态**: 🔄 安装中 (遇到网络问题)

---

## 📊 当前状态

### ✅ 已完成
- [x] GPU 直通确认 (RX6800 已在 VM 内)
- [x] amdgpu 驱动已加载
- [x] ROCm 仓库已添加

### 🔄 进行中
- [ ] ROCm 核心组件安装 (可能已完成)
- [ ] PyTorch ROCm 下载 (网络超时，需重试)

### ❌ 问题
- **PyTorch 下载超时**: `ReadTimeoutError: HTTPSConnectionPool(host='download.pytorch.org', port=443)`
- **原因**: 网络慢或服务器拥堵

---

## 🛠️ 解决方案

### 方案 1: 使用国内镜像 (推荐)

```bash
# SSH 到服务器
ssh root@106.53.186.90

# 使用清华镜像安装 PyTorch
pip3 install --break-system-packages \
  torch torchvision torchaudio \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 验证
python3 -c "import torch; print(torch.cuda.is_available())"
```

### 方案 2: 手动下载离线包

```bash
# 下载离线 wheel 包
wget https://download.pytorch.org/whl/rocm6.0/torch-2.2.0%2Brocm6.0-cp311-cp311-linux_x86_64.whl

# 本地安装
pip3 install torch-2.2.0+rocm6.0-cp311-cp311-linux_x86_64.whl
```

### 方案 3: 先用 CPU 版本

```bash
# 安装 CPU 版 (快速)
pip3 install --break-system-packages torch torchvision torchaudio

# 先用着，GPU 版本晚点再装
```

---

## 📈 预期性能

安装完成后：

| 操作 | CPU | RX6800 | 提升 |
|------|-----|--------|------|
| 向量化 | 25ms | 3ms | ↑8 倍 |
| 检索 | 19ms | 8ms | ↑2.4 倍 |
| 重排 | 40ms | 5ms | ↑8 倍 |

---

## 🚀 下一步

**推荐执行方案 1**（使用清华镜像）：

```bash
ssh root@106.53.186.90 "
pip3 install --break-system-packages \
  torch torchvision torchaudio \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple
"
```

**预计时间**: 5-10 分钟

---

*报告生成时间：2026-03-04 20:45*  
*下一步：使用国内镜像重新安装 PyTorch*
