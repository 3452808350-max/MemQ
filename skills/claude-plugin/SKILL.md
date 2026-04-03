---
name: claude-plugin
description: |
  Claude Code 多 Agent 架构插件，替代原有的 subagent-mode 和 coding-agent。
  提供 Coordinator Mode 四阶段工作流、Fork Subagent 并行执行、Permission System 权限控制。
triggers:
  - /claude
  - /coordinator
  - /coord
  - /fork
  - /agent
  - "使用协调器"
  - "用子代理"
  - "并行调查"
disable-model-invocation: false
---

# Claude Plugin for OpenClaw

## 概述

Claude Plugin 将 Claude Code 的多 Agent 架构移植到 OpenClaw，替代原有的 `subagent-mode` 和 `coding-agent` skills，提供更强大的多 Agent 协调能力。

### 核心模块

| 模块 | 功能 | 替代的原功能 |
|------|------|-------------|
| **Agent Definitions** | Agent 类型定义系统 | - |
| **Fork Subagent** | 轻量级并行子代理 | `sessions_spawn` 基础调用 |
| **Task Notification** | 任务状态通知协议 | - |
| **Message Passing** | Agent 间消息传递 | `sessions_send` |
| **Coordinator Mode** | 四阶段工作流编排 | `subagent-mode` skill |
| **Permission System** | 7 种权限模式 | `coding-agent` 的权限控制 |
| **Decision Engine** | Continue vs Spawn 智能决策 | - |

---

## 快速开始

### 1. Coordinator Mode（复杂任务）

自动执行四阶段工作流：Research → Synthesis → Implementation → Verification

```
/coordinator 实现一个 OAuth2 认证系统
```

**选项**:
- `--max-workers N` - 最大并行 Worker 数（默认 4）
- `--timeout N` - 超时时间秒数（默认 300）
- `--no-verify` - 跳过验证阶段

**示例**:
```
/coordinator 重构用户管理模块 --max-workers 6 --timeout 600
```

### 2. Fork 模式（并行调查）

同时执行多个独立任务，结果汇总

```
/fork 调查认证流程; 分析会话管理; 检查权限控制
```

**适用场景**:
- 需要同时调查多个方面
- 任务之间无依赖关系
- 需要快速收集信息

### 3. 特定 Agent（专用工具）

使用预定义的 Agent 类型执行特定任务

```
/agent code-explorer 调查 src/auth 目录结构
/agent code-planner 设计新的 API 架构
/agent implementer 实现用户注册功能
/agent verifier 验证登录流程
```

---

## Agent 类型参考

### 内置 Agents

| Agent | 用途 | 工具集 | 特点 |
|-------|------|--------|------|
| `code-explorer` | 代码库探索 | Read, Grep, Glob, Bash | 只读，快速调查 |
| `code-planner` | 架构规划 | Read, Grep, Glob | 分析设计，不修改代码 |
| `implementer` | 代码实现 | Read, Write, Edit, Bash | 全功能编码 |
| `verifier` | 验证测试 | Read, Bash | 验证和测试 |
| `security-reviewer` | 安全审查 | Read, Grep | 安全检查 |

### 自定义 Agents

在 `~/.openclaw/agents/` 目录创建 Agent 定义文件：

**my-agent.md**:
```yaml
---
agent_type: custom
name: my-agent
description: 我的自定义 Agent
model: inherit
max_turns: 100
permission_mode: bubble
tools:
  allow: [Read, Write, Bash]
  deny: [Browser, Canvas]
---

你是专门处理 xxx 的 Agent。

任务规则：
1. 只处理指定范围内的任务
2. 修改前必须确认
3. 完成后提交代码
```

---

## 权限模式

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| `default` | 默认权限，每次操作询问 | 一般开发 |
| `plan` | 只读规划模式 | 调查分析 |
| `bubble` | 隔离沙箱模式 | 安全执行 |
| `auto` | 自动批准低风险操作 | 信任环境 |
| `acceptEdits` | 自动接受文件编辑 | 快速迭代 |
| `bypassPermissions` | 绕过权限检查 | ⚠️ 危险 |
| `dontAsk` | 不询问直接执行 | ⚠️ 危险 |

---

## 与原 Skill 的对比

### 替代 `subagent-mode`

| 原方式 | 新方式 | 优势 |
|--------|--------|------|
| `/subagent 研究...` | `/coordinator 研究...` | 四阶段工作流，更系统 |
| `/subagent 并行...` | `/fork 任务1; 任务2` | 更清晰的并行语法 |
| 自动分配 researcher/analyst/writer | 显式 Agent 类型 | 更可控 |

### 替代 `coding-agent`

