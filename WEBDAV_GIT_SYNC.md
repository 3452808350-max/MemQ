# WebDAV + Git 文件同步配置指南

> **目标**：通过 WebDAV 挂载服务器目录 + Git 同步实现文件中转  
> **服务器**: 106.53.186.90  
> **用途**：本地 PC ↔ 服务器 ↔ AI 文件无缝同步

---

## 🏗️ 架构

```
本地 PC (Windows/Mac/Linux)
       │
       │ WebDAV (挂载为网络驱动器)
       ▼
远程服务器 (106.53.186.90)
       │
       │ Git 同步
       ▼
OpenClaw Workspace (AI 可访问)
```

---

## 📦 步骤 1: 服务器上安装 WebDAV

### 方案 A: 使用 Nginx + WebDAV（推荐）

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
htpasswd -c /etc/nginx/.webdav-password your_username
# 输入密码

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
        # 启用 WebDAV
        if ($request_method = OPTIONS) {
            add_header Dav "1,2";
            add_header Access-Control-Allow-Origin "*";
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE, MKCOL, PROPFIND, COPY, MOVE";
            add_header Access-Control-Allow-Headers "Depth, Authorization, Content-Type, Content-Length, X-Requested-With";
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        # 同步后钩子（Git 自动同步）
        location ~ ^/sync-trigger$ {
            limit_except POST { deny all; }
            fastcgi_pass unix:/var/run/fcgiwrap.socket;
            include fastcgi_params;
            fastcgi_param SCRIPT_FILENAME /var/webdav/sync.sh;
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
```

### 方案 B: 使用 rclone + WebDAV（简单）

```bash
# 安装 rclone
curl https://rclone.org/install.sh | sudo bash

# 配置 WebDAV 服务端（使用 rclone serve）
rclone serve webdav /var/webdav --addr :80 --user your_username --pass your_password
```

---

## 📦 步骤 2: 配置 Git 同步

### 在服务器上创建 Git 仓库

```bash
# 创建工作目录
mkdir -p ~/sync-workspace
cd ~/sync-workspace

# 初始化 Git 仓库
git init --bare

# 设置钩子（同步后自动更新文件）
cat > hooks/post-receive << 'EOF'
#!/bin/bash
GIT_WORK_TREE=/var/webdata git checkout -f
EOF

chmod +x hooks/post-receive
```

### 在本地配置 Git

```bash
# 本地创建仓库
mkdir -p ~/openclaw-sync
cd ~/openclaw-sync
git init

# 添加远程仓库
git remote add origin root@106.53.186.90:~/sync-workspace

# 创建测试文件
echo "Hello from PC" > test.txt
git add .
git commit -m "Initial commit"

# 推送
git push -u origin master
```

---

## 📦 步骤 3: 本地挂载 WebDAV

### Windows

```
1. 打开"此电脑"
2. 点击"映射网络驱动器"
3. 地址：http://106.53.186.90/
4. 输入用户名和密码
5. 完成
```

### macOS

```bash
# Finder → 前往 → 连接服务器
# 地址：http://106.53.186.90/
# 或使用命令行
mount_webdav http://your_username@106.53.186.90/ ~/mnt/webdav
```

### Linux

```bash
# 安装 davfs2
sudo apt install davfs2

# 挂载
sudo mount -t davfs http://106.53.186.90/ /mnt/webdav

# 或永久挂载（/etc/fstab）
echo "http://106.53.186.90/ /mnt/webdav davfs user,noauto 0 0" | sudo tee -a /etc/fstab
```

---

## 📦 步骤 4: 自动化同步脚本

### 创建同步脚本（服务器端）

```bash
# ~/sync.sh
#!/bin/bash
cd ~/sync-workspace
git pull origin master
cp -r ~/sync-workspace/* /var/webdav/
```

### 创建同步脚本（本地）

```bash
#!/bin/bash
# sync_to_server.sh

WORKSPACE="~/openclaw-sync"
REMOTE="root@106.53.186.90:~/sync-workspace"

cd $WORKSPACE

# Git 推送
git add .
git commit -m "Auto-sync from $(hostname)"
git push origin master

# 触发服务器同步
curl -X POST http://106.53.186.90/sync-trigger

echo "✅ 同步完成"
```

---

## 📦 步骤 5: OpenClaw 集成

### 配置 AI 访问目录

```bash
# 在服务器上
ln -s /var/webdav ~/.openclaw/workspace/remote-files

# AI 可以访问 ~/.openclaw/workspace/remote-files/
```

### 测试 AI 读写

```python
# 测试 AI 能否访问 WebDAV 目录
import os

webdav_path = "/home/root/.openclaw/workspace/remote-files"

# 列出文件
files = os.listdir(webdav_path)
print("WebDAV 文件:", files)

# 写入文件
with open(f"{webdav_path}/ai_note.txt", "w") as f:
    f.write("这是 AI 写的笔记")

# 读取文件
with open(f"{webdav_path}/test.txt", "r") as f:
    print("PC 创建的文件:", f.read())
```

---

## 🔄 使用流程

### 场景 1: PC → 服务器 → AI

```
1. PC 保存文件到 WebDAV 挂载目录
2. Git 自动推送到服务器
3. AI 在 ~/.openclaw/workspace/remote-files/ 读取
```

### 场景 2: AI → 服务器 → PC

```
1. AI 写入文件到 ~/.openclaw/workspace/remote-files/
2. Git 自动提交并推送
3. PC 从 WebDAV 目录读取（或 Git pull）
```

### 场景 3: 双向同步

```
1. PC 修改文件 → Git push
2. AI 修改文件 → Git push
3. 定期 Git pull 保持同步
```

---

## 🛠️ 自动化配置

### Cron 定时同步（服务器）

```bash
# 每 5 分钟同步一次
crontab -e

# 添加
*/5 * * * * cd ~/sync-workspace && git pull origin master
*/5 * * * * rsync -av ~/sync-workspace/ /var/webdav/
```

### Git Hook 自动同步

```bash
# 服务器端 post-receive 钩子
cat > ~/sync-workspace/hooks/post-receive << 'EOF'
#!/bin/bash
GIT_WORK_TREE=/var/webdav git checkout -f
cd /var/webdav && git add . && git commit -m "Auto-sync from WebDAV" && git push origin master
EOF

chmod +x ~/sync-workspace/hooks/post-receive
```

---

## 🔒 安全配置

### HTTPS（推荐）

```bash
# 使用 Let's Encrypt 证书
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com

# 更新 Nginx 配置
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    # ... 其他配置
}
```

### 防火墙限制

```bash
# 只允许特定 IP 访问 WebDAV
ufw allow from 192.168.1.0/24 to any port 80
```

---

## 🧪 测试清单

- [ ] WebDAV 可以访问（浏览器打开 http://106.53.186.90/）
- [ ] 可以上传/下载文件
- [ ] Git 推送成功
- [ ] 本地可以挂载为网络驱动器
- [ ] AI 可以读写 /var/webdav/ 目录
- [ ] 同步脚本正常工作

---

## 📊 使用示例

### 1. 本地创建文件

```bash
# PC 上
echo "这是测试文档" > ~/mnt/webdav/test.txt
```

### 2. AI 读取

```python
# AI 代码
with open("/var/webdav/test.txt", "r") as f:
    content = f.read()
    print(f"PC 创建的文件：{content}")
```

### 3. AI 写入

```python
# AI 代码
with open("/var/webdav/ai_response.txt", "w") as f:
    f.write("这是 AI 的回复")
```

### 4. PC 读取 AI 回复

```bash
cat ~/mnt/webdav/ai_response.txt
```

---

## 🐛 故障排查

### WebDAV 无法访问

```bash
# 检查 Nginx 状态
systemctl status nginx

# 查看日志
tail -f /var/log/nginx/error.log
```

### Git 同步失败

```bash
# 手动测试
cd ~/sync-workspace
git pull origin master
```

### 权限问题

```bash
# 修复权限
chown -R www-data:www-data /var/webdav
chmod -R 755 /var/webdav
```

---

## ✅ 完成标志

配置完成后，你应该能够：

1. ✅ 在文件管理器中访问 WebDAV 目录（像本地文件夹一样）
2. ✅ 本地保存文件 → 自动同步到服务器
3. ✅ AI 读取/写入 WebDAV 目录
4. ✅ Git 自动同步保持文件一致

---

**配置时间**: 2026-03-02  
**服务器**: 106.53.186.90  
**用途**: WebDAV + Git 文件中转

---

*下一步：告诉我你想用哪种方案（Nginx 或 rclone），我帮你详细配置*
