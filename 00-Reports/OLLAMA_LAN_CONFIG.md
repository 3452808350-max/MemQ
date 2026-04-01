# 🔓 Ollama 局域网访问配置指南

---

## 📋 配置步骤

### 步骤 1: 创建 systemd 配置

```bash
# 创建配置目录
sudo mkdir -p /etc/systemd/system/ollama.service.d

# 创建覆盖配置
sudo cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_ORIGINS=*"
EOF
```

### 步骤 2: 重新加载并重启服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 重启 Ollama
sudo systemctl restart ollama

# 检查状态
systemctl status ollama --no-pager | head -10
```

### 步骤 3: 配置防火墙

```bash
# 开放 11434 端口（如果需要使用 UFW）
sudo ufw allow 11434/tcp

# 或者只允许特定 IP 段（推荐）
sudo ufw allow from 192.168.1.0/24 to any port 11434

# 检查防火墙状态
sudo ufw status | grep 11434
```

### 步骤 4: 验证配置

```bash
# 检查监听端口
ss -tlnp | grep 11434
# 或
netstat -tlnp | grep 11434

# 应该看到：0.0.0.0:11434 或 *:11434
```

---

## 🌐 访问方式

### 本地访问
```
http://localhost:11434
```

### 局域网访问
```
http://[服务器 IP]:11434
```

**获取服务器 IP**:
```bash
hostname -I | awk '{print $1}'
# 或
ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d/ -f1
```

---

## 🔒 安全配置

### 方案 1: 防火墙限制 IP（推荐）

```bash
# 只允许特定 IP 段访问
sudo ufw allow from 192.168.1.0/24 to any port 11434

# 或者只允许特定 IP
sudo ufw allow from 192.168.1.100 to any port 11434
```

### 方案 2: 只监听特定网卡

```bash
# 编辑配置
sudo nano /etc/systemd/system/ollama.service.d/override.conf

# 只监听特定 IP（替换为你的内网 IP）
[Service]
Environment="OLLAMA_HOST=192.168.1.100:11434"
Environment="OLLAMA_ORIGINS=*"

# 重新加载
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

---

## 🧪 测试连接

### 从其他机器测试

```bash
# 从局域网其他机器测试
curl http://[服务器 IP]:11434/api/tags

# 应该返回已下载的模型列表
```

### 测试 API

```bash
# 测试 API 端点
curl http://[服务器 IP]:11434/api/generate -d '{
  "model": "qwen2.5:latest",
  "prompt": "Hello",
  "stream": false
}'
```

---

## 📊 完整配置脚本

如果你想一键配置，运行：

```bash
# 下载并执行配置脚本
wget https://raw.githubusercontent.com/your-repo/configure_ollama_lan.sh -O /tmp/configure_ollama.sh
chmod +x /tmp/configure_ollama.sh
sudo /tmp/configure_ollama.sh
```

---

## 🔍 故障排查

### 问题 1: 无法连接

```bash
# 检查服务状态
systemctl status ollama

# 检查端口监听
ss -tlnp | grep 11434

# 检查防火墙
sudo ufw status | grep 11434
```

### 问题 2: 连接被拒绝

```bash
# 检查 OLLAMA_HOST 配置
systemctl show ollama | grep OLLAMA_HOST

# 应该是：OLLAMA_HOST=0.0.0.0:11434
```

### 问题 3: 防火墙阻止

```bash
# 临时关闭防火墙测试
sudo ufw disable

# 测试连接
curl http://[服务器 IP]:11434/api/tags

# 重新开启防火墙
sudo ufw enable

# 添加规则
sudo ufw allow 11434/tcp
```

---

## 📝 总结

### 配置完成后

- ✅ Ollama 监听所有网卡 (0.0.0.0:11434)
- ✅ 局域网内可以访问
- ✅ 防火墙已配置（可选）

### 访问地址

- **本地**: http://localhost:11434
- **局域网**: http://[服务器内网 IP]:11434

---

**配置完成后，局域网内的其他设备就可以访问 Ollama API 了！** 🚀
