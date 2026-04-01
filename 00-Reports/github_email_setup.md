# GitHub 每日推荐 - 邮件配置指南

## 📧 配置 Outlook 邮箱

### 1. 获取应用专用密码

1. 登录你的 Outlook 邮箱
2. 进入 **账户安全** 设置
3. 找到 **应用密码** 或 **App passwords**
4. 点击 **创建新密码**
5. 复制生成的密码（类似：`abcd efgh ijkl mnop`）

### 2. 编辑配置文件

编辑 `/home/kyj/.openclaw/workspace/.env.github`：

```bash
OUTLOOK_EMAIL=你的邮箱@outlook.com
OUTLOOK_PASSWORD=你的应用密码（去掉空格）
```

### 3. 测试发送

```bash
cd /home/kyj/.openclaw/workspace
source .env.github
export OUTLOOK_EMAIL OUTLOOK_PASSWORD
python3 github_daily.py --email 你的邮箱@outlook.com
```

### 4. 自动发送

配置完成后，每日早上 9 点会自动发送到你的邮箱！

---

## 🔧 故障排除

### 问题：邮件发送失败

**可能原因：**
- 使用了登录密码而不是应用密码
- 邮箱地址填写错误
- 网络问题（需要代理）

**解决方法：**
1. 确认使用的是应用专用密码
2. 检查邮箱地址是否正确
3. 如果有代理，设置：`export HTTPS_PROXY=http://127.0.0.1:7890`

### 问题：收不到邮件

**检查：**
- 垃圾邮件文件夹
- 邮箱是否已满
- 发件人是否被阻止

---

## 📊 当前设置

- **发送时间：** 每天早上 9:00 (Asia/Shanghai)
- **发送目标：** Telegram + Outlook 邮箱
- **任务 ID：** `0f8c24ad-47ca-47ac-b36f-efdb14fdde7e`
