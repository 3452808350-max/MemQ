# Claude Code 最佳实践分析 - OpenClaw 集成建议

## 执行摘要

基于对 Claude Code 源代码的深度分析，本文档提取了 5 个核心最佳实践领域，并提供具体的 OpenClaw 集成建议。

---

## 1. 上下文管理最佳实践（/clear, /compact, /btw）

### 1.1 Claude Code 实现机制

#### Token 预算分配策略
| 分配项 | 比例 | 用途 |
|--------|------|------|
| System Prompt | 15% | 身份定义、能力描述 |
| Tool Definitions | 10% | 工具定义 |
| Message History | 60% | 消息历史（主体） |
| Reserve | 15% | 预留空间 |

#### 消息优先级分层
| 优先级 | 级别 | 消息类型 | 处理策略 |
|--------|------|----------|----------|
| CRITICAL | 1 | 系统消息、错误消息 | 始终保留 |
| HIGH | 2 | 用户指令、工具调用 | 高优先保留 |
| MEDIUM | 3 | 工具输出、Agent 响应 | 可转摘要 |
| LOW | 4 | 元数据、状态信息 | 可丢弃 |
| EPHEMERAL | 5 | 临时信息 | 优先丢弃 |

#### 上下文截断触发条件
- **WARNING**: 75% 使用率 → 开始监控
- **CRITICAL**: 90% 使用率 → 强制执行摘要
- **TRUNCATION**: 95% 使用率 → 触发强制截断

#### /compact 命令实现
```typescript
// services/compact/compact.ts
export async function compactConversation(context: Context): Promise<CompactResult> {
  // 1. 保存当前文件状态
  const preCompactReadFileState = cacheToObject(context.readFileState)
  
  // 2. 清空文件缓存
  context.readFileState.clear()
  
  // 3. 生成对话摘要
  const summary = await generateSummary(context.messages)
  
  // 4. 恢复最近的文件（最多 5 个，每个最多 5000 tokens）
  const restoredFiles = await createPostCompactFileAttachments(
    preCompactReadFileState,
    context,
    POST_COMPACT_MAX_FILES_TO_RESTORE, // 5
    preservedMessages
  )
  
  return { summary, restoredFiles }
}
```

### 1.2 OpenClaw 集成建议

#### 建议 1.1: 增强 LCM 优先级分层
- 为 LCM 摘要添加优先级标记 (CRITICAL/HIGH/MEDIUM/LOW/EPHEMERAL)
- 在达到 90% 阈值时自动触发摘要
- /compact 后自动恢复最近读取的文件

#### 建议 1.2: 添加上下文管理命令
```yaml
# ~/.openclaw/commands/context.yaml
commands:
  clear:
    description: "Clear conversation history, keep system prompt"
    action: context_clear
    confirm: true
    
  compact:
    description: "Compact conversation into summary"
    action: context_compact
    options:
      preserve_files: 5
      max_tokens_per_file: 5000
```

#### 建议 1.3: 与 memory-lancedb-pro 协同
在上下文压缩时自动存储到长期记忆，实现短期上下文与长期记忆的无缝衔接。

---

## 2. 四阶段工作流（Explore → Plan → Implement → Commit）

### 2.1 Claude Code Coordinator Mode 架构

```
┌─────────────────────────────────────────┐
│           Coordinator                   │
│  ┌─────────────────────────────────┐    │
│  │  System Prompt (6 章节)         │    │
│  └─────────────────────────────────┘    │
│                    │                    │
│  ┌─────────────────┼─────────────────┐  │
│  ▼                 ▼                 ▼  │
│ Worker 1       Worker 2       Worker 3  │
│ (Research)    (Research)    (Research)  │
│     │              │              │     │
│     └──────────────┼──────────────┘     │
│                    ▼                    │
│              Coordinator                │
│           (Synthesis Phase)             │
│                    │                    │
│  ┌─────────────────┼─────────────────┐  │
│  ▼                 ▼                 ▼  │
│ Worker 4       Worker 5       Worker 6  │
│(Implementation)(Implementation)(Verify) │
└─────────────────────────────────────────┘
```

### 2.2 四阶段详细说明

| 阶段 | 执行者 | 目的 | 并行度 |
|------|--------|------|--------|
| Research | Workers (并行) | 调查代码库 | 高并行 |
| Synthesis | Coordinator | 制定实现规范 | 单线程 |
| Implementation | Workers | 执行针对性修改 | 文件级并行 |
| Verification | Workers | 验证修改有效 | 可并行 |

### 2.3 OpenClaw 集成建议

