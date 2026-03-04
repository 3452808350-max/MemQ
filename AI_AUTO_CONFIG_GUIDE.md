# 🤖 AI 远程服务器自动配置指南

> **目标**: 让 AI 自动配置 Fara-7B + Kimi Remote API + WebDAV 环境  
> **服务器**: 192.168.4.147 (Homelab, RX6800)  
> **执行者**: 服务器上的 AI 助手  
> **日期**: 2026-03-03

---

## 📋 任务说明

**你好！请帮我在服务器上配置以下环境：**

1. ✅ **Fara-7B** - 微软的 7B 电脑使用 Agent 模型
2. ✅ **Kimi Remote API** - Kimi CLI 的 HTTP 封装（已安装，需检查）
3. ✅ **WebDAV** - 文件存储服务（已安装，需检查）
4. ✅ **OpenClaw 集成** - 创建调用脚本

**所有配置都应该自动化执行，无需人工干预。**

---

## 🚀 自动配置脚本

### 步骤 1: 检查现有服务

```bash
#!/bin/bash
# check_existing_services.sh

echo "🔍 检查现有服务..."

# 检查 Kimi CLI
if command -v kimi-cli &> /dev/null; then
    echo "✅ Kimi CLI 已安装"
    KIMI_INSTALLED=true
else
    echo "❌ Kimi CLI 未安装"
    KIMI_INSTALLED=false
fi

# 检查 Kimi Remote API (端口 5000)
if netstat -tlnp 2>/dev/null | grep -q ":5000"; then
    echo "✅ Kimi Remote API 运行中 (端口 5000)"
    KIMI_API_RUNNING=true
else
    echo "⚠️  Kimi Remote API 未运行"
    KIMI_API_RUNNING=false
fi

# 检查 WebDAV (端口 80)
if netstat -tlnp 2>/dev/null | grep -q ":80"; then
    echo "✅ WebDAV 运行中 (端口 80)"
    WEBDAV_RUNNING=true
else
    echo "⚠️  WebDAV 未运行"
    WEBDAV_RUNNING=false
fi

# 检查 GPU
if command -v rocm-smi &> /dev/null; then
    echo "✅ ROCm 已安装"
    rocm-smi
else
    echo "❌ ROCm 未安装"
fi

# 检查 Python
python3 --version
echo "Python 路径：$(which python3)"

# 检查磁盘空间
df -h /home | tail -1
```

---

### 步骤 2: 安装 Fara-7B

```bash
#!/bin/bash
# install_fara.sh

set -e

echo "🚀 开始安装 Fara-7B..."

# 创建目录
mkdir -p /opt/fara
cd /opt/fara

# 克隆仓库
echo "📦 克隆 Fara 仓库..."
git clone https://github.com/microsoft/fara.git .

# 创建 Python 环境
echo "🐍 创建 Python 环境..."
python3 -m venv fara_env
source fara_env/bin/activate

# 安装依赖
echo "📦 安装依赖..."
pip install --upgrade pip
pip install -e .
pip install playwright
playwright install

# 安装 ROCm 特定依赖（AMD GPU）
echo "🔧 安装 ROCm 依赖..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0

# 检查 GPU
echo "🎮 检查 GPU..."
if command -v rocm-smi &> /dev/null; then
    rocm-smi
    export HSA_OVERRIDE_GFX_VERSION=10.3.0  # RX6800 RDNA2
fi

echo "✅ Fara-7B 安装完成！"
```

---

### 步骤 3: 创建 Fara 服务

```bash
#!/bin/bash
# setup_fara_service.sh

set -e

echo "🔧 配置 Fara 系统服务..."

# 创建服务文件
cat > /etc/systemd/system/fara.service << 'EOF'
[Unit]
Description=Fara-7B AI Agent Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fara
Environment="PATH=/opt/fara/fara_env/bin:/usr/bin:/bin"
Environment="HSA_OVERRIDE_GFX_VERSION=10.3.0"
ExecStart=/opt/fara/fara_env/bin/vllm serve microsoft/Fara-7B --port 5001 --dtype auto --gpu-memory-utilization 0.8
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
echo "🔌 启用服务..."
systemctl daemon-reload
systemctl enable fara
systemctl start fara

# 检查状态
echo "📊 服务状态:"
systemctl status fara --no-pager

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 测试服务
echo "🧪 测试服务..."
curl -s http://localhost:5001/health || echo "⚠️  服务尚未就绪"

echo "✅ Fara 服务配置完成！"
```

---

### 步骤 4: 创建调用脚本

