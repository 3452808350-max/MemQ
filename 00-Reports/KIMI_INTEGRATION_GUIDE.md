# 🚀 OpenClaw + Kimi CLI 集成指南

> 让 OpenClaw 控制 Kimi CLI 执行代码任务

---

## 📋 目录

1. [快速开始](#快速开始)
2. [配置](#配置)
3. [使用方法](#使用方法)
4. [高级功能](#高级功能)
5. [与记忆系统集成](#与记忆系统集成)
6. [故障排除](#故障排除)

---

## 🎯 快速开始

### 1. 验证安装

```bash
# 检查 Kimi CLI
kimi --version
# ✅ kimi, version 1.12.0

# 检查 OpenClaw
openclaw status
```

### 2. 登录 Kimi

```bash
kimi /login
# 选择 Kimi Code 平台
# 自动打开浏览器进行 OAuth 授权
```

### 3. 测试集成

```bash
# 使用控制脚本
cd /home/kyj/.openclaw/workspace
python3 kimi_controller.py --status

# 执行简单任务
python3 kimi_controller.py "帮我写一个 Hello World Python 程序"
```

---

## ⚙️ 配置

### Kimi CLI 配置

**配置文件位置**: `~/.kimi-cli/config.json`

```json
{
  "provider": "kimi-code",
  "model": "kimi-k2.5",
  "timeout": 300,
  "workdir": "/home/kyj/.openclaw/workspace"
}
```

### OpenClaw 配置

在 `openclaw.json` 中添加 Kimi 工具配置：

```json
{
  "tools": {
    "kimi": {
      "enabled": true,
      "command": "/home/kyj/.openclaw/workspace/kimi_tool.js",
      "timeout": 300
    }
  },
  "agents": {
    "defaults": {
      "tools": ["kimi", "memory_search", "memory_store"]
    }
  }
}
```

---

## 📖 使用方法

### 基础用法

#### 1. 简单代码任务

```bash
# Python 函数
kimi "写一个 Python 函数，计算斐波那契数列"

# JavaScript 模块
kimi "创建一个 Express.js 中间件，用于 JWT 验证"

# Bug 修复
kimi "修复内存泄漏，在 src/store.ts 第 130 行"
```

#### 2. 项目相关任务

```bash
# 切换到项目目录
cd /path/to/project
kimi "添加用户认证功能"

# 或者指定项目目录
python3 kimi_controller.py -p /path/to/project "实现登录 API"
```

#### 3. 使用斜杠命令

```bash
# 初始化项目（生成 AGENTS.md）
kimi /init

# 查看帮助
kimi /help

# 查看会话历史
kimi /history
```

### OpenClaw 集成用法

#### 方式 1: 通过控制脚本

```python
# 在 OpenClaw 会话中
exec("python3 /home/kyj/.openclaw/workspace/kimi_controller.py '写一个排序算法'")
```

#### 方式 2: 使用 ACP

```python
# 创建 ACP 会话
sessions_spawn(
    runtime="acp",
    agentId="kimi",
    task="实现用户注册功能",
    cwd="/path/to/project"
)
```

#### 方式 3: 直接调用 Kimi CLI

```python
# 直接执行 kimi 命令
exec("kimi '帮我审查这个 PR 的代码质量'")
```

---

## 🔧 高级功能

### 1. 多 Agent 协作

```
OpenClaw (协调者)
├─ Kimi CLI (代码实现)
├─ Qwen (代码审查)
└─ LanceDB (记忆存储)
```

**工作流示例**:

```bash
# 1. Kimi 实现功能
kimi "实现用户登录功能，包含密码加密和 JWT token"

# 2. Qwen 审查代码
# (通过 OpenClaw 调用其他 Agent)

# 3. 运行测试
pytest tests/test_login.py

# 4. 保存决策到记忆
memory_store(
    text="登录功能使用 bcrypt 加密密码，JWT token 有效期 24 小时",
    category="decision",
    importance=0.9
)
```

### 2. 项目初始化

```bash
# 生成 AGENTS.md（项目规范文件）
kimi /init

# AGENTS.md 包含:
# - 项目结构
# - 编码规范
# - 技术栈说明
# - 常见问题
```

### 3. 批量任务

```bash
# 创建任务列表
cat > tasks.json << 'EOF'
[
  {"task": "创建用户模型", "priority": "high"},
  {"task": "实现认证中间件", "priority": "high"},
  {"task": "编写单元测试", "priority": "medium"},
  {"task": "更新 API 文档", "priority": "low"}
]
EOF

# 批量执行
python3 kimi_batch_runner.py tasks.json
```

---

## 🧠 与记忆系统集成

### 自动保存决策

```python
# Kimi 完成任务后
def save_kimi_result(task, result):
    memory_store(
        text=f"Kimi 完成了：{task}",
        category="decision",
        importance=0.8,
        tags=["kimi", "code-task"],
        metadata={
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    )
```

### 检索项目知识

```python
# 开始新任务前，检索相关记忆
def prepare_context(task):
    # 检索类似任务
    related = memory_recall(query=task, limit=5)
    
    # 提取关键信息
    context = "\n".join([m.text for m in related])
    
    # 提供给 Kimi
    return f"""
    项目上下文:
    {context}
    
    新任务：{task}
    """
```

### 记忆分类

```python
# 代码实现
memory_store(
    text="实现了用户认证模块，使用 JWT + bcrypt",
    category="fact",
    importance=0.8
)

# 架构决策
memory_store(
    text="选择 PostgreSQL 而非 MongoDB，因为需要事务支持",
    category="decision",
    importance=0.9
)

# 用户偏好
memory_store(
    text="K 偏好使用 TypeScript 而非 JavaScript",
    category="preference",
    importance=0.7
)
```

---

## 📊 最佳实践

### 1. 使用 AGENTS.md

```bash
# 在每个项目根目录创建 AGENTS.md
kimi /init

# 包含内容:
# - 项目目标
# - 技术栈
# - 目录结构
# - 编码规范
# - 测试要求
```

### 2. 分步执行复杂任务

```bash
# ❌ 不要
kimi "重构整个项目"

# ✅ 更好
kimi "1. 分析当前架构问题"
kimi "2. 提出重构方案"
kimi "3. 创建迁移计划"
kimi "4. 逐步实施"
```

### 3. 保存重要上下文

```bash
# 每次重要修改后
memory_store(
    text="重构：将 monolithic 拆分为微服务架构",
    category="decision",
    importance=0.9,
    tags=["architecture", "refactoring"]
)
```

### 4. 设置合适的超时

```bash
# 简单任务：60 秒
kimi "写一个工具函数"

# 复杂任务：300 秒
kimi --timeout 300 "实现完整的认证系统"

# 大型重构：600 秒
kimi --timeout 600 "重构数据库层"
```

---

## ⚠️ 故障排除

### 问题 1: Kimi CLI 未安装

```bash
# 解决方案
curl -LsSf https://code.kimi.com/install.sh | bash

# 验证
kimi --version
```

### 问题 2: API 认证失败

```bash
# 重新登录
kimi /login

# 选择 Kimi Code 平台
# 完成 OAuth 授权
```

### 问题 3: 任务超时

```bash
# 增加超时时间
kimi --timeout 600 "复杂任务"

# 或者分步执行
kimi "第一步..."
kimi "第二步..."
```

### 问题 4: 项目上下文丢失

```bash
# 确保在项目目录中运行
cd /path/to/project
kimi "任务"

# 或者使用 AGENTS.md
kimi /init
```

### 问题 5: 记忆系统未集成

```bash
# 检查 LanceDB 配置
openclaw memory stats

# 确保插件已启用
cat ~/.openclaw/openclaw.json | grep memory-lancedb-pro
```

---

## 🔗 相关资源

- [Kimi CLI 官方文档](https://www.kimi.com/code/docs/kimi-cli/)
- [ACP 协议](https://agentclientprotocol.com/)
- [OpenClaw 文档](https://docs.openclaw.ai)
- [LanceDB 记忆系统](./memory-lancedb-pro/README_CN.md)

---

## 📝 示例项目

### 示例 1: Web 应用开发

```bash
# 1. 初始化项目
mkdir my-web-app && cd my-web-app
kimi /init

# 2. 实现功能
kimi "创建 Express.js 项目结构"
kimi "添加用户认证中间件"
kimi "实现 REST API"

# 3. 保存决策
memory_store "使用 Express + JWT + PostgreSQL", category="decision"
```

### 示例 2: 数据分析脚本

```bash
# 1. 创建脚本
kimi "写一个 Python 脚本，分析 CSV 数据并生成图表"

# 2. 运行测试
python3 analyze.py

# 3. 保存结果
memory_store "数据分析脚本使用 pandas + matplotlib", category="fact"
```

### 示例 3: Bug 修复

```bash
# 1. 描述 bug
kimi "修复内存泄漏，在 src/memory/store.ts 第 130 行"

# 2. 验证修复
npm test

# 3. 记录教训
memory_store "Bug 原因：未关闭数据库连接", category="decision", importance=0.8
```

---

*最后更新：2026-03-13*
*版本：1.0*
