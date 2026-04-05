# Telegram 通知配置指南

## 快速配置

### 1. 创建 Telegram Bot

1. 打开 Telegram，搜索 `@BotFather`
2. 发送 `/start`
3. 发送 `/newbot`
4. 按提示输入 Bot 名称和用户名
5. 获得 **Bot Token** (格式: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. 获取 Chat ID

**方法 A: 通过 API (推荐)**

1. 给刚创建的 Bot 发送一条消息
2. 浏览器访问:
   ```
   https://api.telegram.org/bot<你的BotToken>/getUpdates
   ```
3. 在返回的 JSON 中找到 `chat` -> `id`，这就是 **Chat ID**

**方法 B: 使用 @userinfobot**

1. 搜索 `@userinfobot`
2. 发送 `/start`
3. 获得你的 User ID (就是 Chat ID)

### 3. 配置 .env 文件

编辑 `.env` 文件:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=8278708856
```

### 4. 测试

```bash
cd /home/kyj/.openclaw/workspace/00-Projects/dss_modules
python3 telegram_notifier.py
```

## 使用方式

### 在验证脚本中启用 Telegram 通知

```bash
# 运行验证并发送 Telegram 通知
python validate_dss_factors.py --data-path ./dss_data.csv --telegram
```

### Python 代码中使用

```python
from telegram_notifier import send_validation_report, send_simple_notification

# 发送验证报告
send_validation_report('./report.md', summary='今日验证完成')

# 发送简单通知
send_simple_notification('任务完成', 'DSS预测任务已成功执行')
```

## 通知格式

Telegram 通知支持 Markdown 格式，包含:
- 📊 验证摘要
- ✅ 通过的因子
- ❌ 失败的因子
- 📁 报告文件路径

## 常见问题

**Q: 为什么收不到消息?**
A: 检查:
1. 是否给 Bot 发送了 `/start`
2. Bot Token 是否正确
3. Chat ID 是否正确

**Q: 可以给群组发送通知吗?**
A: 可以! 把 Bot 加入群组，然后获取群组的 Chat ID (通常是负数)

**Q: 支持图片/文件吗?**
A: 当前版本只支持文本通知，可以扩展支持文件发送
