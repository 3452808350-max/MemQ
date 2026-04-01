# WebDAV + AI 按需处理配置指南

> **方案**: Nginx WebDAV + AI 命令触发（不自动处理）  
> **服务器**: 106.53.186.90  
> **核心**: AI 只在收到命令后处理文件

---

## 🏗️ 架构

```
PC 保存文件 → WebDAV → 等待命令 → AI 收到命令 → 处理文件 → 保存结果
```

**关键原则**：
- ✅ WebDAV 只作为文件存储
- ✅ AI 不自动处理文件
- ✅ 明确命令才触发处理

---

## 📦 步骤 1: 服务器安装 Nginx + WebDAV

```bash
# SSH 登录服务器
ssh root@106.53.186.90

# 安装 Nginx
apt update
apt install nginx nginx-extras -y

# 创建 WebDAV 目录
mkdir -p /var/webdav
chown -R www-data:www-data /var/webdav
chmod -R 755 /var/webdav

# 创建 WebDAV 密码文件
htpasswd -c /etc/nginx/.webdav-password admin
# 输入密码（例如：webdav-password-2026）

# Nginx 配置
cat > /etc/nginx/sites-available/webdav << 'EOF'
server {
    listen 80;
    server_name 106.53.186.90;
    
    root /var/webdav;
    
    dav_methods PUT DELETE MKCOL COPY MOVE;
    dav_ext_methods PROPFIND OPTIONS;
    
    create_full_put_path on;
    dav_access user:rw group:r all:r;
    
    auth_basic "WebDAV";
    auth_basic_user_file /etc/nginx/.webdav-password;
    
    location / {
        # 处理 OPTIONS 请求
        if ($request_method = OPTIONS) {
            add_header Dav "1,2";
            add_header Access-Control-Allow-Origin "*";
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE, MKCOL, PROPFIND, COPY, MOVE";
            add_header Access-Control-Allow-Headers "Depth, Authorization, Content-Type, Content-Length, X-Requested-With";
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
    }
}
EOF

# 启用配置
ln -s /etc/nginx/sites-available/webdav /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 开放防火墙
ufw allow 80/tcp

# 测试
curl -X PROPFIND http://106.53.186.90/ --user admin:webdav-password-2026
```

---

## 📦 步骤 2: 本地挂载 WebDAV

### Windows

```
1. 打开"此电脑"
2. 点击"映射网络驱动器"
3. 地址：http://106.53.186.90/
4. 用户名：admin
5. 密码：webdav-password-2026
6. 完成（会显示为 Z: 盘）
```

### macOS

```bash
# Finder → 前往 → 连接服务器
# 地址：http://106.53.186.90/
# 用户名：admin
# 密码：webdav-password-2026
```

### Linux

```bash
# 安装 davfs2
sudo apt install davfs2

# 挂载
sudo mount -t davfs http://106.53.186.90/ /mnt/webdav

# 输入用户名和密码
```

---

## 📦 步骤 3: AI 文件处理集成

### 在服务器上创建符号链接

```bash
# 让 OpenClaw 可以访问 WebDAV 目录
ln -s /var/webdav /root/.openclaw/workspace/webdav-files

# 验证
ls -la /root/.openclaw/workspace/webdav-files
```

### AI 处理命令示例

**PC 发送命令**（通过 Kimi Remote API）：

```bash
# 建立 SSH 隧道（如果还没建立）
ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N

# 发送处理命令
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请读取 /root/.openclaw/workspace/webdav-files/input.txt 文件内容，分析后把结果保存到 /root/.openclaw/workspace/webdav-files/output.txt",
    "session": "file-processing"
  }'
```

---

## 📝 使用流程

### 场景 1: 文件分析

```
1. PC 保存文件
   → 复制到 Z:/input.txt（WebDAV 挂载点）

2. PC 发送命令
   → curl 调用 Kimi Remote API
   → "请分析 Z:/input.txt 并保存结果到 Z:/output.txt"

3. AI 处理
   → 读取 /root/.openclaw/workspace/webdav-files/input.txt
   → 分析内容
   → 写入 /root/.openclaw/workspace/webdav-files/output.txt

4. PC 读取结果
   → 打开 Z:/output.txt
```

### 场景 2: 代码审查

```
1. PC 保存代码
   → Z:/code.py

2. 发送命令
   → "请审查 Z:/code.py 的代码质量，给出改进建议，保存到 Z:/review.txt"

3. AI 审查
   → 读取代码
   → 分析问题
   → 写入建议

4. PC 查看建议
   → 打开 Z:/review.txt
```

### 场景 3: 数据处理

```
1. PC 保存数据
   → Z:/data.csv

2. 发送命令
   → "请分析 Z:/data.csv 的数据，生成统计报告，保存到 Z:/report.md"

3. AI 分析
   → 读取 CSV
   → 计算统计
   → 生成 Markdown 报告

4. PC 查看报告
   → 打开 Z:/report.md
```

---

## 🤖 Python 调用示例

### 封装为函数

