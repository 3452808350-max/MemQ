# SSH 隧道 + Kimi Remote API 配置指南

> **目标**：在远程服务器上部署 Kimi Remote API，通过 SSH 隧道实现本地远程调用  
> **服务器**：106.53.186.90  
> **用途**：远程控制服务器上的 kimi-cli

---

## 📋 方案说明

### 架构

```
┌─────────────────┐         SSH 隧道          ┌─────────────────┐
│     本地        │ ────────────────────────► │   远程服务器     │
│   OpenClaw     │                           │   (106.53.186.90)│
│                │   http://localhost:5000   │                │
│                │ ◄──────────────────────── │                │
└─────────────────┘                           └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Flask API     │
                                              │   Port 5000     │
                                              │                 │
                                              │   kimi-cli      │
                                              └─────────────────┘
```

### 优势

| 特性 | 说明 |
|------|------|
| 🔒 安全 | SSH 加密，无需暴露 API 到公网 |
| 🚀 快速 | 直接本地访问，低延迟 |
| 🛠️ 简单 | 无需复杂配置，只需 SSH |
| 💰 免费 | 无需额外服务 |

---

## 🚀 配置步骤

### 步骤 1: 确认 kimi-cli 已安装

```bash
# 检查 kimi-cli
which kimi-cli
kimi-cli --version

# 如果未安装
pip install kimi-cli --user
```

### 步骤 2: 安装 Flask

```bash
pip install flask --user
```

### 步骤 3: 创建 API 脚本

在服务器上创建 `~/kimi_remote_api.py`：

```python
#!/usr/bin/env python3
"""
Kimi Remote API - 简单的 HTTP 封装
允许通过 HTTP 调用 kimi-cli
"""
from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

# 配置
KIMI_CMD = "/root/.local/bin/kimi-cli"  # kimi-cli 路径
DEFAULT_WORK_DIR = "/root/workspace"     # 默认工作目录

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "kimi-remote-api"})

@app.route('/chat', methods=['POST'])
def chat():
    """
    调用 kimi-cli
    
    JSON Body:
    {
        "prompt": "你的问题",
        "session": "会话 ID (可选，默认 default)",
        "work_dir": "工作目录 (可选)"
    }
    """
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Missing 'prompt' field"}), 400
    
    prompt = data['prompt']
    session = data.get('session', 'default')
    work_dir = data.get('work_dir', DEFAULT_WORK_DIR)
    
    try:
        # 构建命令
        cmd = [
            KIMI_CMD,
            '-S', session,
            '-w', work_dir,
            prompt
        ]
        
        # 执行命令（设置超时）
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 分钟超时
        )
        
        return jsonify({
            "success": True,
            "response": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "returncode": result.returncode
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Command timed out (5 minutes)"
        }), 504
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/execute', methods=['POST'])
def execute():
    """
    执行任意 shell 命令（需要认证）
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    
    # 简单认证
    auth_token = data.get('auth_token')
    expected_token = os.environ.get('KIMI_API_TOKEN', 'change-me')
    
    if auth_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    command = data.get('command')
    if not command:
        return jsonify({"error": "Missing 'command' field"}), 400
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return jsonify({
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # 生成默认 token
    import secrets
    default_token = secrets.token_urlsafe(16)
    print(f"\n🔑 默认 API Token: {default_token}")
    print(f"   设置方式：export KIMI_API_TOKEN='{default_token}'\n")
    
    app.run(host='127.0.0.1', port=5000, debug=False)
```

### 步骤 4: 启动 API 服务

```bash
# 设置 API Token
export KIMI_API_TOKEN='my-secret-token-123'

# 启动服务（前台运行，用于测试）
python3 ~/kimi_remote_api.py

# 或后台运行（生产环境）
nohup python3 ~/kimi_remote_api.py > ~/kimi_api.log 2>&1 &

# 检查服务
curl http://localhost:5000/health
```

应返回：
```json
{"status": "ok", "service": "kimi-remote-api"}
```

### 步骤 5: 本地建立 SSH 隧道

**在本地机器上执行**：

```bash
# 建立 SSH 隧道（保持运行）
ssh -L 5000:localhost:5000 root@106.53.186.90 -N

# 或后台运行
ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N

# 或使用 autossh（自动重连）
autossh -M 0 -f -N -L 5000:localhost:5000 root@106.53.186.90
```

### 步骤 6: 测试连接

**在本地机器上**：

```bash
# 测试健康检查
curl http://localhost:5000/health

# 测试调用 Kimi
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "你好，请帮我写个 Hello World Python 脚本"}'

# 测试执行命令
curl http://localhost:5000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "ls -la",
    "auth_token": "my-secret-token-123"
  }'
```

---

## 📡 API 接口文档

### 1. 健康检查

```bash
GET /health

# 响应
{
  "status": "ok",
  "service": "kimi-remote-api"
}
```

### 2. 调用 Kimi

```bash
POST /chat
Content-Type: application/json

Body:
{
  "prompt": "你的问题",
  "session": "会话 ID (可选，默认 default)",
  "work_dir": "工作目录 (可选)"
}

# 响应
{
  "success": true,
  "response": "Kimi 的回答内容...",
  "error": null,
  "returncode": 0
}
```

### 3. 执行 Shell 命令（需要认证）

