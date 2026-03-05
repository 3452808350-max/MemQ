# AMD RX6800 GPU 手动安装指南

> **状态**: ⚠️ 自动安装失败，需要手动安装  
> **GPU**: AMD RX6800 (16GB)  
> **原因**: ROCm 安装需要特定系统配置

---

## 🔍 安装失败原因

ROCm 自动安装失败可能是因为：
1. Debian Bookworm 兼容性问题
2. 缺少内核头文件
3. Secure Boot 未禁用
4. 内核版本不兼容

---

## 📝 手动安装步骤

### 步骤 1: 系统准备

```bash
# SSH 登录 Debian Server
ssh root@106.53.186.90

# 更新系统
apt update && apt upgrade -y

# 安装内核头文件
apt install -y linux-headers-$(uname -r)

# 禁用 Secure Boot (如果需要)
# 重启进入 BIOS 禁用 Secure Boot
```

### 步骤 2: 添加 ROCm 仓库

```bash
# 添加 GPG 密钥
wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | apt-key add -

# 添加 ROCm 仓库 (Ubuntu 22.04 兼容)
echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/debian/ jammy main' > /etc/apt/sources.list.d/rocm.list

# 或者使用国内镜像
echo 'deb [arch=amd64] https://mirrors.tuna.tsinghua.edu.cn/rocm/apt/debian/ jammy main' > /etc/apt/sources.list.d/rocm.list

# 更新
apt update
```

### 步骤 3: 安装 ROCm

```bash
# 安装 ROCm 核心
apt install -y rocm-dkms rocm-opencl-runtime

# 安装开发工具
apt install -y rocblas hipblas-dev
```

### 步骤 4: 安装 PyTorch ROCm

```bash
# 安装 PyTorch (ROCm 6.0)
pip3 install --break-system-packages torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0
```

### 步骤 5: 验证安装

```bash
# 验证 ROCm
rocm-smi

# 验证 PyTorch
python3 -c "
import torch
print(f'GPU 可用：{torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'显存：{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB')
"
```

---

## 🚀 快速方案：使用 Docker

如果直接安装困难，可以使用 Docker：

```bash
# 安装 Docker
apt install -y docker.io docker-compose

# 运行 ROCm Docker
docker run --device=/dev/kfd --device=/dev/dri --group-add=video \
  -it pytorch/rocm pyt

# 在容器内验证
python3 -c "import torch; print(torch.cuda.is_available())"
```

---

## 💡 备选方案：使用 CPU 版本

如果 GPU 安装确实困难，可以先使用 CPU 版本：

```bash
# 安装 CPU 版 PyTorch
pip3 install --break-system-packages torch torchvision torchaudio

# 混合记忆架构仍然可以运行
# 性能：向量化 25ms/文本，检索 19ms P50
# 已经足够日常使用
```

---

## 📊 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| **GPU 直通** | ✅ 已完成 | RX6800 已直通到 VM |
| **ROCm 驱动** | ❌ 未安装 | 需要手动安装 |
| **PyTorch** | ❌ 未安装 | 等待 ROCm |
| **GPU 优化代码** | ✅ 已就绪 | gpu_optimized_memory.py |

---

## 🎯 建议

### 方案 A: 继续 GPU 安装 (推荐)

**优点**: 性能 ↑8 倍  
**缺点**: 安装复杂，可能需要调试  
**时间**: 30-60 分钟

### 方案 B: 先用 CPU，后升级

**优点**: 立即可用，稳定  
**缺点**: 性能较低 (但已足够)  
**时间**: 5 分钟安装

---

## 📞 需要帮助

如果需要帮助安装 ROCm，可以：

1. **检查系统日志**: `dmesg | grep -i amdgpu`
2. **检查内核兼容性**: `uname -r`
3. **查看 ROCm 支持列表**: https://rocm.docs.amd.com/

---

*创建时间：2026-03-04*  
*下一步：选择安装方案*