```python
import requests

KIMI_API_URL = "http://localhost:5000/chat"
WEBDAV_PATH = "Z:/"  # Windows 或 /mnt/webdav/ (Linux)

def ask_ai_to_process_file(input_file: str, output_file: str, instruction: str):
    """
    让 AI 处理文件
    
    Args:
        input_file: 输入文件名（相对于 WebDAV 根目录）
        output_file: 输出文件名
        instruction: 处理指令
    """
    prompt = f"""
请处理以下文件：

**输入文件**: /root/.openclaw/workspace/webdav-files/{input_file}
**输出文件**: /root/.openclaw/workspace/webdav-files/{output_file}

**处理要求**:
{instruction}

请直接读取输入文件，处理后保存结果到输出文件。完成后回复"处理完成"。
"""
    
    response = requests.post(
        KIMI_API_URL,
        json={'prompt': prompt, 'session': 'file-processing'},
        timeout=300
    )
    
    result = response.json()
    if result.get('success'):
        return result.get('response')
    else:
        return f"Error: {result.get('error')}"

# 使用示例
if __name__ == "__main__":
    # 示例 1: 文件分析
    response = ask_ai_to_process_file(
        input_file="report.txt",
        output_file="analysis.txt",
        instruction="分析这份报告的关键点，总结成 300 字摘要"
    )
    print(response)
    
    # 示例 2: 代码审查
    response = ask_ai_to_process_file(
        input_file="main.py",
        output_file="review.md",
        instruction="审查代码质量，指出潜在问题，给出改进建议"
    )
    print(response)
    
    # 示例 3: 数据处理
    response = ask_ai_to_process_file(
        input_file="sales.csv",
        output_file="summary.md",
        instruction="分析销售数据，生成月度统计报告，包含图表描述"
    )
    print(response)
```

---

## 🎯 命令触发机制

### 方案 A: HTTP API（推荐）

```python
# 本地运行一个简单的 HTTP 服务
from flask import Flask, request
import requests

app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process_file():
    data = request.json
    input_file = data['input']
    output_file = data['output']
    instruction = data['instruction']
    
    # 调用 Kimi API
    response = ask_ai_to_process_file(input_file, output_file, instruction)
    
    return {'status': 'ok', 'response': response}

if __name__ == '__main__':
    app.run(port=8080)
```

**使用**：

```bash
curl http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "input.txt",
    "output": "output.txt",
    "instruction": "分析并总结"
  }'
```

### 方案 B: 命令行工具

```bash
#!/bin/bash
# ai-process.sh

INPUT_FILE=$1
OUTPUT_FILE=$2
INSTRUCTION=$3

curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"请处理 /root/.openclaw/workspace/webdav-files/$INPUT_FILE，$INSTRUCTION，保存到 /root/.openclaw/workspace/webdav-files/$OUTPUT_FILE\",
    \"session\": \"file-processing\"
  }"

echo "✅ 已发送处理命令"
```

**使用**：

```bash
./ai-process.sh input.txt output.txt "分析并总结"
```

---

## ✅ 验证清单

- [ ] WebDAV 可以访问（浏览器打开 http://106.53.186.90/）
- [ ] 可以上传/下载文件
- [ ] 本地可以挂载为网络驱动器
- [ ] AI 可以访问 /root/.openclaw/workspace/webdav-files/
- [ ] 发送命令后 AI 可以处理文件
- [ ] 处理结果可以从 WebDAV 读取

---

## 🔒 安全配置

### 密码管理

```bash
# 修改密码
htpasswd /etc/nginx/.webdav-password admin

# 添加多个用户
htpasswd /etc/nginx/.webdav-password user2
```

### 限制访问 IP

```nginx
# Nginx 配置
location / {
    allow 192.168.1.0/24;  # 只允许内网
    deny all;
    # ... 其他配置
}
```

### HTTPS（推荐）

```bash
# 使用 Let's Encrypt
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

---

## 📊 完整流程示例

### 1. PC 保存文件

```bash
# Windows
echo "这是测试数据" > Z:/input.txt
```

### 2. 发送处理命令

```python
import requests

response = requests.post(
    'http://localhost:5000/chat',
    json={
        'prompt': '请读取 /root/.openclaw/workspace/webdav-files/input.txt，分析内容并保存到 /root/.openclaw/workspace/webdav-files/output.txt',
        'session': 'file-processing'
    }
)

print(response.json()['response'])
```

### 3. 读取结果

```bash
# Windows
type Z:/output.txt

# Linux
cat /mnt/webdav/output.txt
```

---

## 🐛 故障排查

### AI 无法访问文件

```bash
# 检查权限
ls -la /var/webdav/

# 修复权限
chown -R www-data:www-data /var/webdav
chmod -R 755 /var/webdav

# 检查符号链接
ls -la /root/.openclaw/workspace/webdav-files
```

### WebDAV 无法访问

```bash
# 检查 Nginx
systemctl status nginx

# 查看日志
tail -f /var/log/nginx/error.log
```

---

## 💡 最佳实践

1. **文件命名规范**
   - 输入文件：`input_*.txt`
   - 输出文件：`output_*.txt`
   - 避免文件名冲突

2. **命令明确**
   - 清楚说明输入/输出文件
   - 具体描述处理要求
   - 设置合理超时

3. **错误处理**
   - 检查 AI 响应是否成功
   - 验证输出文件是否生成
   - 处理超时情况

---

**配置时间**: 2026-03-02  
**服务器**: 106.53.186.90  
**用途**: WebDAV 文件存储 + AI 按需处理

---

*下一步：告诉我是否开始配置，我帮你在服务器上执行命令*
