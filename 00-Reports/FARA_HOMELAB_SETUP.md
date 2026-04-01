# Fara-7B + Homelab 配置指南

> **目标**: 在 Homelab (RX6800) 上部署 Fara-7B，实现本地 AI 桌面自动化  
> **服务器**: 192.168.4.147 (Homelab)  
> **现有服务**: Kimi Remote API (端口 5000), WebDAV (端口 80)  
> **日期**: 2026-03-03

---

## 🏗️ 架构设计

```
┌─────────────────┐
│   OpenClaw      │  (虚拟机)
│   (Kaguya)      │
└────────┬────────┘
         │ 局域网调用
         ▼
┌─────────────────┐
│   Homelab       │  192.168.4.147
│   (RX6800)      │
│   ├── Fara-7B   │  端口 5001
│   ├── Kimi CLI  │  已有
│   └── WebDAV    │  端口 80 (已有)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   网页自动化     │
│   Playwright    │
└─────────────────┘
```

---

## 📋 前置检查

### 在 Homelab 上执行

```bash
# SSH 登录 Homelab
ssh user@192.168.4.147

# 1. 检查 GPU
rocm-smi

# 2. 检查 ROCm 版本
rocminfo | grep "Name.*AMD"

# 3. 检查 Python
python3 --version  # 需要 3.10+

# 4. 检查磁盘空间
df -h /home  # 需要至少 20GB

# 5. 检查现有服务
ps aux | grep -E "kimi|webdav|nginx"
```

---

## 🚀 安装步骤

### 步骤 1: 创建 Fara 环境

```bash
# 在 Homelab 上
cd /home

# 克隆 Fara
git clone https://github.com/microsoft/fara.git
cd fara

# 创建 Python 环境
python3 -m venv fara_env
source fara_env/bin/activate

# 安装依赖（AMD GPU 版本）
pip install -e .
pip install vllm-rocm  # AMD ROCm 版本
playwright install

# 安装 ROCm 特定依赖
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0
```

### 步骤 2: 配置 Fara 服务

```bash
# 创建服务配置文件
cat > /home/fara/fara_service.json << 'EOF'
{
  "model": "microsoft/Fara-7B",
  "base_url": "http://localhost:5001",
  "port": 5001,
  "device": "cuda",
  "gpu_memory_utilization": 0.8,
  "max_model_len": 4096
}
EOF
```

### 步骤 3: 启动 Fara 服务

```bash
# 方法 A: vLLM 启动（推荐）
cd /home/fara
source fara_env/bin/activate

vllm serve "microsoft/Fara-7B" \
  --port 5001 \
  --dtype auto \
  --gpu-memory-utilization 0.8 \
  --max-model-len 4096 \
  --device auto

# 方法 B: 如果 vLLM 不支持 RX6800，使用 Ollama
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取 Fara（如果 Ollama 支持）
ollama pull fara:7b

# 启动
ollama serve fara:7b --port 5001
```

### 步骤 4: 创建 Systemd 服务

```bash
# 创建服务文件
sudo cat > /etc/systemd/system/fara.service << 'EOF'
[Unit]
Description=Fara-7B AI Agent Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/fara
Environment="PATH=/home/fara/fara_env/bin:/usr/bin:/bin"
ExecStart=/home/fara/fara_env/bin/vllm serve microsoft/Fara-7B --port 5001 --dtype auto
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable fara
sudo systemctl start fara

# 检查状态
sudo systemctl status fara
```

---

## 🔗 与现有服务集成

### 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| **WebDAV** | 80 | 文件存储（已有） |
| **Kimi Remote API** | 5000 | Kimi CLI 封装（已有） |
| **Fara-7B** | 5001 | 新增 |
| **SSH** | 22 | 远程访问（已有） |

### 防火墙配置

```bash
# 开放 Fara 端口
sudo ufw allow 5001/tcp
sudo ufw reload

# 验证
sudo ufw status
```

---

## 🤖 OpenClaw 集成

### 创建 Fara 调用脚本

```bash
# 在 Homelab 上创建
cat > /home/fara/fara_cli_wrapper.sh << 'EOF'
#!/bin/bash
# fara_cli_wrapper.sh - Fara-7B 命令行封装

TASK="$1"

if [ -z "$TASK" ]; then
    echo "用法：$0 <任务描述>"
    echo "示例：$0 '搜索 iPhone 15 价格'"
    exit 1
fi

cd /home/fara
source fara_env/bin/activate

# 调用 Fara
fara-cli --task "$TASK" --headless

# 保存结果到 WebDAV
RESULT_FILE="/var/webdav/fara_results/$(date +%Y%m%d_%H%M%S).md"
mkdir -p /var/webdav/fara_results

cat > "$RESULT_FILE" << RESULT
# Fara 任务执行结果

**时间**: $(date '+%Y-%m-%d %H:%M:%S')

**任务**: $TASK

**执行日志**:
$(tail -100 /home/fara/fara.log)

**状态**: $([ $? -eq 0 ] && echo "✅ 成功" || echo "❌ 失败")
RESULT

echo "结果已保存到：$RESULT_FILE"
EOF

chmod +x /home/fara/fara_cli_wrapper.sh
```

### 在 OpenClaw 中调用

```python
# 在 OpenClaw 虚拟机上
import requests
import subprocess

def call_fara(task: str) -> str:
    """通过 SSH 调用 Homelab 上的 Fara-7B"""
    
    # SSH 执行
    cmd = [
        'ssh', 'user@192.168.4.147',
        '/home/fara/fara_cli_wrapper.sh',
        f'"{task}"'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

# 使用示例
response = call_fara("搜索最新的 AI 新闻并总结")
print(response)
```

