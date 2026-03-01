# OpenClaw 维护技能包 🦞

> 集成自 [win4r/OpenClaw-Skill](https://github.com/win4r/OpenClaw-Skill)
> 专注于运维、故障排查、安全加固

---

## 🚀 快速诊断命令链

**遇到问题时，按顺序执行：**

```bash
# 1. 快速概览
openclaw status

# 2. Gateway 状态
openclaw gateway status

# 3. 查看日志
openclaw logs --follow

# 4. 诊断问题
openclaw doctor

# 5. 频道健康检查
openclaw channels status --probe

# 6. 安全检查
openclaw security audit
```

---

## 🔧 核心维护任务

### Gateway 管理

```bash
# 安装为系统服务
openclaw gateway install

# 启动/停止/重启
openclaw gateway start
openclaw gateway stop
openclaw gateway restart

# 强制启动（杀掉已有监听器）
openclaw gateway --force

# 前台运行（调试用）
openclaw gateway --port 18789 --verbose
```

### 配置管理

```bash
# 读取配置
openclaw config get <path>
# 例：openclaw config get gateway.bind

# 修改配置
openclaw config set <path> <value>
# 例：openclaw config set gateway.port 18790

# 交互式配置向导
openclaw configure
```

### 频道管理

```bash
# 添加频道
openclaw channels add

# WhatsApp QR 配对
openclaw channels login --channel whatsapp

# 查看已配置频道
openclaw channels list

# 频道健康检查
openclaw channels status --probe
```

### 安全加固

```bash
# 安全检查
openclaw security audit

# 自动修复（安全操作）
openclaw security audit --fix

# 深度检查
openclaw security audit --deep
```

---

## 🔍 常见故障排查

### 1. Gateway 无法启动

```bash
# 检查端口占用
lsof -i :18789

# 强制启动
openclaw gateway --force

# 查看日志
openclaw logs --follow
```

### 2. Telegram 无法接收消息

```bash
# 检查频道状态
openclaw channels status --probe

# 检查配对
openclaw pairing list telegram

# 检查代理（中国大陆需要）
# 确保 7890 端口代理运行
```

### 3. 模型认证失败

```bash
# 检查模型状态
openclaw models status --probe

# 重新设置模型
openclaw models set <model>

# 检查 API Key
openclaw secrets list
```

### 4. 安全检查失败

```bash
# 运行审计
openclaw security audit

# 自动修复
openclaw security audit --fix

# 手动检查配置
openclaw config get gateway.auth
```

---

## 📁 关键文件路径

| 路径 | 用途 |
|------|------|
| `~/.openclaw/openclaw.json` | 主配置文件 |
| `~/.openclaw/.env` | 环境变量 |
| `~/.openclaw/workspace` | 默认工作空间 |
| `~/.openclaw/agents/<id>/` | 每 Agent 状态 |
| `~/.openclaw/credentials/` | 频道凭证 |

---

## 🔐 安全基线配置

```json5
{
  // Gateway 认证（必须）
  gateway: {
    auth: {
      mode: "token",
      token: "your-random-token-here"
    }
  },
  
  // 频道访问控制
  channels: {
    telegram: {
      dmPolicy: "pairing",  // 或 "allowlist"
      allowFrom: ["+86123456789"]
    }
  },
  
  // 工具策略
  toolPolicy: {
    default: "minimal"  // 或 "coding"/"full"
  }
}
```

---

## 📊 健康检查清单

每周执行一次：

- [ ] `openclaw status` - 所有服务正常
- [ ] `openclaw gateway status` - RPC probe ok
- [ ] `openclaw channels status --probe` - 频道在线
- [ ] `openclaw security audit` - 无严重问题
- [ ] `openclaw models status --probe` - 模型认证有效
- [ ] 检查日志无重复错误

---

## 🆘 紧急恢复

### Gateway 完全无法启动

```bash
# 1. 停止所有进程
pkill -f openclaw

# 2. 清理端口
lsof -ti :18789 | xargs kill -9

# 3. 重置配置（备份后）
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak
openclaw configure

# 4. 重新启动
openclaw gateway --force
```

### 频道凭证损坏

```bash
# 1. 删除凭证
rm -rf ~/.openclaw/credentials/<channel>/<account>/

# 2. 重新配对
openclaw channels login --channel <channel>
```

---

## 📚 完整文档

详细参考：
- [channels.md](./references/channels.md) - 频道配置
- [gateway_ops.md](./references/gateway_ops.md) - Gateway 运维
- [security.md](./references/security.md) - 安全加固
- [channel_troubleshooting.md](./references/channel_troubleshooting.md) - 故障排查

---

*最后更新：2026-03-01*
