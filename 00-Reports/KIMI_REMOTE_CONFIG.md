# Kimi Remote API 配置信息

> **配置时间**: 2026-03-02  
> **服务器**: 106.53.186.90  
> **状态**: ✅ 服务已就绪

---

## 🔑 认证信息

| 项目 | 值 |
|------|-----|
| **API Token** | `kimi-remote-api-token-2026` |
| **服务器 IP** | `106.53.186.90` |
| **SSH 用户** | `root` |
| **本地端口** | `5000` |
| **远程端口** | `5000` |

---

## 🚀 快速使用

### 1. 建立 SSH 隧道

```bash
# 方式 A：使用密码登录
ssh -L 5000:localhost:5000 root@106.53.186.90 -N

# 方式 B：使用密钥登录（推荐）
ssh -i ~/.ssh/id_rsa -L 5000:localhost:5000 root@106.53.186.90 -N

# 方式 C：后台运行
ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N
```

### 2. 测试连接

```bash
# 健康检查
curl http://localhost:5000/health

# 调用 Kimi
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "你好，请帮我写个 Hello World"}'

# 执行命令（需要 Token）
curl http://localhost:5000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command": "ls -la",
    "auth_token": "kimi-remote-api-token-2026"
  }'
```

---

## 📡 API 接口

### 调用 Kimi

```bash
POST http://localhost:5000/chat
Content-Type: application/json

{
  "prompt": "你的问题",
  "session": "会话 ID (可选)",
  "work_dir": "工作目录 (可选)"
}
```

### 执行命令

```bash
POST http://localhost:5000/execute
Content-Type: application/json

{
  "command": "shell 命令",
  "auth_token": "kimi-remote-api-token-2026"
}
```

---

## 🤖 Python 调用示例

```python
import requests

API_TOKEN = "kimi-remote-api-token-2026"

def call_kimi(prompt: str) -> str:
    """调用远程 Kimi API"""
    try:
        resp = requests.post(
            'http://localhost:5000/chat',
            json={'prompt': prompt},
            timeout=300
        )
        data = resp.json()
        if data.get('success'):
            return data.get('response')
        else:
            return f"Error: {data.get('error')}"
    except Exception as e:
        return f"Connection Error: {e}"

def execute_command(cmd: str) -> dict:
    """在远程服务器上执行命令"""
    try:
        resp = requests.post(
            'http://localhost:5000/execute',
            json={
                'command': cmd,
                'auth_token': API_TOKEN
            },
            timeout=60
        )
        return resp.json()
    except Exception as e:
        return {'success': False, 'error': str(e)}

# 测试
if __name__ == "__main__":
    # 测试 Kimi 调用
    print("🤖 Kimi 测试:")
    response = call_kimi("你好，请用 Python 写个 Hello World")
    print(response)
    
    # 测试命令执行
    print("\n📝 命令执行测试:")
    result = execute_command("uname -a")
    print(result)
```

---

## 🔧 自动化脚本

### 快速连接脚本

创建 `~/kimi_connect.sh`：

```bash
#!/bin/bash
# kimi_connect.sh - 连接到远程 Kimi API

SERVER="root@106.53.186.90"
LOCAL_PORT=5000

echo "🔌 建立 SSH 隧道到 $SERVER..."

# 检查是否已运行
if pgrep -f "ssh -L $LOCAL_PORT:localhost:5000 $SERVER" > /dev/null; then
    echo "✅ SSH 隧道已建立"
else
    ssh -L $LOCAL_PORT:localhost:5000 $SERVER -f -N
fi

# 测试连接
echo "🧪 测试 Kimi API 连接..."
if curl -s http://localhost:$LOCAL_PORT/health | grep -q "ok"; then
    echo "✅ Kimi API 连接成功！"
    echo ""
    echo "📝 使用示例:"
    echo "   curl http://localhost:$LOCAL_PORT/chat -d '{\"prompt\":\"你好\"}'"
    echo ""
else
    echo "❌ Kimi API 连接失败，请检查服务状态"
fi
```

```bash
chmod +x ~/kimi_connect.sh
```

---

## 🐛 故障排查

### SSH 连接失败

```bash
# 使用详细输出调试
ssh -v -L 5000:localhost:5000 root@106.53.186.90 -N

# 如果是密钥问题，复制公钥到服务器
ssh-copy-id root@106.53.186.90
```

### API 无法访问

```bash
# 检查 SSH 隧道
ps aux | grep "ssh -L"

# 检查服务状态
curl http://localhost:5000/health

# 如果服务未运行，在服务器上重启
ssh root@106.53.186.90 "pkill -f kimi_remote_api.py; nohup python3 ~/kimi_remote_api.py > ~/kimi_api.log 2>&1 &"
```

### Token 认证失败

```bash
# 确认 Token 正确
echo "kimi-remote-api-token-2026"

# 在服务器上检查环境变量
ssh root@106.53.186.90 "echo \$KIMI_API_TOKEN"
```

---

## ✅ 验证清单

- [ ] SSH 隧道可以建立
- [ ] `curl http://localhost:5000/health` 返回 `{"status": "ok"}`
- [ ] Kimi 调用可以正常工作
- [ ] 命令执行（带 Token）可以正常工作
- [ ] Python 脚本可以调用

---

## 📝 重要提醒

1. **保持 SSH 隧道运行** - 可以使用 `autossh` 自动重连
2. **Token 保密** - 不要公开分享 `kimi-remote-api-token-2026`
3. **定期重启服务** - 避免内存泄漏

---

*配置完成时间：2026-03-02*
