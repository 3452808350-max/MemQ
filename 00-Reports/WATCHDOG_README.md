# 🦮 OpenClaw Watchdog - 自动监控和修复

> 独立的 Gateway 守护神，即使 OpenClaw 崩溃也能自动恢复

---

## 🎯 功能

- ✅ **健康检查** - 每 30 秒检查 Gateway 状态
- ✅ **自动重启** - Gateway 崩溃时自动重启
- ✅ **问题修复** - 清理僵尸进程、锁文件等
- ✅ **通知报警** - Telegram 通知重要事件
- ✅ **状态持久化** - 记录重启历史
- ✅ **独立运行** - 不依赖 Gateway，单独 systemd 服务

---

## 🚀 快速安装

### 一键安装（推荐）

```bash
cd /home/kyj/.openclaw/workspace
chmod +x install_watchdog.sh
./install_watchdog.sh
```

### 手动安装

```bash
# 1. 复制服务文件
cp openclaw-watchdog.service ~/.config/systemd/user/

# 2. 启用 linger（让服务在登出后继续运行）
sudo loginctl enable-linger $USER

# 3. 重载并启动
systemctl --user daemon-reload
systemctl --user enable openclaw-watchdog
systemctl --user start openclaw-watchdog
```

---

## 📊 查看状态

```bash
# 查看服务状态
systemctl --user status openclaw-watchdog

# 查看实时日志
journalctl --user -u openclaw-watchdog -f

# 查看 Watchdog 日志
tail -f ~/.openclaw/watchdog.log

# 查看历史重启记录
cat ~/.openclaw/watchdog_state.json
```

---

## ⚙️ 配置选项

```bash
# 显示当前配置
python3 watchdog_config.py show

# 获取单个配置
python3 watchdog_config.py get check_interval_seconds

# 设置配置
python3 watchdog_config.py set check_interval_seconds 60
python3 watchdog_config.py set max_restart_attempts 5
python3 watchdog_config.py set telegram_notify false

# 重置配置
python3 watchdog_config.py reset
```

### 配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `check_interval_seconds` | 30 | 健康检查间隔（秒） |
| `max_restart_attempts` | 3 | 最大自动重启次数 |
| `restart_delay_seconds` | 5 | 重启延迟（秒） |
| `gateway_port` | 18789 | Gateway 端口 |
| `telegram_notify` | true | 是否发送 Telegram 通知 |

---

## 🔍 工作原理

```
┌─────────────────────────────────────────┐
│         Watchdog 检查周期                │
├─────────────────────────────────────────┤
│                                         │
│  1. 检查 Gateway 端口 (18789)            │
│     ↓                                   │
│  2. 检查 Gateway 进程                    │
│     ↓                                   │
│  3. 检查配置文件有效性                   │
│     ↓                                   │
│  4. 判断状态：                           │
│     - ok: 一切正常，重置重启计数         │
│     - error: 进程在但端口不通 → 修复     │
│     - dead: 进程和端口都没有 → 重启      │
│     ↓                                   │
│  5. 尝试修复常见问题：                   │
│     - 清理僵尸进程                       │
│     - 删除锁文件                         │
│     - 修复配置权限                       │
│     ↓                                   │
│  6. 如果需要重启：                       │
│     - 检查重启频率限制                   │
│     - 停止 Gateway                       │
│     - 启动 Gateway                       │
│     - 发送 Telegram 通知                 │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🛠️ 管理命令

```bash
# 启动服务
systemctl --user start openclaw-watchdog

# 停止服务
systemctl --user stop openclaw-watchdog

# 重启服务
systemctl --user restart openclaw-watchdog

# 禁用服务
systemctl --user disable openclaw-watchdog

# 卸载服务
systemctl --user stop openclaw-watchdog
rm ~/.config/systemd/user/openclaw-watchdog.service
systemctl --user daemon-reload
```

---

## 📋 日志示例

### 正常检查日志

```
2026-03-01 22:00:00 - INFO - 执行健康检查...
2026-03-01 22:00:00 - INFO - 健康状态：ok - {'port_listening': True, 'process_running': True}
```

### 自动重启日志

```
2026-03-01 22:05:00 - INFO - 执行健康检查...
2026-03-01 22:05:00 - WARNING - 发现问题：Gateway 未运行
2026-03-01 22:05:00 - INFO - 正在重启 Gateway...
2026-03-01 22:05:01 - INFO - 停止 Gateway...
2026-03-01 22:05:03 - INFO - 启动 Gateway...
2026-03-01 22:05:05 - INFO - Gateway 重启成功（总重启次数：1）
```

### 错误日志

```
2026-03-01 22:10:00 - ERROR - Gateway 重启失败
2026-03-01 22:10:00 - WARNING - 发送通知失败：...
```

---

## 🆘 故障排查

### Watchdog 不启动

```bash
# 检查 systemd 服务
systemctl --user status openclaw-watchdog

# 查看详细日志
journalctl --user -u openclaw-watchdog --no-pager -n 50

# 手动运行测试
python3 /home/kyj/.openclaw/workspace/openclaw_watchdog.py
```

### Gateway 无法自动重启

```bash
# 检查 Gateway 是否能手动启动
openclaw gateway --force

# 检查端口占用
lsof -i :18789

# 检查 Watchdog 日志
tail -f ~/.openclaw/watchdog.log
```

### Telegram 通知不发送

```bash
# 检查配置
python3 watchdog_config.py get telegram_notify

# 手动测试通知
openclaw message send --target self --message "Watchdog 测试"
```

---

## 📊 状态文件

Watchdog 状态保存在 `~/.openclaw/watchdog_state.json`：

```json
{
  "restart_count": 3,
  "last_restart": "2026-03-01T22:05:05.123456"
}
```

---

## 🔐 安全设置

Watchdog 服务使用以下安全限制：

- `NoNewPrivileges=true` - 不获取新权限
- `ProtectSystem=strict` - 系统目录只读
- `ProtectHome=read-only` - 家目录只读
- `ReadWritePaths=/home/kyj/.openclaw` - 只允许写 OpenClaw 目录
- `PrivateTmp=true` - 独立临时目录

---

## 💡 最佳实践

1. **检查间隔** - 生产环境建议 30-60 秒
2. **最大重启次数** - 建议 3-5 次，过多说明有根本问题
3. **通知** - 开启 Telegram 通知，及时发现问题
4. **日志轮转** - 定期清理日志文件（>100MB 时）
5. **定期检查** - 每周查看一次重启记录

---

## 📝 文件清单

```
/home/kyj/.openclaw/workspace/
├── openclaw_watchdog.py          # 主程序
├── watchdog_config.py             # 配置工具
├── install_watchdog.sh            # 安装脚本
├── openclaw-watchdog.service      # systemd 服务文件
└── WATCHDOG_README.md             # 本文档
```

---

*最后更新：2026-03-01*