#### 建议 2.1: 实现 Coordinator Mode Skill
```yaml
# ~/.openclaw/skills/coordinator-mode/SKILL.md
name: coordinator-mode
description: "Four-phase workflow orchestration for complex tasks"
triggers:
  - pattern: "/coordinator"
  - pattern: "/orchestrate"

workflow:
  phases:
    - research: "Spawn parallel subagents to investigate"
    - synthesis: "Analyze findings and create plan"
    - implementation: "Execute changes"
    - verification: "Verify results"
```

#### 建议 2.2: Continue vs Spawn 决策矩阵

| 场景 | 决策 | 原因 |
|------|------|------|
| 研究文件正好是需编辑的文件 | Continue | Worker 已有文件上下文 |
| 研究广泛但实现狭窄 | Spawn | 避免探索噪音 |
| 纠正失败或扩展最近工作 | Continue | Worker 有错误上下文 |
| 验证其他 worker 的代码 | Spawn | 验证者应有新鲜视角 |
| 第一次实现完全错误 | Spawn | 错误上下文污染重试 |
| 完全不相关的任务 | Spawn | 无有用上下文可重用 |

---

## 3. 子代理使用模式（Continue vs Spawn 决策）

### 3.1 Fork Subagent 机制

#### FORK_PLACEHOLDER_RESULT 设计
```typescript
const FORK_PLACEHOLDER_RESULT = 'Fork started — processing in background'

// 所有 fork 子进程使用相同的 tool_result 内容
// 确保 API 请求的 prefix 字节一致，最大化 prompt cache 命中率
```

#### 上下文继承配置
```typescript
interface ForkContextConfig {
  inheritFiles: boolean        // 默认：true
  inheritEnv: boolean          // 默认：true
  inheritGitStatus: boolean    // 默认：true
  messageHistoryCount: number  // 默认：0 (Fork 不继承消息历史)
}
```

### 3.2 OpenClaw 集成建议

#### 建议 3.1: 实现 Fork Subagent 缓存优化
- 使用统一的占位符结果确保 prompt cache 命中
- 克隆文件状态缓存避免并发修改
- 子 Agent 默认不修改父进程状态

#### 建议 3.2: 决策流程实现
```typescript
function decideContinueOrSpawn(context: TaskContext): 'continue' | 'spawn' {
  // 场景 1: Worker 有精确文件在上下文中
  if (context.researchFiles === context.targetFiles) {
    return 'continue'
  }
  
  // 场景 2: 研究广泛但实现狭窄
  if (context.researchScope === 'broad' && context.implementationScope === 'narrow') {
    return 'spawn'
  }
  
  // 场景 3: 纠正失败
  if (context.isRetry && context.previousAttemptFailed) {
    return 'continue'
  }
  
  // 场景 4: 验证刚写的代码
  if (context.isVerification && context.targetWorkerJustWroteCode) {
    return 'spawn'
  }
  
  // 默认：Spawn fresh
  return 'spawn'
}
```

---

## 4. 工具权限控制（7 种 permission modes）

### 4.1 Claude Code 权限模式

```typescript
type PermissionMode =
  | 'default'           // 默认：所有敏感操作需确认
  | 'plan'              // 计划模式：只读，不执行
  | 'acceptEdits'       // 自动接受文件编辑
  | 'bypassPermissions' // 绕过所有权限（危险）
  | 'dontAsk'           // 不询问，但保留安全检查
  | 'auto'              // 自动分类器模式（实验性）
  | 'bubble'            // 权限提示冒泡到父 Agent（Fork 专用）
```

### 4.2 权限决策流程
```typescript
checkPermission(toolName, input, context): PermissionDecision {
  // 1. 检查模式覆盖
  if (mode === 'bypassPermissions') return ALLOW
  
  if (mode === 'plan') {
    if (!isReadOnlyTool(toolName)) return DENY
  }
  
  // 2. 检查 deny 规则
  if (matchesDenyRule(toolName, input)) return DENY
  
  // 3. 检查 allow 规则
  if (matchesAllowRule(toolName, input)) return ALLOW
  
  // 4. 检查 ask 规则
  if (matchesAskRule(toolName, input)) return ASK
  
  // 5. 默认行为
  return getDefaultDecision(toolName)
}
```

### 4.3 OpenClaw 集成建议

#### 建议 4.1: 实现 Permission System Skill
```yaml
# ~/.openclaw/skills/permission-system/SKILL.md
name: permission-system
description: "Flexible permission control with 7 modes"

modes:
  default: "All sensitive operations require confirmation"
  plan: "Read-only mode, no execution"
  acceptEdits: "Auto-accept file edits"
  bypassPermissions: "Bypass all permissions (DANGEROUS)"
  dontAsk: "Don't ask, but keep safety checks"
  auto: "Auto-classifier mode (experimental)"
  bubble: "Permission prompts bubble to parent Agent"
```

