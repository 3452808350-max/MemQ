# OpenClaw Agent 交互框架

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    主会话 (Main Session)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  主 Agent (你 / Kaguya)                              │   │
│  │  - 接收用户消息                                       │   │
│  │  - 决策任务分配                                       │   │
│  │  - 协调 Sub-Agent                                     │   │
│  │  - 整合结果返回用户                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                   │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Sub-Agent 管理层                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │ Sub-Agent 1 │  │ Sub-Agent 2 │  │ Sub-Agent N │  │   │
│  │  │ (任务A)     │  │ (任务B)     │  │ (任务C)     │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 两种 Sub-Agent 类型

### 1. 标准 Sub-Agent (`runtime: "subagent"`)

用于一般性任务委托，如研究、分析、代码审查等。

```javascript
// 创建
sessions_spawn({
  runtime: "subagent",
  task: "分析这段代码的性能瓶颈",
  mode: "run"        // 一次性任务
  // mode: "session"  // 持久会话（线程绑定）
})

// 管理
subagents({ action: "list" })     // 列出活跃 Sub-Agent
subagents({ action: "kill", target: "<id>" })   // 终止
subagents({ action: "steer", target: "<id>", message: "..." })  // 干预
```

### 2. ACP 编码 Agent (`runtime: "acp"`)

用于编码任务，支持 Codex、Claude Code、Gemini 等 harness。

```javascript
// 创建
sessions_spawn({
  runtime: "acp",
  agentId: "codex",      // 或 "claude-code", "gemini", etc.
  task: "实现用户认证模块",
  mode: "session",       // 编码任务通常用持久会话
  thread: true,          // Discord 等平台绑定到线程
  cwd: "./project"       // 工作目录
})

// ACP Agent 自动继承父目录，独立执行
// 完成后自动推送结果到主会话
```

---

## 交互模式

### 模式一：Fire-and-Forget（推模式）

```
用户请求 → 主 Agent 判断需要子任务 → 启动 Sub-Agent
                                            ↓
用户 ←── 主 Agent 继续处理其他事 ←── 完成推送 (自动)
```

**特点：**
- Sub-Agent 完成后自动推送结果到主会话
- 主 Agent 无需轮询等待
- 适合耗时较长的独立任务

**示例：**
```javascript
// 启动一个代码审查任务
sessions_spawn({
  runtime: "subagent",
  task: "审查 src/ 目录下的所有代码，找出潜在bug",
  mode: "run"
})

// 立即返回，不等待
// 完成后结果自动出现在主会话
```

### 模式二：同步等待（拉模式）

```
用户请求 → 主 Agent 启动 Sub-Agent → 等待完成
                                            ↓
用户 ←── 主 Agent 整合结果 ←── 查询状态/结果
```

**特点：**
- 主 Agent 需要结果才能继续
- 使用 `runTimeoutSeconds` 或手动查询
- 适合需要顺序执行的依赖任务

**示例：**
```javascript
// 启动并等待
const result = await sessions_spawn({
  runtime: "subagent",
  task: "生成API文档",
  mode: "run",
  runTimeoutSeconds: 60
})

// 使用结果继续
const summary = `文档已生成: ${result.output}`
```

### 模式三：持久会话协作

```
用户 ──→ 主 Agent ──→ 创建 ACP Session (thread: true)
                          ↓
                    持续交互，多轮对话
                          ↓
                    自动或手动结束
```

**特点：**
- 用于复杂编码任务的多轮迭代
- Discord 等平台自动创建线程
- 用户可直接在线程中与 ACP Agent 交互

**示例：**
```javascript
// Discord 中创建 Claude Code 线程
sessions_spawn({
  runtime: "acp",
  agentId: "claude-code",
  task: "帮我重构这个React项目",
  mode: "session",
  thread: true,
  cwd: "./my-react-app"
})

// 结果：Discord 中创建新线程，用户可在其中与 Claude Code 直接对话
```

---

## 关键工具对比

| 工具 | 用途 | 何时使用 |
|------|------|----------|
| `sessions_spawn` | 创建 Sub-Agent | 启动新任务 |
| `subagents` | 管理 Sub-Agent | 列出、终止、干预 |
| `sessions_list` | 查看所有会话 | 检查活跃任务 |
| `sessions_send` | 发送消息到指定会话 | 跨会话通信 |
| `sessions_history` | 获取会话历史 | 查看 Sub-Agent 做了什么 |

---

## 最佳实践

### ✅ 应该做的

1. **任务分解清晰**
   - 一个 Sub-Agent 负责一个明确的子任务
   - 避免一个 Sub-Agent 做太多不相关的事

2. **善用 Fire-and-Forget**
   - 耗时任务启动后不要轮询等待
   - 让 Sub-Agent 完成后自动推送

3. **ACP 任务用 `thread: true`**
   - Discord 等平台自动创建线程
   - 用户可以直接参与编码过程

4. **设置合理的超时**
   - `runTimeoutSeconds` 防止无限等待
   - 编码任务可以给更长超时

5. **记录 Sub-Agent 输出**
   - 重要结果写入 memory/ 文件
   - 便于后续查询和审计

### ❌ 避免做的

1. **不要频繁轮询 `subagents list`**
   - 推模式已经处理了完成通知
   - 轮询浪费资源