---

## 📝 使用示例

### 示例 1: 搜索任务

```bash
# 在 OpenClaw 上
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请使用 Fara-7B 搜索最新的 AI 新闻，把结果保存到 WebDAV",
    "session": "fara-search"
  }'
```

### 示例 2: 购物比价

```bash
# 直接调用 Fara
ssh user@192.168.4.147 "/home/fara/fara_cli_wrapper.sh '比较 iPhone 15 在 Amazon 和 BestBuy 的价格'"
```

### 示例 3: 数据收集

```bash
# 复杂任务
ssh user@192.168.4.147 "/home/fara/fara_cli_wrapper.sh '收集特斯拉股票最近 30 天的价格，生成 CSV 保存到 WebDAV'"
```

---

## 🧪 测试验证

### 测试 1: Fara 服务状态

```bash
# 在 Homelab 上
curl http://localhost:5001/health

# 应返回服务状态
```

### 测试 2: 简单任务

```bash
# 在 Homelab 上
cd /home/fara
source fara_env/bin/activate
fara-cli --task "whats the weather in new york"
```

### 测试 3: 从 OpenClaw 调用

```bash
# 在 OpenClaw 虚拟机上
ssh user@192.168.4.147 "/home/fara/fara_cli_wrapper.sh '搜索 Python 最新版本的发布时间'"
```

### 测试 4: 检查 WebDAV 结果

```bash
# 检查执行结果
curl http://192.168.4.147/fara_results/ --user admin:webdav-password-2026
```

---

## ⚠️ RX6800 特殊配置

### ROCm 兼容性

RX6800 基于 RDNA2 架构，需要特殊配置：

```bash
# 1. 安装 ROCm 6.0+
sudo apt update
sudo apt install rocm-dkms rocm-opencl-runtime

# 2. 添加用户到 render 和 video 组
sudo usermod -aG render $USER
sudo usermod -aG video $USER

# 3. 设置环境变量
export HSA_OVERRIDE_GFX_VERSION=10.3.0  # RDNA2

# 4. 验证 GPU 识别
rocm-smi
```

### 如果 vLLM 不支持 RX6800

使用 Ollama 作为备选：

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取视觉模型（最接近 Fara 的）
ollama pull llava:7b

# 或使用 Qwen2.5-VL
ollama pull qwen2.5-vl:7b

# 创建封装脚本
cat > /home/fara/ollama_browser.sh << 'EOF'
#!/bin/bash
# 使用 Ollama + Playwright 实现类似 Fara 的功能

TASK="$1"

# 截图当前网页
playwright screenshot --wait-for 2000 https://example.com /tmp/screen.png

# 发送给 Ollama 分析
ollama run llava:7b "分析这个网页截图，$TASK" < /tmp/screen.png
EOF
```

---

## 📊 性能优化

### GPU 内存管理

```bash
# 限制 Fara 使用的 GPU 内存
export VLLM_GPU_MEMORY_UTILIZATION=0.7

# 或者在启动时指定
vllm serve microsoft/Fara-7B \
  --gpu-memory-utilization 0.7 \
  --max-model-len 2048  # 减少上下文长度
```

### 批处理优化

```bash
# 如果同时处理多个任务
export VLLM_MAX_NUM_BATCHED_TOKENS=4096
```

---

## 🔒 安全配置

### SSH 密钥认证

```bash
# 在 OpenClaw 虚拟机上生成密钥
ssh-keygen -t ed25519 -f ~/.ssh/homelab_key

# 复制公钥到 Homelab
ssh-copy-id -i ~/.ssh/homelab_key.pub user@192.168.4.147

# 后续使用密钥连接
ssh -i ~/.ssh/homelab_key user@192.168.4.147
```

### API 访问控制

```bash
# 在 Homelab 上配置防火墙
sudo ufw allow from 192.168.4.0/24 to any port 5001
sudo ufw deny from any to any port 5001
```

---

## 📋 检查清单

- [ ] GPU 驱动安装（ROCm）
- [ ] Python 3.10+ 环境
- [ ] Fara 克隆和依赖安装
- [ ] Playwright 安装
- [ ] Fara 服务启动（端口 5001）
- [ ] Systemd 服务配置
- [ ] 防火墙规则
- [ ] SSH 密钥配置
- [ ] WebDAV 结果目录
- [ ] OpenClaw 调用脚本
- [ ] 测试简单任务
- [ ] 测试复杂任务

---

## 🐛 故障排查

### Fara 无法启动

```bash
# 检查日志
sudo journalctl -u fara -n 50

# 检查 GPU
rocm-smi

# 检查内存
free -h
```

### GPU 不识别

```bash
# 重新安装 ROCm
sudo apt reinstall rocm-dkms

# 重启
sudo reboot

# 验证
rocminfo
```

### 网络连接问题

```bash
# 从 OpenClaw 测试 Homelab 连接
ping 192.168.4.147

# 测试端口
nc -zv 192.168.4.147 5001
```

---

## 📚 资源链接

- **Fara GitHub**: https://github.com/microsoft/fara
- **模型下载**: https://huggingface.co/microsoft/Fara-7B
- **ROCm 文档**: https://rocm.docs.amd.com
- **WebTailBench**: https://huggingface.co/datasets/microsoft/WebTailBench

---

## 💡 下一步

1. **基础测试** - 运行简单网页任务
2. **工作流设计** - 结合 Kimi + Fara + WebDAV
3. **自动化配置** - 定时任务 + 触发器
4. **性能调优** - GPU 内存 + 批处理

---

*配置指南版本：v1.0*  
*创建时间：2026-03-03*  
*适用：Homelab (RX6800) + OpenClaw*
