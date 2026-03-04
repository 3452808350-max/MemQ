# SSH 密钥配置指南

> **问题**: SSH 隧道建立失败（Permission denied: publickey）  
> **目标**: 配置无密码 SSH 登录到 106.53.186.90

---

## 🔑 方案 A: 手动复制公钥（推荐）

### 步骤 1: 查看公钥

```bash
cat ~/.ssh/id_rsa.pub
```

复制输出的内容（以 `ssh-rsa` 开头的一长串字符）

### 步骤 2: SSH 登录服务器

```bash
ssh root@106.53.186.90
# 输入密码登录
```

### 步骤 3: 在服务器上添加公钥

```bash
# 创建 .ssh 目录
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 添加公钥（粘贴步骤 1 复制的内容）
echo "ssh-rsa AAAA..." >> ~/.ssh/authorized_keys

# 设置正确权限
chmod 600 ~/.ssh/authorized_keys
```

### 步骤 4: 测试无密码登录

```bash
# 退出服务器
exit

# 测试无密码登录
ssh root@106.53.186.90 "echo 连接成功"
```

---

## 🔑 方案 B: 使用密码建立隧道

如果不想配置密钥，可以每次输入密码：

```bash
# 建立隧道（会提示输入密码）
ssh -L 5000:localhost:5000 root@106.53.186.90 -N

# 或使用 sshpass（需要安装）
sshpass -p "你的密码" ssh -L 5000:localhost:5000 root@106.53.186.90 -f -N
```

---

## 🧪 测试连接

配置好密钥后，运行测试脚本：

```bash
cd /home/kyj/.openclaw/workspace
./test_kimi_remote.sh
```

---

## 🐛 故障排查

### 仍然提示 Permission denied

```bash
# 检查服务器端 SSH 配置
ssh root@106.53.186.90

# 在服务器上编辑
nano /etc/ssh/sshd_config

# 确保以下配置正确：
PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys
PermitRootLogin yes  # 或 prohibit-password

# 重启 SSH 服务
systemctl restart sshd
```

### 检查权限

```bash
# 在服务器上
ls -la ~/.ssh/
# 应该是：drwx------ (700)

ls -la ~/.ssh/authorized_keys
# 应该是：-rw------- (600)
```

---

## ✅ 验证成功

```bash
# 应该无需密码即可连接
ssh root@106.53.186.90 "echo 成功"

# 输出：成功
```

---

*配置时间：2026-03-02*
