# WebDAV + AI File Processing System - Setup Complete

> **Setup Time**: 2026-03-02  
> **Server**: 106.53.186.90  
> **Status**: ✅ All Complete

---

## 🎉 Setup Complete!

### Completed Steps

| Step | Status | Details |
|------|--------|---------|
| ✅ Nginx Installation | Done | nginx-extras + apache2-utils |
| ✅ WebDAV Directory | Done | `/var/webdav/` |
| ✅ Password File | Done | `admin:webdav-password-2026` |
| ✅ Nginx Config | Done | WebDAV enabled |
| ✅ Symlink | Done | `/root/.openclaw/workspace/webdav-files` |
| ✅ Service Test | Done | File upload successful |
| ✅ AI Access | Done | Can read/write WebDAV files |

---

## 📋 Access Information

| Item | Value |
|------|-------|
| **WebDAV URL** | `http://106.53.186.90/` |
| **Username** | `admin` |
| **Password** | `webdav-password-2026` |
| **Server Path** | `/var/webdav/` |
| **AI Access Path** | `/root/.openclaw/workspace/webdav-files/` |

---

## 🚀 Usage Methods

### Method 1: Ubuntu Desktop (GNOME Files)

```
1. Open Files (Nautilus)
2. Click "Other Locations" (bottom left)
3. In "Connect to Server" enter: http://106.53.186.90/
4. Click "Connect"
5. Username: admin
6. Password: webdav-password-2026
7. Bookmark it (right-click → Add to Bookmarks)
```

**Or via command line:**

```bash
# Install davfs2
sudo pacman -S davfs2  # Arch
sudo apt install davfs2  # Ubuntu

# Mount
sudo mount -t davfs http://106.53.186.90/ /mnt/webdav

# Or mount to user directory (no sudo needed after setup)
mkdir ~/webdav
mount -t davfs http://106.53.186.90/ ~/webdav

# Add to /etc/fstab for auto-mount
echo "http://106.53.186.90/ /home/kyj/webdav davfs user,noauto 0 0" | sudo tee -a /etc/fstab
```

### Method 2: Arch Linux (KDE/Dolphin or CLI)

**KDE Dolphin:**
```
1. Open Dolphin
2. Click "Network" → "Add Network Folder"
3. Select "WebDAV"
4. Server: 106.53.186.90
5. User: admin
6. Password: webdav-password-2026
7. Name: Remote WebDAV
8. Finish
```

**Command Line (Arch):**
```bash
# Install davfs2
sudo pacman -S davfs2

# Add user to davfs group
sudo usermod -aG davfs $USER

# Create mount point
mkdir ~/webdav

# Mount
mount -t davfs http://106.53.186.90/ ~/webdav

# Configure credentials (optional, avoid entering password each time)
echo "http://106.53.186.90/ admin webdav-password-2026" >> ~/.davfs2/secrets
chmod 600 ~/.davfs2/secrets
```

### Method 3: Command Line Upload/Download

```bash
# Upload file
curl -T input.txt http://106.53.186.90/input.txt --user admin:webdav-password-2026

# Download file
curl http://106.53.186.90/output.txt --user admin:webdav-password-2026 -o output.txt

# List files
curl -X PROPFIND http://106.53.186.90/ --user admin:webdav-password-2026
```

---

## 🤖 AI File Processing

### Ensure SSH Tunnel is Running

```bash
# Check if tunnel exists
pgrep -f "ssh -L 5000:localhost:5000 root@106.53.186.90"

# If not, create it
ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N

# Or use autossh for auto-reconnect
autossh -M 0 -f -N -L 5000:localhost:5000 root@106.53.186.90
```

### Send Processing Command

```bash
# Using the wrapper script
cd /home/kyj/.openclaw/workspace
./ai_process.sh input.txt output.txt "分析并总结"

# Or direct call
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请读取 /root/.openclaw/workspace/webdav-files/input.txt，分析内容并保存到 output.txt",
    "session": "file-processing"
  }'
```

### Python Integration

```python
import requests

# Ensure SSH tunnel is running
# ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N

response = requests.post(
    'http://localhost:5000/chat',
    json={
        'prompt': '请读取 /root/.openclaw/workspace/webdav-files/input.txt，分析并保存到 output.txt',
        'session': 'file-processing'
    }
)

print(response.json()['response'])
```

---

## 📝 Complete Workflow Examples

### Example 1: File Analysis

```bash
# 1. Upload file
echo "这是需要分析的文本" > input.txt
curl -T input.txt http://106.53.186.90/input.txt --user admin:webdav-password-2026

# 2. Send processing command
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请读取 /root/.openclaw/workspace/webdav-files/input.txt，分析内容并写一份摘要保存到 output.txt",
    "session": "file-processing"
  }'

# 3. Read result
curl http://106.53.186.90/output.txt --user admin:webdav-password-2026
```

### Example 2: Code Review

