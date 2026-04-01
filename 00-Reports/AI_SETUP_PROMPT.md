# AI 配置助手提示词

**将此提示词和配置包一起发送给 AI，让它帮你配置远程服务器上的 OpenClaw**

---

## 📋 任务说明

你是一名 OpenClaw 配置专家。我需要你在远程服务器上配置 OpenClaw，使其与本地环境一致。

**服务器信息**：
- IP: `106.53.186.90`
- 用户：`root`
- 已安装：OpenClaw（需要配置）

**目标**：
1. 配置 OpenClaw Gateway（监听 0.0.0.0:18789）
2. 配置所有 AI 模型（MiniMax、Qwen、Kimi、DeepSeek）
3. 部署 DSS 股票分析系统
4. 配置 LanceDB Pro 长期记忆插件
5. 设置多 AI 协作流程

---

## 📦 配置包内容

我已上传 `openclaw-config-*.tar.gz` 到服务器，包含：

```
01-SETUP.md                 # 详细配置指南
02-openclaw.json            # OpenClaw 主配置
03-models.json              # 模型配置（含 API Keys）
04-workspace-files/         # Workspace 文件（SOUL、USER、MEMORY 等）
05-dss-modules/             # DSS 股票分析系统
06-tools/                   # 工具脚本
07-docs/                    # 文档
```

---

## 🚀 配置步骤

### 步骤 1: 解压配置包

```bash
cd ~
tar -xzf openclaw-config-*.tar.gz -C ~/.openclaw/ --strip-components=1
```

### 步骤 2: 验证配置

```bash
# 检查配置文件
cat ~/.openclaw/openclaw.json | head -50
cat ~/.openclaw/agents/main/agent/models.json | grep -A2 "apiKey"

# 检查 Workspace 文件
ls -la ~/.openclaw/workspace/
```

### 步骤 3: 安装依赖

```bash
cd ~/.openclaw/workspace
pip install dashscope flask pandas numpy xgboost lightgbm -q
```

### 步骤 4: 配置 Gateway 监听地址

**重要**：确保 Gateway 监听 `0.0.0.0` 而不是 `127.0.0.1`

```bash
# 检查配置
cat ~/.openclaw/openclaw.json | grep -A2 '"gateway"'

# 如果需要修改，编辑配置文件
nano ~/.openclaw/openclaw.json
```

### 步骤 5: 重启 Gateway

```bash
openclaw gateway restart
```

### 步骤 6: 验证服务

```bash
# 检查 Gateway 状态
openclaw gateway status

# 检查插件
openclaw gateway status | grep -i plugin

# 检查模型
openclaw models list

# 测试 Web UI
curl http://localhost:18789/ | head -20
```

### 步骤 7: 配置防火墙

```bash
# 开放 18789 端口
sudo ufw allow 18789/tcp
sudo ufw reload
sudo ufw status
```

---

## ✅ 验证清单

配置完成后，请运行以下检查并告诉我结果：

```bash
# 1. Gateway 状态
openclaw gateway status

# 2. 插件状态
openclaw gateway status | grep plugin

# 3. 模型列表
openclaw models list

# 4. 端口监听
netstat -tlnp | grep 18789

# 5. Web UI 访问
curl http://localhost:18789/chat?session=main | head -5

# 6. DSS 模块测试
cd ~/.openclaw/workspace
python3 dss_v4.py --help

# 7. 宏观分析模块测试
python3 test_macro_analyzer.py
```

---

## 🔧 故障排查

### Gateway 无法启动

```bash
# 查看日志
journalctl -u openclaw-gateway -n 50 --no-pager

# 前台运行调试
openclaw gateway run
```

### 模型无法使用

```bash
# 检查 API Keys
grep -r "apiKey" ~/.openclaw/agents/main/agent/models.json | head -5

# 测试 MiniMax API
curl -X POST https://api.minimaxi.com/v1/chat/completions \
  -H "Authorization: Bearer sk-cp-..." \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M2.5","messages":[{"role":"user","content":"hello"}]}'
```

### 无法从外部访问

```bash
# 检查防火墙
sudo ufw status

# 检查端口监听
netstat -tlnp | grep 18789

# 应该看到 0.0.0.0:18789 而不是 127.0.0.1:18789
```

---

## 📝 特别配置

### 多 AI 协作流程

已配置到 Workspace，AI 应遵循以下流程：

```
Minimax 2.5 (初版) → README.md → Qwen 3.5 (审查改进) → 迭代 → 终版 → LanceDB Pro → 清理 context
```

### DSS 股票分析系统

位置：`~/.openclaw/workspace/dss_v4.py`

API Keys 已配置：
- Alpha Vantage: `MXAYBEBGFHR6PHYW`
- 宏观分析模块：`dss_modules/macro_analyzer.py`

### LanceDB Pro 长期记忆

位置：`~/.openclaw/workspace/memory-lancedb-pro/`

配置：使用 DashScope embedding (`sk-e8b53592ebe841f28a03d4d54024761c`)

---

## 🎯 最终目标

配置完成后，我应该能够：

1. ✅ 通过浏览器访问：`http://106.53.186.90:18789/chat?session=main`
2. ✅ 使用 MiniMax-M2.5、Qwen3.5-Plus、Kimi、DeepSeek 模型
3. ✅ 运行 DSS 股票分析系统
4. ✅ 使用 LanceDB Pro 长期记忆
5. ✅ 通过 SSH 隧道或公网访问 OpenClaw

---

## 📞 联系方式

配置过程中遇到任何问题，请告诉我：
1. 错误信息（完整日志）
2. 已执行的命令
3. 当前状态

我会协助你解决！

---

**配置时间**: 2026-03-02  
**配置者**: K  
**服务器**: 106.53.186.90