```bash
POST /execute
Content-Type: application/json

Body:
{
  "command": "shell 命令",
  "auth_token": "API Token"
}

# 响应
{
  "success": true,
  "stdout": "命令输出",
  "stderr": "错误输出",
  "returncode": 0
}
```

---

## 🤖 在 OpenClaw 中集成

### Python 调用示例

```python
import requests
import json

def call_remote_kimi(prompt: str, session: str = "default"):
    """通过 SSH 隧道调用远程 kimi-cli"""
    
    url = "http://localhost:5000/chat"
    
    payload = {
        "prompt": prompt,
        "session": session
    }
    
    response = requests.post(url, json=payload, timeout=300)
    result = response.json()
    
    if result.get('success'):
        return result.get('response')
    else:
        return f"Error: {result.get('error')}"

# 使用
response = call_remote_kimi("帮我分析一下今天的股票行情")
print(response)
```

### OpenClaw 工具集成

在 OpenClaw 中创建一个工具函数：

```python
# ~/.openclaw/workspace/tools/kimi_remote.py
import requests

def kimi_chat(prompt: str) -> str:
    """Remote Kimi Chat via SSH tunnel"""
    try:
        resp = requests.post(
            'http://localhost:5000/chat',
            json={'prompt': prompt},
            timeout=300
        )
        data = resp.json()
        return data.get('response', 'No response')
    except Exception as e:
        return f"Error: {e}"
```

---

## 🛠️ 自动化脚本

### 启动脚本（服务器端）

创建 `~/start_kimi_api.sh`：

```bash
#!/bin/bash
# start_kimi_api.sh - 启动 Kimi Remote API

# 设置 Token
export KIMI_API_TOKEN='my-secret-token-123'

# 检查是否已运行
if pgrep -f "kimi_remote_api.py" > /dev/null; then
    echo "✅ Kimi API 已在运行"
    exit 0
fi

# 启动服务
cd ~
nohup python3 ~/kimi_remote_api.py > ~/kimi_api.log 2>&1 &

# 等待启动
sleep 2

# 检查状态
if curl -s http://localhost:5000/health | grep -q "ok"; then
    echo "✅ Kimi API 启动成功"
else
    echo "❌ Kimi API 启动失败，查看日志：~/kimi_api.log"
fi
```

```bash
chmod +x ~/start_kimi_api.sh
```

### 隧道脚本（本地）

创建 `~/kimi_tunnel.sh`：

```bash
#!/bin/bash
# kimi_tunnel.sh - 建立 SSH 隧道到远程服务器

SERVER="root@106.53.186.90"
LOCAL_PORT=5000

# 检查是否已运行
if ssh -O check -L $LOCAL_PORT:localhost:5000 $SERVER 2>/dev/null; then
    echo "✅ SSH 隧道已建立"
    exit 0
fi

# 建立隧道
echo "🔌 建立 SSH 隧道..."
ssh -L $LOCAL_PORT:localhost:5000 $SERVER -f -N

# 测试连接
if curl -s http://localhost:$LOCAL_PORT/health | grep -q "ok"; then
    echo "✅ Kimi API 连接成功"
else
    echo "❌ Kimi API 连接失败"
fi
```

```bash
chmod +x ~/kimi_tunnel.sh
```

---

## 🐛 故障排查

### 服务无法启动

```bash
# 查看日志
tail -f ~/kimi_api.log

# 检查端口是否被占用
netstat -tlnp | grep 5000

# 检查 kimi-cli 是否可用
kimi-cli --version
```

### 连接超时

```bash
# 检查 SSH 隧道
ps aux | grep "ssh -L"

# 重新建立隧道
ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N

# 测试连接
curl http://localhost:5000/health
```

### 认证失败

```bash
# 检查 Token 是否一致
echo $KIMI_API_TOKEN

# 重启服务
pkill -f kimi_remote_api.py
export KIMI_API_TOKEN='your-token'
python3 ~/kimi_remote_api.py
```

### Kimi-cli 执行失败

```bash
# 测试 kimi-cli
kimi-cli '你好'

# 检查路径
which kimi-cli

# 修改脚本中的 KIMI_CMD 路径
nano ~/kimi_remote_api.py
```

---

## ✅ 验证清单

配置完成后，请运行以下检查：

```bash
# 服务器端
# 1. API 服务运行中
curl http://localhost:5000/health

# 2. Kimi 可以调用
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "你好"}'

# 本地端
# 3. SSH 隧道建立
ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N

# 4. 本地可以访问
curl http://localhost:5000/health
```

---

## 🔒 安全建议

1. **使用 SSH 隧道** - 不要直接暴露 API 到公网
2. **设置强 Token** - `KIMI_API_TOKEN` 用随机字符串
3. **防火墙限制** - 只允许本地访问 5000 端口
4. **日志监控** - 定期检查 `~/kimi_api.log`
5. **定期重启** - 避免内存泄漏

---

## 📝 下一步

1. ✅ 部署 API 到服务器
2. ✅ 测试 SSH 隧道连接
3. ✅ 在 OpenClaw 中集成调用函数
4. ✅ 配置自动启动（systemd 或 cron）

---

**配置时间**: 2026-03-02  
**服务器**: 106.53.186.90  
**用途**: 远程 Kimi 调用

---

*如有问题，查看日志文件 `~/kimi_api.log`*
