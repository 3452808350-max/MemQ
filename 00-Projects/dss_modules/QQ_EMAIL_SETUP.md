# QQ 邮箱 SMTP 配置指南

## 快速配置

编辑 `.env` 文件：

```bash
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=你的QQ号@qq.com
SMTP_PASS=你的授权码
EMAIL_TO=收件人邮箱@qq.com
```

## 获取 QQ 邮箱授权码

### 步骤 1: 开启 SMTP 服务
1. 登录 QQ 邮箱网页版: https://mail.qq.com
2. 点击顶部「设置」→「账户」
3. 找到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」
4. 开启「SMTP服务」

### 步骤 2: 生成授权码
1. 点击「生成授权码」
2. 按提示发送短信验证
3. 获得 16 位授权码 (如: `abcdxyz123456789`)
4. **注意**: 授权码不是登录密码！

### 步骤 3: 配置到 .env
```bash
SMTP_PASS=abcdxyz123456789  # 填入你的授权码
```

## 测试邮件发送

```bash
# 方法1: 测试配置
python email_sender.py

# 方法2: 直接运行验证+邮件
python validate_dss_factors.py \
    --data-path ./dss_data.csv \
    --email
```

## 常见问题

### Q: 提示 "认证失败"
- 确认使用的是**授权码**而非登录密码
- 确认 SMTP 服务已开启
- 检查邮箱地址是否包含 `@qq.com`

### Q: 提示 "连接超时"
- 检查网络连接
- 确认防火墙未拦截 587 端口
- 尝试使用手机热点测试

### Q: 邮件被拦截到垃圾箱
- 在 QQ 邮箱设置中添加发件人到白名单
- 或使用其他邮箱作为收件人测试

## 其他邮箱配置

### 163 邮箱
```bash
SMTP_HOST=smtp.163.com
SMTP_PORT=25
SMTP_USER=xxx@163.com
SMTP_PASS=授权码  # 同样需要授权码
```

### Gmail
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=xxx@gmail.com
SMTP_PASS=应用专用密码  # 非登录密码
```

### 企业微信邮箱
```bash
SMTP_HOST=smtp.exmail.qq.com
SMTP_PORT=465  # 注意是465，使用SSL
SMTP_USER=xxx@company.com
SMTP_PASS=密码
```
