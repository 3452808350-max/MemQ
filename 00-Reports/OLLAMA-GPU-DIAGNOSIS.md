# 🔍 Ollama GPU 问题诊断报告

**时间**: 2026-03-17 15:58  
**问题**: Ollama 使用 CPU 而非 GPU 运行模型

---

## 📊 当前状态

### 硬件检测

| 组件 | 状态 | 说明 |
|------|------|------|
| **GPU 1** | ✅ Virtio 虚拟 GPU | 虚拟机显卡，不支持计算 |
| **GPU 2** | ✅ AMD RX 6800/6900 | 独立显卡，应支持 ROCm |
| **amdgpu 驱动** | ✅ 已加载 | 内核模块正常 |
| **ROCm** | ❌ 未检测到 | Ollama 无法使用 AMD GPU |

### Ollama 状态

```
NAME                                                 ID              SIZE      PROCESSOR    CONTEXT
modelscope.cn/Qwen/Qwen3-Embedding-4B-GGUF:latest    839c975f400b    3.7 GB    100% CPU     4096
```

**问题**: 显示 `100% CPU` 而非 `AMD`

---

## 🚨 问题原因

### 1. ROCm 未安装或未配置

**Ollama 需要 ROCm** 来支持 AMD GPU：
- ROCm = Radeon Open Compute Platform
- 类似 NVIDIA CUDA 的 AMD 版本
- Ubuntu 需要手动安装

### 2. Ollama 版本问题

**检查 Ollama 是否支持 ROCm**:
```bash
ollama --version
# 某些版本需要特殊构建才能支持 AMD
```

### 3. 用户权限问题

**视频用户组权限**:
```bash
groups $USER
# 需要包含 'video' 或 'render'
```

### 4. Docker 容器限制

**如果在 Docker 中运行 Ollama**:
- 需要传递 GPU 设备
- 需要 ROCm 兼容的镜像

---

## ✅ 解决方案

### 方案 A: 安装 ROCm（推荐）

**步骤**:

```bash
# 1. 添加 ROCm 仓库
wget https://repo.radeon.com/amdgpu-install/6.0.2/ubuntu/noble/amdgpu-install_6.0.60002-1_all.deb
sudo apt install ./amdgpu-install_6.0.60002-1_all.deb

# 2. 安装 ROCm
sudo amdgpu-install --usecase=rocm --no-dkms

# 3. 添加用户到渲染组
sudo usermod -aG render $USER
sudo usermod -aG video $USER

# 4. 重启
sudo reboot

# 5. 验证
rocm-smi
ollama ps  # 应该显示 AMD 而非 CPU
```

**注意**: 
- ROCm 安装复杂，可能需要 30+ 分钟
- 需要重启系统
- 某些 AMD 显卡不支持 ROCm

### 方案 B: 使用 NVIDIA GPU（如果有）

如果有 NVIDIA 显卡：
```bash
# 安装 NVIDIA 驱动 + CUDA
sudo apt install nvidia-driver-550 nvidia-cuda-toolkit

# 重启后 Ollama 会自动检测
```

### 方案 C: 接受 CPU 运行（临时）

如果不想安装 ROCm：
```bash
# 等待模型自动卸载（4 分钟）
# 或手动卸载
curl http://localhost:11434/api/generate -d '{
  "model": "modelscope.cn/Qwen/Qwen3-Embedding-4B-GGUF",
  "keep_alive": 0
}'
```

### 方案 D: 使用云 GPU 服务

**远程 Ollama 服务**:
```bash
# 使用远程 GPU 服务器
export OLLAMA_HOST=https://gpu-server:11434
```

---

## 🔧 验证步骤

### 1. 检查 ROCm 是否安装

```bash
rocm-smi
# 或
rocminfo
```

### 2. 检查 Ollama GPU 检测

```bash
# 重启 Ollama
sudo systemctl restart ollama

# 查看日志
journalctl -u ollama -f | grep -i gpu
```

### 3. 测试 GPU 推理

```bash
# 运行小模型
ollama run qwen2.5:0.5b "hi"

# 检查处理器
ollama ps
# 应该显示 AMD 或 CUDA 而非 CPU
```

---

## 📈 性能对比

| 场景 | CPU | GPU (预期) |
|------|-----|-----------|
| Qwen3-Embedding-4B | 727% CPU | ~50% GPU |
| 内存占用 | 3.7GB | 3.7GB VRAM |
| 推理速度 | 慢 | 5-10x 快 |
| 系统响应 | 卡顿 | 流畅 |

---

## 🎯 建议

### 短期（现在）

1. **等待模型自动卸载** - 4 分钟后 CPU 会降下来
2. **或手动卸载** - 立即释放 CPU

### 中期（本周）

1. **评估是否需要 GPU 加速**
   - 如果经常用 Ollama → 安装 ROCm
   - 如果偶尔用 → 接受 CPU 运行

2. **考虑替代方案**
   - 使用远程 GPU 服务
   - 使用 Kimi Remote API（已有）

### 长期（可选）

1. **升级硬件** - NVIDIA GPU（更好的 Ollama 支持）
2. **云服务** - 按需使用 GPU

---

## 📝 快速命令

```bash
# 检查 GPU 状态
lspci | grep -i vga

# 检查 ROCm
rocm-smi 2>&1 || echo "ROCm 未安装"

# 检查 Ollama 处理器
ollama ps

# 手动卸载模型（释放 CPU）
curl http://localhost:11434/api/generate -d '{"model": "modelscope.cn/Qwen/Qwen3-Embedding-4B-GGUF", "keep_alive": 0}'

# 再次检查 CPU
ps aux --sort=-%cpu | head -5
```

---

## 🔗 相关资源

- **ROCm 安装指南**: https://rocm.docs.amd.com/
- **Ollama GPU 支持**: https://github.com/ollama/ollama/blob/main/docs/gpu.md
- **AMD GPU 支持列表**: https://rocm.docs.amd.com/projects/radeon/en/latest/docs/system_requirements.html

---

**诊断状态**: ✅ 完成  
**根本原因**: ROCm 未安装  
**建议**: 等待模型自动卸载 或 安装 ROCm