```bash
#!/bin/bash
# create_cli_wrappers.sh

set -e

echo "🔧 创建命令行封装脚本..."

# 创建 Fara 调用脚本
cat > /usr/local/bin/fara-task << 'EOF'
#!/bin/bash
# fara-task - Fara-7B 任务执行脚本

TASK="$1"
OUTPUT_DIR="/var/webdav/fara_results"

if [ -z "$TASK" ]; then
    echo "用法：$0 <任务描述>"
    echo "示例：$0 '搜索 iPhone 15 价格'"
    exit 1
fi

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 执行任务
echo "🤖 执行任务：$TASK"
cd /opt/fara
source fara_env/bin/activate

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_FILE="$OUTPUT_DIR/task_${TIMESTAMP}.md"

# 运行 Fara
fara-cli --task "$TASK" --headless 2>&1 | tee /tmp/fara_last_output.log

# 保存结果
cat > "$RESULT_FILE" << RESULT
# Fara 任务结果

**时间**: $(date '+%Y-%m-%d %H:%M:%S')

**任务**: $TASK

**执行日志**:
\`\`\`
$(tail -50 /tmp/fara_last_output.log)
\`\`\`

**状态**: $([ $? -eq 0 ] && echo "✅ 成功" || echo "❌ 失败")
RESULT

echo "✅ 结果已保存到：$RESULT_FILE"
EOF

chmod +x /usr/local/bin/fara-task

# 创建 Kimi 调用脚本（如果不存在）
if [ ! -f /usr/local/bin/kimi-task ]; then
    cat > /usr/local/bin/kimi-task << 'EOF'
#!/bin/bash
# kimi-task - Kimi CLI 任务执行脚本

PROMPT="$1"

if [ -z "$PROMPT" ]; then
    echo "用法：$0 <提示词>"
    exit 1
fi

echo "🤖 Kimi 处理：$PROMPT"
kimi-cli "$PROMPT"
EOF

    chmod +x /usr/local/bin/kimi-task
fi

echo "✅ 调用脚本创建完成！"
```

---

### 步骤 5: 配置防火墙

```bash
#!/bin/bash
# setup_firewall.sh

echo "🔒 配置防火墙..."

# 启用 UFW（如果未启用）
if ! systemctl is-active --quiet ufw; then
    echo "启用 UFW..."
    ufw --force enable
fi

# 开放端口
echo "开放端口..."
ufw allow 22/tcp    comment "SSH"
ufw allow 80/tcp    comment "WebDAV"
ufw allow 5000/tcp  comment "Kimi Remote API"
ufw allow 5001/tcp  comment "Fara-7B"

# 重新加载
ufw reload

echo "✅ 防火墙配置完成！"
echo ""
echo "当前规则:"
ufw status numbered
```

---

### 步骤 6: 测试所有服务

```bash
#!/bin/bash
# test_all_services.sh

echo "🧪 测试所有服务..."

# 测试 1: Kimi CLI
echo ""
echo "📝 测试 1: Kimi CLI"
if command -v kimi-cli &> /dev/null; then
    kimi-cli --version
    echo "✅ Kimi CLI 正常"
else
    echo "❌ Kimi CLI 未安装"
fi

# 测试 2: Kimi Remote API
echo ""
echo "🌐 测试 2: Kimi Remote API"
if curl -s http://localhost:5000/health | grep -q "ok"; then
    echo "✅ Kimi Remote API 正常"
else
    echo "❌ Kimi Remote API 未运行"
fi

# 测试 3: WebDAV
echo ""
echo "📂 测试 3: WebDAV"
if curl -s -X PROPFIND http://localhost:5000/ --user admin:webdav-password-2026 | grep -q "multistatus"; then
    echo "✅ WebDAV 正常"
else
    echo "⚠️  WebDAV 可能未运行或密码不同"
fi

# 测试 4: Fara-7B
echo ""
echo "🤖 测试 4: Fara-7B"
if curl -s http://localhost:5001/health | grep -q "ok"; then
    echo "✅ Fara-7B 服务正常"
else
    echo "⏳ Fara-7B 服务可能正在启动..."
    systemctl status fara --no-pager | tail -5
fi

# 测试 5: GPU
echo ""
echo "🎮 测试 5: GPU"
if command -v rocm-smi &> /dev/null; then
    rocm-smi | head -10
else
    echo "❌ ROCm 未安装"
fi

echo ""
echo "✅ 所有测试完成！"
```

---

### 步骤 7: 创建 OpenClaw 集成脚本

```bash
#!/bin/bash
# setup_openclaw_integration.sh

echo "🔗 配置 OpenClaw 集成..."

# 创建远程调用脚本
cat > /opt/fara/openclaw_bridge.sh << 'EOF'
#!/bin/bash
# openclaw_bridge.sh - OpenClaw 远程调用桥接

ACTION="$1"
TASK="$2"

case "$ACTION" in
    "fara")
        /usr/local/bin/fara-task "$TASK"
        ;;
    "kimi")
        /usr/local/bin/kimi-task "$TASK"
        ;;
    "webdav-upload")
        # 上传文件到 WebDAV
        curl -T "$TASK" http://localhost:80/ --user admin:webdav-password-2026
        ;;
    "webdav-download")
        # 从 WebDAV 下载文件
        curl "http://localhost:80/$TASK" --user admin:webdav-password-2026 -o "/tmp/$(basename $TASK)"
        ;;
    *)
        echo "用法：$0 {fara|kimi|webdav-upload|webdav-download} <任务/文件>"
        exit 1
        ;;
esac
EOF

chmod +x /opt/fara/openclaw_bridge.sh

# 创建 SSH 密钥认证（如果 OpenClaw 需要）
echo ""
echo "🔑 SSH 配置..."
if [ ! -f /root/.ssh/authorized_keys ]; then
    mkdir -p /root/.ssh
    chmod 700 /root/.ssh
    touch /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
fi

echo ""
echo "✅ OpenClaw 集成配置完成！"
echo ""
echo "使用示例:"
echo "  ssh root@192.168.4.147 '/opt/fara/openclaw_bridge.sh fara \"搜索 AI 新闻\"'"
echo "  ssh root@192.168.4.147 '/opt/fara/openclaw_bridge.sh kimi \"写首诗\"'"
```