#### 建议 4.2: Agent 工具过滤
```typescript
function filterToolsForAgent(tools, agentDef, isAsync): Tool[] {
  // MCP 工具对所有 Agent 开放
  if (tool.name.startsWith('mcp__')) return true
  
  // Plan 模式特殊处理
  if (tool.name === 'ExitPlanMode' && agentDef.permissionMode === 'plan') {
    return true
  }
  
  // 所有 Agent 禁止的工具
  if (ALL_AGENT_DISALLOWED_TOOLS.has(tool.name)) return false
  
  // 异步 Agent 限制
  if (isAsync && !ASYNC_AGENT_ALLOWED_TOOLS.has(tool.name)) {
    return false
  }
  
  return true
}
```

---

## 5. 验证驱动开发（给 Claude 验证手段）

### 5.1 Claude Code Verification Loop

#### 6 阶段验证流程
| 阶段 | 检查项 | 工具 |
|------|--------|------|
| Build | 项目构建 | npm run build |
| Types | 类型检查 | tsc --noEmit / pyright |
| Lint | 代码规范 | eslint / ruff |
| Tests | 测试套件 | npm test --coverage |
| Security | 安全检查 | grep secrets, console.log |
| Diff | 变更审查 | git diff --stat |

### 5.2 OpenClaw 集成建议

#### 建议 5.1: 实现 Verification Skill
```yaml
# ~/.openclaw/skills/verification-loop/SKILL.md
name: verification-loop
description: "Comprehensive verification system"

phases:
  - build: "Check if project builds"
  - types: "TypeScript/Python type check"
  - lint: "Lint check"
  - tests: "Run test suite with coverage"
  - security: "Security scan for secrets"
  - diff: "Review git diff"

output:
  format: |
    VERIFICATION REPORT
    ==================
    Build:     [PASS/FAIL]
    Types:     [PASS/FAIL] (X errors)
    Lint:      [PASS/FAIL] (X warnings)
    Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
    Security:  [PASS/FAIL] (X issues)
    Diff:      [X files changed]
    Overall:   [READY/NOT READY] for PR
```

#### 建议 5.2: 与 PostToolUse Hooks 协同
- Hooks 即时捕获问题
- Verification Loop 提供全面审查
- 两者互补形成完整质量保障

---

## 6. 总结与优先级建议

### 6.1 实施优先级

| 优先级 | 模块 | 复杂度 | 价值 |
|--------|------|--------|------|
| P0 | Permission System | 中 | 高 |
| P0 | Verification Loop | 低 | 高 |
| P1 | Coordinator Mode | 高 | 高 |
| P1 | Context Management | 中 | 中 |
| P2 | Fork Subagent Optimization | 中 | 中 |

### 6.2 关键设计原则

1. **Cache 优先**: Fork Subagent 使用相同 placeholder 确保 prompt cache 命中
2. **隔离可变状态**: 子 Agent 默认不修改父进程状态
3. **自包含 Prompt**: Coordinator Worker 的 prompt 必须包含所有必要上下文
4. **结构化通信**: Agent 间使用结构化 JSON/XML 消息
5. **优先级分层**: 关键消息始终保留，低优先级消息摘要或丢弃

### 6.3 与现有 OpenClaw 组件的协同

| Claude Code 组件 | OpenClaw 对应组件 | 协同方式 |
|-----------------|------------------|---------|
| Token Budget | Context Manager (已有) | 增强优先级分层 |
| Fork Subagent | subagents 系统 | 添加缓存优化 |
| Coordinator Mode | /subagent 模式 | 实现四阶段工作流 |
| Permission System | 待实现 | 新增 Skill |
| Verification Loop | 待实现 | 新增 Skill |
| LCM | lossless-claw | 已有，增强压缩策略 |
| Memory | memory-lancedb-pro | 已有，增强协同 |

---

## 附录：相关文件索引

| 文件路径 | 主要内容 |
|---------|---------|
| `tools/AgentTool/forkSubagent.ts` | Fork Subagent 实现 |
| `utils/forkedAgent.ts` | CacheSafeParams, createSubagentContext |
| `coordinator/coordinatorMode.ts` | Coordinator Mode 系统提示 |
| `tools/SendMessageTool/SendMessageTool.ts` | SendMessage 工具 |
| `utils/task/framework.ts` | Task Notification XML |
| `utils/teammateMailbox.ts` | 邮箱系统 |
| `services/compact/compact.ts` | 上下文压缩 |
| `utils/readFileInRange.ts` | 文件读取策略 |