2. **不要让 Sub-Agent 处理敏感操作**
   - 外部发送（邮件、推文）保持主 Agent 控制
   - 需要用户确认的操作留在主会话

3. **不要创建过多并发 Sub-Agent**
   - 资源有限，合理排队
   - 大批量任务考虑串行化

4. **不要在 ACP 中混用 `message` 创建线程**
   - 用 `sessions_spawn` 的 `thread: true` 是单一路径
   - 混用会导致线程混乱

---

## 典型工作流示例

### 场景：GitHub Issue 自动化

```
用户: "处理前5个bug标签的issue"

主 Agent:
  1. 调用 gh-issues skill 获取issue列表
  2. 对每个issue:
     - sessions_spawn({
         runtime: "acp",
         agentId: "claude-code",
         task: "修复issue #XXX: ...",
         mode: "run"
       })
  3. 等待推送结果
  4. 整合所有PR链接返回用户
```

### 场景：多源数据收集

```
用户: "搜集关于X的最新信息"

主 Agent:
  1. 启动3个Sub-Agent并行:
     - Sub-Agent A: web_search 搜集新闻
     - Sub-Agent B: web_fetch 获取深度文章
     - Sub-Agent C: 分析已有文档
  2. 各自完成后自动推送
  3. 主 Agent 整合成报告
```

### 场景：代码审查 + 修复

```
用户: "审查并修复这段代码"

主 Agent:
  1. sessions_spawn({
       runtime: "subagent",
       task: "审查代码问题",
       mode: "run"
     })
  2. 收到审查报告
  3. sessions_spawn({
       runtime: "acp",
       agentId: "codex",
       task: "根据审查报告修复代码",
       mode: "run"
     })
  4. 返回修复后的代码
```

---

## 故障处理

| 问题 | 诊断 | 解决 |
|------|------|------|
| Sub-Agent 无响应 | `subagents({action: "list"})` | `subagents({action: "kill"})` 后重试 |
| ACP 线程未创建 | 检查 `thread: true` | 确认平台支持线程 |
| 结果未推送 | `sessions_history({sessionKey})` | 检查 Sub-Agent 是否崩溃 |
| 任务超时 | 增加 `runTimeoutSeconds` | 或改为 `mode: "session"` |

---

## 附录：clawteam vs OpenClaw 框架对比

| 维度 | clawteam | OpenClaw |
|------|----------|----------|
| **定位** | 通用 AI Agent 框架 | OpenClaw 专用 Sub-Agent 系统 |
| **运行环境** | 独立进程/容器 | 同一 Gateway 内的隔离会话 |
| **启动方式** | CLI / API 调用 | `sessions_spawn` 工具调用 |
| **通信协议** | 自定义协议 | 内部消息总线（推/拉模式） |
| **生命周期** | 完全独立 | 由主会话管理（可 kill/steer） |
| **结果返回** | 回调 / Webhook | 自动推送或同步等待 |
| **工作目录** | 可任意指定 | 默认继承父目录 |
| **适用场景** | 复杂多 Agent 编排 | OpenClaw 生态内的任务委托 |

### 关键差异详解

**1. 架构层级**
```
clawteam:
  外部框架 ──→ 启动独立 Agent 进程
  适合：跨系统、跨网络的 Agent 协作

OpenClaw Sub-Agent:
  Gateway 内部 ──→ 隔离会话
  适合：同一生态内的任务分解
```

**2. 启动复杂度**
```python
# clawteam - 需要外部配置
from clawteam import Agent
agent = Agent(config={...})
agent.start()

# OpenClaw - 工具调用即可
sessions_spawn({
  runtime: "subagent",
  task: "..."
})
```

**3. 管理粒度**
- clawteam：粗粒度，Agent 是黑盒
- OpenClaw：细粒度，可 `list`/`kill`/`steer`/`history`

**4. 集成深度**
- clawteam：松耦合，通过 API 交互
- OpenClaw：紧耦合，共享 memory/文件系统/配置

### 何时用哪个

| 场景 | 推荐 |
|------|------|
| 纯 OpenClaw 生态内的任务 | OpenClaw Sub-Agent |
| 需要调用外部工具/服务 | clawteam |
| 多框架混合编排 | clawteam |
| 快速启动、快速迭代 | OpenClaw Sub-Agent |
| 需要细粒度生命周期管理 | OpenClaw Sub-Agent |
| 跨网络/跨机器的 Agent | clawteam |

### 混合使用模式

```
用户请求
    ↓
主 Agent (OpenClaw)
    ↓
判断任务类型
    ↓
    ├─→ 内部任务 ──→ OpenClaw Sub-Agent
    │
    └─→ 外部任务 ──→ clawteam Agent
                          ↓
                    调用外部 API/服务
                          ↓
                    返回结果给主 Agent
```

---

## 总结

**核心原则：**
- 主 Agent 是协调者，Sub-Agent 是执行者
- 推模式优先，避免轮询
- ACP 编码任务用线程绑定
- 敏感操作留在主会话
- OpenClaw 生态内优先用内置 Sub-Agent

**记忆锚点：**
- `sessions_spawn` = 启动
- `subagents` = 管理
- `thread: true` = Discord 线程
- Fire-and-forget = 高效
- clawteam = 外部编排，OpenClaw Sub-Agent = 内部分解