| 原方式 | 新方式 | 优势 |
|--------|--------|------|
| `coding-agent` skill | `/coordinator` + implementer | 更完整的工作流 |
| 直接调用 Claude Code | 通过 Coordinator 编排 | 更好的任务分解 |

---

## 工作流示例

### 示例 1：新功能开发

```
# 1. 探索现有代码
/agent code-explorer 调查当前的认证实现

# 2. 规划架构
/agent code-planner 设计 OAuth2 集成方案

# 3. 实现功能（Coordinator 自动编排）
/coordinator 实现 OAuth2 登录功能

# 4. 验证
/agent verifier 验证 OAuth2 流程
```

### 示例 2：代码审查

```
# 并行审查多个方面
/fork 检查安全漏洞; 分析性能影响; 验证测试覆盖
```

### 示例 3：Bug 修复

```
# Coordinator 自动处理
/coordinator 修复登录超时问题
```

---

## 配置

在 `AGENTS.md` 中添加：

```yaml
claude_plugin:
  coordinator:
    max_parallel_workers: 4
    default_timeout_ms: 300000
    enable_verification: true
  default_permission_mode: bubble
  
  # Agent 定义目录
  agents_dir: ~/.openclaw/agents
```

---

## 架构图

```
用户输入
    │
    ├─→ /coordinator ──→ Coordinator Mode
    │                      ├─→ Research Workers (并行)
    │                      ├─→ Synthesis (Coordinator)
    │                      ├─→ Implementation Workers
    │                      │     └─→ [Decision Engine] Continue vs Spawn?
    │                      └─→ Verification Workers
    │                           └─→ [Decision Engine] 必须 Spawn (fresh eyes)
    │
    ├─→ /fork ─────────→ Fork Subagent
    │                      └─→ 并行执行多个 Worker
    │
    └─→ /agent ────────→ 特定 Agent
                           └─→ 预定义工具集和 Prompt
    
    所有路径最终调用 OpenClaw sessions_spawn
```

---

## Continue vs Spawn 决策引擎

### 核心原则

Claude Code 最佳实践：智能决定何时复用 Worker（Continue）vs 派生新 Worker（Spawn）。

### 决策场景

| 场景 | 决策 | 原因 |
|------|------|------|
| **Worker 已有文件** | Continue | Worker 已有相关文件上下文 |
| **探索广实现窄** | Spawn | 避免探索阶段的上下文噪音 |
| **修复失败尝试** | Continue | 保留错误上下文有助于定位 |
| **验证 Fresh Eyes** | Spawn | 验证者需要独立视角 |
| **方法错误** | Spawn | 错误上下文会污染重试 |
| **Token 阈值** | Spawn | 保持性能，避免膨胀 |

### 使用示例

```typescript
import { ContinueVsSpawnEngine, DecisionContext } from './decision-engine';

const engine = new ContinueVsSpawnEngine({ debug: true });

const context: DecisionContext = {
  currentPhase: 'explore',
  targetPhase: 'implement',
  tokenCount: 3500,
  relevantFiles: ['src/auth.ts'],
  targetFiles: ['src/auth.ts'],
  researchScope: 'broad',
  implementationScope: 'narrow',
  isRetry: false,
  previousAttemptFailed: false,
  previousApproachWasWrong: false,
  existingWorker: workerInfo,
  workerFilesInContext: ['src/auth.ts', 'src/user.ts'],
  workerJustWroteCode: false,
  workerHasErrors: false,
  isVerification: false,
  isExploration: false,
  isImplementation: true
};

const result = engine.decide(context);
// result.action: 'continue' | 'spawn'
// result.reason: '探索范围广但实现范围窄，避免上下文噪音'
// result.confidence: 0.85
```

### 快速决策

```typescript
import { quickDecide } from './decision-engine';

const result = quickDecide('explore', 'implement', existingWorker);
// 自动分析并返回决策
```

---

## 故障排除

### 子代理没有返回结果

- 检查 `runTimeoutSeconds` 是否足够
- 使用 `streamTo: 'parent'` 查看实时输出

### 权限被拒绝

- 检查 `permission_mode` 设置
- 使用 `bubble` 模式在沙箱中执行

### Agent 未找到

- 确认 Agent 文件在 `~/.openclaw/agents/` 目录
- 检查文件名和 `name` 字段匹配

---

## 迁移指南

从原有 Skill 迁移：

| 旧命令 | 新命令 |
|--------|--------|
| `/subagent 研究...` | `/coordinator 研究...` |
| `/subagent 并行...` | `/fork 任务1; 任务2` |
| `coding-agent` 自动触发 | `/coordinator` 或 `/agent implementer` |

---

*基于 Claude Code 多 Agent 架构 | 46 个测试覆盖 | Commit 3156f72*
