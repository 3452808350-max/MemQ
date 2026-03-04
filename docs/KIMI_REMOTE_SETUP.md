# Kimi Remote API - 远程调用指南

> 在远程服务器上部署 HTTP API，实现本地对远程 kimi-cli 的调用

---

## 📦 部署步骤（在远程服务器上）

### 1. 上传脚本

```bash
# 将 kimi_remote_api.py 上传到远程服务器
scp kimi_remote_api.py user@remote-server:~/kimi_remote_api.py
```

### 2. 安装依赖

```bash
# SSH 登录远程服务器
ssh user@remote-server

# 安装 Flask
pip install flask --user
```

### 3. 启动服务

```bash
# 设置 API Token（用于认证）
export KIMI_API_TOKEN='your-secret-token-here'

# 启动服务（后台运行）
nohup python3 ~/kimi_remote_api.py > ~/kimi_api.log 2>&1 &

# 检查服务是否启动
curl http://localhost:5000/health
# 应返回：{"status": "ok", "service": "kimi-remote-api"}
```

### 4. 开放端口（可选）

**选项 A：仅内网访问**（安全）
```bash
# 只允许本地访问，通过 SSH 隧道连接
```

**选项 B：公网访问**（需要防火墙配置）
```bash
# Ubuntu UFW
sudo ufw allow 5000/tcp

# 或只允许特定 IP
sudo ufw allow from 1.2.3.4 to any port 5000
```

---

## 🔌 连接方式

### 方式 1：SSH 隧道（推荐，最安全）

```bash
# 本地建立 SSH 隧道
ssh -L 5000:localhost:5000 user@remote-server -N

# 保持隧道后台运行
ssh -L 5000:localhost:5000 user@remote-server -f -N

# 本地调用
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "你好，请帮我写个 Python 脚本"}'
```

### 方式 2：直接公网访问（如果服务器有公网 IP）

```bash
curl http://your-server-ip:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "你好"}'
```

---

## 📡 API 接口

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

{
  "prompt": "你的问题",
  "session": "会话 ID (可选，默认 default)",
  "work_dir": "工作目录 (可选)"
}

# 响应
{
  "success": true,
  "response": "Kimi 的回答...",
  "error": null,
  "returncode": 0
}
```

### 3. 执行 Shell 命令（需要认证）

```bash
POST /execute
Content-Type: application/json

{
  "command": "ls -la",
  "auth_token": "your-secret-token"
}

# 响应
{
  "success": true,
  "stdout": "输出内容...",
  "stderr": "",
  "returncode": 0
}
```

---

## 🤖 在 OpenClaw 中集成

创建一个 Python 工具函数：

```python
# 在 OpenClaw 工具中调用
import requests
import json

def call_remote_kimi(prompt: str, session: str = "default"):
    """调用远程 kimi-cli"""
    
    # 通过 SSH 隧道访问
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

---

## 🔒 安全建议

1. **使用 SSH 隧道** - 不要直接暴露 API 到公网
2. **设置强 Token** - `KIMI_API_TOKEN` 用随机字符串
3. **防火墙限制** - 只允许信任的 IP 访问
4. **HTTPS** - 如果需要公网访问，用 Nginx 反向代理 + HTTPS
5. **日志监控** - 定期检查 `~/kimi_api.log`

---

## 🛠️ 故障排查

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
ssh -L 5000:localhost:5000 user@remote-server -N
```

### 认证失败

```bash
# 检查 Token 是否一致
echo $KIMI_API_TOKEN

# 重启服务
pkill -f kimi_remote_api.py
export KIMI_API_TOKEN='your-token'
nohup python3 ~/kimi_remote_api.py > ~/kimi_api.log 2>&1 &
```

---

## 📝 下一步

1. **部署到远程服务器**
2. **测试连接**
3. **在 OpenClaw 中集成调用函数**
4. **配置自动启动（systemd）**

---

*最后更新：2026-03-02*
