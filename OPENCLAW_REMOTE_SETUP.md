# OpenClaw 远程服务器配置指南

> **版本**: 2026-03-02  
> **目标服务器**: 106.53.186.90  
> **用途**: 完整复制本地 OpenClaw 配置到远程服务器

---

## 📦 配置包内容

```
openclaw-config-package/
├── 01-SETUP.md                 # 本文件 - 配置指南
├── 02-openclaw.json            # OpenClaw 主配置
├── 03-models.json              # 模型配置（含 API Keys）
├── 04-workspace-files/         # Workspace 重要文件
│   ├── SOUL.md
│   ├── USER.md
│   ├── IDENTITY.md
│   ├── AGENTS.md
│   ├── MEMORY.md
│   ├── memory-projects.md
│   ├── memory-resources.md
│   ├── memory-preferences.md
│   └── memory-lessons.md
├── 05-dss-modules/             # DSS 系统模块
│   ├── dss_v4.py
│   ├── dss_modules/
│   │   ├── macro_analyzer.py
│   │   ├── data_loader.py
│   │   ├── features.py
│   │   └── models.py
│   └── test_macro_analyzer.py
└── 06-tools/                   # 工具脚本
    └── kimi_remote_api.py
```

---

## 🚀 快速配置（AI 辅助）

### 步骤 1: 上传配置包到服务器

```bash
# 在本地打包
cd /home/kyj/.openclaw/workspace
tar -czf openclaw-config.tar.gz \
  openclaw.json \
  agents/main/agent/models.json \
  workspace/SOUL.md \
  workspace/USER.md \
  workspace/IDENTITY.md \
  workspace/AGENTS.md \
  workspace/MEMORY.md \
  workspace/memory-*.md \
  workspace/dss_v4.py \
  workspace/dss_modules/ \
  workspace/docs/

# 上传到服务器
scp openclaw-config.tar.gz root@106.53.186.90:~/
```

### 步骤 2: SSH 登录服务器并解压

```bash
ssh root@106.53.186.90

# 解压配置包
cd ~
tar -xzf openclaw-config.tar.gz -C ~/.openclaw/

# 或者让 AI 帮你解压
```

### 步骤 3: 验证配置

```bash
# 检查 OpenClaw 状态
openclaw status

# 检查 Gateway
openclaw gateway status

# 重启 Gateway 应用配置
openclaw gateway restart
```

---

## ⚙️ 手动配置（如需）

### 1. 配置 OpenClaw 主配置

```bash
# 备份原配置
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak

# 复制新配置
cp /path/to/02-openclaw.json ~/.openclaw/openclaw.json
```

### 2. 配置模型（API Keys）

```bash
# 复制模型配置
cp /path/to/03-models.json ~/.openclaw/agents/main/agent/models.json
```

### 3. 配置 Workspace

```bash
# 复制 Workspace 文件
cp /path/to/04-workspace-files/* ~/.openclaw/workspace/

# 复制 DSS 模块
cp -r /path/to/05-dss-modules/* ~/.openclaw/workspace/

# 复制工具
cp -r /path/to/06-tools/* ~/.openclaw/workspace/tools/
```

### 4. 安装依赖

```bash
# 进入 workspace
cd ~/.openclaw/workspace

# 安装 Python 依赖
pip install dashscope flask pandas numpy xgboost lightgbm -q

# 验证插件
openclaw gateway status | grep -i plugin
```

### 5. 重启 Gateway

```bash
openclaw gateway restart
```

---

## 🔧 Gateway 配置要点

### 监听地址（重要！）

确保 Gateway 监听 `0.0.0.0` 而不是 `127.0.0.1`，否则无法从外部访问：

```json
{
  "gateway": {
    "host": "0.0.0.0",
    "port": 18789
  }
}
```

### Telegram 配置（如需要）

```json
{
  "channels": {
    "telegram": {
      "botToken": "YOUR_BOT_TOKEN",
      "enabled": true
    }
  }
}
```

### 代理配置（中国大陆服务器可能需要）

```json
{
  "proxy": {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890"
  }
}
```

---

## 🔐 API Keys 清单

**已包含在配置中**：