```bash
# 1. Upload code
curl -T main.py http://106.53.186.90/main.py --user admin:webdav-password-2026

# 2. Send review command
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请审查 /root/.openclaw/workspace/webdav-files/main.py 的代码质量，指出问题并给出改进建议，保存到 review.md",
    "session": "code-review"
  }'

# 3. View review
curl http://106.53.186.90/review.md --user admin:webdav-password-2026
```

### Example 3: Data Analysis

```bash
# 1. Upload data
curl -T sales.csv http://106.53.186.90/sales.csv --user admin:webdav-password-2026

# 2. Send analysis command
curl http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请分析 /root/.openclaw/workspace/webdav-files/sales.csv 的销售数据，生成月度统计报告保存到 report.md",
    "session": "data-analysis"
  }'

# 3. View report
curl http://106.53.186.90/report.md --user admin:webdav-password-2026
```

---

## 🛠️ Utility Scripts

### Status Check

```bash
cd /home/kyj/.openclaw/workspace
./webdav_status.sh
```

### AI File Processing

```bash
cd /home/kyj/.openclaw/workspace
./ai_process.sh input.txt output.txt "分析并总结"
```

---

## ✅ Verification Checklist

- [x] WebDAV service running
- [x] Can upload/download files
- [x] Password authentication working
- [x] AI can access WebDAV directory
- [x] SSH tunnel established
- [x] Kimi Remote API working
- [x] Symlink created

---

## 🔒 Security Recommendations

### Change Password

```bash
# On server
ssh root@106.53.186.90 "htpasswd /etc/nginx/.webdav-password admin"
```

### Enable HTTPS (Recommended)

```bash
# On server, install Let's Encrypt
ssh root@106.53.186.90 "
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
"
```

### Restrict Access by IP

```bash
# In Nginx config
location / {
    allow 192.168.1.0/24;  # Only allow LAN
    deny all;
    # ... other config
}
```

---

## 🐛 Troubleshooting

### WebDAV Not Accessible

```bash
# Check Nginx status
ssh root@106.53.186.90 "systemctl status nginx"

# View logs
ssh root@106.53.186.90 "tail -f /var/log/nginx/error.log"
```

### AI Cannot Access Files

```bash
# Check symlink
ssh root@106.53.186.90 "ls -la /root/.openclaw/workspace/ | grep webdav"

# Check permissions
ssh root@106.53.186.90 "ls -la /var/webdav/"
```

### Kimi API Not Accessible

```bash
# Check SSH tunnel
ps aux | grep "ssh -L 5000"

# Recreate tunnel
ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N

# Test API
curl http://localhost:5000/health
```

### Mount Permission Issues (Linux)

```bash
# Add user to davfs group
sudo usermod -aG davfs $USER

# Logout and login again

# Or set permissions
sudo chmod u+s /usr/bin/mount.davfs
```

---

## 📊 System Architecture

```
Arch Laptop / Ubuntu Desktop
   │
   │ WebDAV (http://106.53.186.90/)
   │ Mount as ~/webdav or via Files/Dolphin
   ▼
Remote Server /var/webdav/
   │
   │ Symlink
   ▼
AI Access Path /root/.openclaw/workspace/webdav-files/
   │
   │ Process on command only
   ▼
Read File → Process → Save Result
```

---

## 🎯 Core Principles

✅ **AI doesn't auto-process files** - Only processes when explicitly commanded  
✅ **WebDAV as file storage** - PC and AI share files  
✅ **On-demand trigger** - Send commands via Kimi Remote API  
✅ **Secure isolation** - Password auth + SSH tunnel  

---

## 🐧 Linux-Specific Notes

### Arch Linux

```bash
# Install davfs2
sudo pacman -S davfs2

# Configure credentials
mkdir -p ~/.davfs2
echo "http://106.53.186.90/ admin webdav-password-2026" >> ~/.davfs2/secrets
chmod 600 ~/.davfs2/secrets

# Mount
mount -t davfs http://106.53.186.90/ ~/webdav
```

### Ubuntu

```bash
# Install davfs2
sudo apt install davfs2

# Configure credentials
mkdir -p ~/.davfs2
echo "http://106.53.186.90/ admin webdav-password-2026" >> ~/.davfs2/secrets
chmod 600 ~/.davfs2/secrets

# Mount
mount -t davfs http://106.53.186.90/ ~/webdav
```

### Auto-mount on Boot (systemd)

Create `/etc/systemd/system/webdav-mount.service`:

```ini
[Unit]
Description=Mount WebDAV
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/mount -t davfs http://106.53.186.90/ /home/kyj/webdav
RemainAfterExit=yes
ExecStop=/usr/bin/umount /home/kyj/webdav

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable webdav-mount.service
sudo systemctl start webdav-mount.service
```

---

**Setup Complete Time**: 2026-03-02  
**Setup by**: K  
**Server**: 106.53.186.90  
**Status**: ✅ System Ready for Use!

---

*Ready to go! Let me know if you need any adjustments for your Arch/Ubuntu setup~* 🐧🚀
