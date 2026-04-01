# Kimi CLI 集成技能

> 让 OpenClaw 控制 Kimi CLI 执行代码任务

## 🎯 功能

- 通过 OpenClaw 调用 Kimi CLI 执行编程任务
- 自动保存对话到 LanceDB 记忆系统
- 支持项目上下文管理
- Telegram 通知任务完成

## 📋 使用方法

### 基础用法

```bash
# 1. 简单代码任务
kimi "帮我写一个 Python 函数，计算斐波那契数列"

# 2. 带项目上下文
cd /path/to/project
kimi "添加用户认证功能"

# 3. 使用斜杠命令
kimi "/init"  # 生成 AGENTS.md
kimi "/help"  # 查看帮助
```

### OpenClaw 集成

#### 方式 1: 直接 exec 调用

```python
# 在 OpenClaw 中
exec("kimi '帮我修复这个 bug: ...'")
```

#### 方式 2: ACP 会话

```python
# 创建 ACP 会话
sessions_spawn(
  runtime="acp",
  agentId="kimi",
  task="实现用户登录功能"
)
```

## 🔧 配置

### 1. Kimi CLI 配置

```bash
# 登录 Kimi
kimi /login

# 选择平台（推荐 Kimi Code）
# 自动打开浏览器 OAuth 授权

# 验证配置
kimi --version
```

### 2. OpenClaw 配置

在 `openclaw.json` 中添加 Kimi 工具：

```json
{
  "tools": {
    "kimi": {
      "enabled": true,
      "command": "kimi",
      "workdir": "/home/kyj/.openclaw/workspace",
      "timeout": 300
    }
  }
}
```

## 📝 使用示例

### 示例 1: 代码审查

```bash
# OpenClaw 调用 Kimi 审查代码
kimi "审查这个 PR 的代码质量，找出潜在问题"
```

### 示例 2: Bug 修复

```bash
# 描述 bug，让 Kimi 修复
kimi "修复内存泄漏问题，在 src/memory/store.ts 第 130 行"
```

### 示例 3: 功能实现

```bash
# 实现新功能
kimi "添加用户注册 API，包含邮箱验证和密码加密"
```

### 示例 4: 项目理解

```bash
# 让 Kimi 分析项目结构
kimi "解释这个项目的架构和模块划分"
```

## 🧠 与记忆系统集成

### 自动保存决策

```bash
# Kimi 完成任务后，保存到 LanceDB
# 使用 OpenClaw memory_store 工具
memory_store(
  text="Kimi 实现了用户认证模块，使用 JWT token",
  category="decision",
  importance=0.8
)
```

### 检索项目知识

```bash
# 在开始任务前，检索相关记忆
memory_recall(query="用户认证实现")
# → 获取之前的决策和上下文
```

## 🚀 高级用法

### 多 Agent 协作

```
OpenClaw (协调者)
├─ Kimi CLI (代码任务)
├─ Qwen (代码审查)
└─ LanceDB (记忆存储)
```

### 自动化工作流

```bash
# 1. Kimi 实现功能
kimi "实现登录功能"

# 2. 自动测试
pytest tests/test_login.py

# 3. 保存结果到记忆
memory_store("登录功能已完成并通过测试")

# 4. 发送通知
telegram "登录功能已实现 ✅"
```

## ⚠️ 注意事项

1. **API 配额** - Kimi CLI 使用 API，注意配额限制
2. **项目上下文** - 确保在项目目录中运行
3. **敏感信息** - 不要在对话中暴露 API Key
4. **超时设置** - 复杂任务可能需要较长时间

## 📊 最佳实践

### 1. 使用 AGENTS.md

```bash
# 在项目根目录创建 AGENTS.md
kimi "/init"

# 包含项目规范、编码风格、架构说明
# 帮助 Kimi 更好理解项目
```

### 2. 分步执行复杂任务

```bash
# ❌ 不要：一次性完成所有事
kimi "重构整个项目"

# ✅ 更好：分步骤
kimi "1. 分析当前架构"
kimi "2. 提出重构方案"
kimi "3. 逐步实施"
```

### 3. 保存重要决策

```bash
# 每次重要修改后保存到记忆
memory_store(
  text="重构方案：将 monolithic 拆分为微服务",
  category="decision",
  importance=0.9
)
```

## 🔗 相关资源

- [Kimi CLI 文档](https://www.kimi.com/code/docs/kimi-cli/)
- [ACP 协议](https://agentclientprotocol.com/)
- [OpenClaw 文档](https://docs.openclaw.ai)

---

*最后更新：2026-03-13*