| 服务 | Key | 状态 |
|------|-----|------|
| MiniMax | `sk-cp-ri0nrljo8Ug...` | ✅ 已配置 |
| DashScope | `sk-e8b53592ebe8...` | ✅ 已配置 |
| Kimi | `sk-1CMESS3UGM3N...` | ✅ 已配置 |
| DeepSeek | `sk-55369c09b7fb...` | ✅ 已配置 |
| Alpha Vantage | `MXAYBEBGFHR6PHYW` | ✅ 已配置 |

**安全提醒**：
- ⚠️ 这些是敏感信息，不要公开分享
- ✅ 服务器配置好后，建议删除配置包
- 🔒 确保服务器防火墙只允许信任的 IP 访问

---

## 📝 多 AI 协作流程规范

**已配置到服务器**，AI 会自动遵循：

```
Minimax 2.5 (初版) → README.md → Qwen 3.5 (审查改进) → 迭代 → 终版 → LanceDB Pro → 清理 context
```

**核心机制**：
- AI 之间通过 README.md 传递上下文
- 使用临时 workspace 隔离任务
- 终版文档存入 LanceDB Pro 长期记忆
- 任务完成后清理 context

---

## 🧪 验证清单

配置完成后，运行以下检查：

```bash
# 1. Gateway 状态
openclaw gateway status
# ✅ 应显示：running

# 2. 插件状态
openclaw gateway status | grep plugin
# ✅ 应显示：memory-lancedb-pro registered

# 3. 模型配置
openclaw models list
# ✅ 应显示：MiniMax、Qwen、Kimi、DeepSeek

# 4. 访问 Web UI
curl http://localhost:18789/
# ✅ 应返回 HTML

# 5. 测试 DSS 模块
cd ~/.openclaw/workspace
python3 dss_v4.py --test
# ✅ 应正常运行

# 6. 测试宏观分析模块
python3 test_macro_analyzer.py
# ✅ 应显示宏观指标
```

---

## 🌐 远程访问配置

### 方案 A: 直接公网访问

```bash
# 开放防火墙端口
sudo ufw allow 18789/tcp
sudo ufw reload

# 访问
http://106.53.186.90:18789/chat?session=main
```

### 方案 B: SSH 隧道（推荐）

```bash
# 本地建立隧道
ssh -L 18789:localhost:18789 root@106.53.186.90 -N

# 访问本地
http://localhost:18789/chat?session=main
```

### 方案 C: Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:18789;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 🐛 故障排查

### Gateway 无法启动

```bash
# 查看日志
journalctl -u openclaw-gateway -n 100 --no-pager

# 前台运行调试
openclaw gateway run
```

### 模型无法使用

```bash
# 检查 API Keys
cat ~/.openclaw/agents/main/agent/models.json | grep apiKey

# 测试 API 连接
curl -H "Authorization: Bearer sk-xxx" https://api.minimaxi.com/v1/chat/completions
```

### 插件未加载

```bash
# 检查插件目录
ls -la ~/.openclaw/workspace/plugins/

# 重新注册插件
openclaw gateway restart --force
```

---

## 📚 重要文件位置

配置完成后，文件位置：

| 类型 | 路径 |
|------|------|
| OpenClaw 配置 | `~/.openclaw/openclaw.json` |
| 模型配置 | `~/.openclaw/agents/main/agent/models.json` |
| Workspace | `~/.openclaw/workspace/` |
| 记忆文件 | `~/.openclaw/workspace/memory/` |
| DSS 系统 | `~/.openclaw/workspace/dss_v4.py` |
| 宏观模块 | `~/.openclaw/workspace/dss_modules/macro_analyzer.py` |
| LanceDB Pro | `~/.openclaw/workspace/memory-lancedb-pro/` |

---

## ✅ 完成标志

配置完成后，你应该能够：

1. ✅ 访问 Web UI: `http://106.53.186.90:18789/chat?session=main`
2. ✅ 使用 MiniMax、Qwen、Kimi、DeepSeek 模型
3. ✅ 运行 DSS 股票分析系统
4. ✅ 使用 LanceDB Pro 长期记忆
5. ✅ 遵循多 AI 协作流程

---

**配置完成时间**: 2026-03-02  
**配置者**: K  
**服务器**: 106.53.186.90

---

*如有问题，查看 `~/.openclaw/workspace/docs/` 中的详细文档*