---

## 🎯 一键执行脚本

```bash
#!/bin/bash
# auto_configure_all.sh
# 一键自动配置所有服务

set -e

echo "🚀 开始自动配置服务器..."
echo "时间：$(date)"
echo ""

# 步骤 1: 检查现有服务
echo "📋 步骤 1: 检查现有服务"
bash check_existing_services.sh
echo ""

# 步骤 2: 安装 Fara-7B
echo "📦 步骤 2: 安装 Fara-7B"
bash install_fara.sh
echo ""

# 步骤 3: 创建 Fara 服务
echo "🔧 步骤 3: 创建 Fara 服务"
bash setup_fara_service.sh
echo ""

# 步骤 4: 创建调用脚本
echo "📝 步骤 4: 创建调用脚本"
bash create_cli_wrappers.sh
echo ""

# 步骤 5: 配置防火墙
echo "🔒 步骤 5: 配置防火墙"
bash setup_firewall.sh
echo ""

# 步骤 6: 测试所有服务
echo "🧪 步骤 6: 测试所有服务"
bash test_all_services.sh
echo ""

# 步骤 7: 配置 OpenClaw 集成
echo "🔗 步骤 7: 配置 OpenClaw 集成"
bash setup_openclaw_integration.sh
echo ""

echo "========================================"
echo "✅ 所有配置完成！"
echo "========================================"
echo ""
echo "服务状态:"
echo "  - Kimi Remote API: http://192.168.4.147:5000"
echo "  - Fara-7B: http://192.168.4.147:5001"
echo "  - WebDAV: http://192.168.4.147:80"
echo ""
echo "使用示例:"
echo "  ssh root@192.168.4.147 '/usr/local/bin/fara-task \"搜索 AI 新闻\"'"
echo "  ssh root@192.168.4.147 '/usr/local/bin/kimi-task \"写首诗\"'"
echo ""
echo "配置时间：$(date)"
```

---

## 📝 执行说明

**请服务器上的 AI 执行以下命令：**

```bash
# 1. 下载配置脚本
cd /tmp
wget https://raw.githubusercontent.com/your-repo/auto-config/main/auto_configure_all.sh
# 或者手动创建上述脚本

# 2. 赋予执行权限
chmod +x auto_configure_all.sh

# 3. 执行自动配置
./auto_configure_all.sh

# 4. 等待完成（约 10-15 分钟）
# 脚本会自动：
# - 检查现有服务
# - 安装 Fara-7B
# - 配置系统服务
# - 创建调用脚本
# - 配置防火墙
# - 测试所有服务
# - 配置 OpenClaw 集成

# 5. 验证配置
systemctl status fara
curl http://localhost:5001/health
```

---

## ✅ 验证清单

配置完成后，AI 应该报告以下信息：

- [ ] Kimi CLI 已安装并可运行
- [ ] Kimi Remote API 运行在 5000 端口
- [ ] WebDAV 运行在 80 端口
- [ ] Fara-7B 服务运行在 5001 端口
- [ ] GPU (RX6800) 已正确识别
- [ ] 防火墙规则已配置
- [ ] 调用脚本已创建
- [ ] OpenClaw 集成已配置

---

## 🐛 故障排查

### 如果 Fara 启动失败

```bash
# 检查日志
journalctl -u fara -n 50

# 检查 GPU
rocm-smi

# 检查内存
free -h

# 手动测试
cd /opt/fara
source fara_env/bin/activate
vllm serve microsoft/Fara-7B --port 5001 --dtype auto
```

### 如果 ROCm 不工作

```bash
# 重新安装 ROCm
apt update
apt install --reinstall rocm-dkms rocm-opencl-runtime

# 重启
reboot

# 验证
rocminfo
```

---

## 📞 完成后报告

配置完成后，请 AI 提供以下信息：

1. **所有服务的运行状态**
2. **端口监听情况**
3. **GPU 识别状态**
4. **测试命令的输出**
5. **任何错误或警告**

---

*配置指南版本：v1.0*  
*创建时间：2026-03-03*  
*适用于：Homelab (192.168.4.147, RX6800)*
