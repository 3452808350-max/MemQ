# Claude Code 多 Agent 上下文管理机制分析 - 第三部分

## 概述

本部分深入分析 Claude Code 的多 Agent 上下文管理机制，包括：
1. **Fork Subagent 的上下文处理**
2. **Coordinator Mode 的上下文管理**
3. **Agent 间通信的上下文传递**

---

## 1. Fork Subagent 的上下文处理

### 1.1 FORK_PLACEHOLDER_RESULT 机制

**文件位置**: `tools/AgentTool/forkSubagent.ts`

Fork Subagent 使用一个统一的占位符结果来确保所有 fork 子进程能够共享 prompt cache：

```typescript
// tools/AgentTool/forkSubagent.ts:85
const FORK_PLACEHOLDER_RESULT = 'Fork started — processing in background'
```

**关键设计原理**:
- 所有 fork 子进程使用**完全相同**的 `tool_result` 内容
- 这使得 API 请求的 prefix 字节完全一致，从而最大化 prompt cache 命中率
- 只有最后的 directive 文本块在每个子进程中不同

### 1.2 构建 Fork 消息

```typescript
// tools/AgentTool/forkSubagent.ts:94-140
export function buildForkedMessages(
  directive: string,
  assistantMessage: AssistantMessage,
): MessageType[] {
  const fullAssistantMessage: AssistantMessage = {
    ...assistantMessage,
    uuid: randomUUID(),
    message: {
      ...assistantMessage.message,
      content: [...assistantMessage.message.content],
    },
  }

  const toolUseBlocks = assistantMessage.message.content.filter(
    (block): block is BetaToolUseBlock => block.type === 'tool_use',
  )

  const toolResultBlocks = toolUseBlocks.map(block => ({
    type: 'tool_result' as const,
    tool_use_id: block.id,
    content: [{ type: 'text' as const, text: FORK_PLACEHOLDER_RESULT }],
  }))

  const toolResultMessage = createUserMessage({
    content: [...toolResultBlocks, {
      type: 'text' as const,
      text: buildChildMessage(directive),
    }],
  })

  return [fullAssistantMessage, toolResultMessage]
}
```

**消息结构**: `[...history, assistant(all_tool_uses), user(placeholder_results..., directive)]`

### 1.3 Fork Agent 定义

```typescript
// tools/AgentTool/forkSubagent.ts:45-58
export const FORK_AGENT = {
  agentType: FORK_SUBAGENT_TYPE,
  tools: ['*'],
  maxTurns: 200,
  model: 'inherit',
  permissionMode: 'bubble',
  source: 'built-in',
  getSystemPrompt: () => '',
}
```

### 1.4 递归 Fork 防护

```typescript
// tools/AgentTool/forkSubagent.ts:61-75
export function isInForkChild(messages: MessageType[]): boolean {
  return messages.some(m => {
    if (m.type !== 'user') return false
    const content = m.message.content
    if (!Array.isArray(content)) return false
    return content.some(
      block => block.type === 'text' &&
        block.text.includes(`<${FORK_BOILERPLATE_TAG}>`)
    )
  })
}
```

---

## 2. CacheSafeParams 与上下文隔离

### 2.1 CacheSafeParams 定义

**文件位置**: `utils/forkedAgent.ts`

```typescript
export type CacheSafeParams = {
  systemPrompt: SystemPrompt
  userContext: { [k: string]: string }
  systemContext: { [k: string]: string }
  toolUseContext: ToolUseContext
  forkContextMessages: Message[]
}
```

### 2.2 创建子 Agent 上下文

```typescript
// utils/forkedAgent.ts:268-375
export function createSubagentContext(
  parentContext: ToolUseContext,
  overrides?: SubagentContextOverrides,
): ToolUseContext {
  const abortController = overrides?.abortController ??
    (overrides?.shareAbortController
      ? parentContext.abortController
      : createChildAbortController(parentContext.abortController))

  const getAppState = overrides?.getAppState ??
    (overrides?.shareAbortController
      ? parentContext.getAppState
      : () => {
          const state = parentContext.getAppState()
          return {
            ...state,
            toolPermissionContext: {
              ...state.toolPermissionContext,
              shouldAvoidPermissionPrompts: true,
            },
          }
        })

  return {
    readFileState: cloneFileStateCache(
      overrides?.readFileState ?? parentContext.readFileState
    ),
    nestedMemoryAttachmentTriggers: new Set<string>(),
    discoveredSkillNames: new Set<string>(),
    contentReplacementState: overrides?.contentReplacementState ??
      (parentContext.contentReplacementState
        ? cloneContentReplacementState(parentContext.contentReplacementState)
        : undefined),
    abortController,
    getAppState,
    setAppState: overrides?.shareSetAppState ? parentContext.setAppState : () => {},
    setAppStateForTasks: parentContext.setAppStateForTasks ?? parentContext.setAppState,
    setResponseLength: overrides?.shareSetResponseLength
      ? parentContext.setResponseLength : () => {},
    options: overrides?.options ?? parentContext.options,
    messages: overrides?.messages ?? parentContext.messages,
    agentId: overrides?.agentId ?? createAgentId(),
  }
}
```

**隔离机制**:
- `readFileState`: 克隆父进程的文件状态缓存
- `setAppState`: 默认为 no-op，防止子进程修改父进程状态
- `setAppStateForTasks`: 始终指向根存储，确保任务注册/终止正常工作
- 新建集合：`nestedMemoryAttachmentTriggers`, `discoveredSkillNames`

---

## 3. Coordinator Mode 的上下文管理

### 3.1 Coordinator Mode 检测

**文件位置**: `coordinator/coordinatorMode.ts`

```typescript
export function isCoordinatorMode(): boolean {
  if (feature('COORDINATOR_MODE')) {
    return isEnvTruthy(process.env.CLAUDE_CODE_COORDINATOR_MODE)
  }
  return false
}
```

### 3.2 Worker 工具限制

```typescript
// coordinator/coordinatorMode.ts:23-27
const INTERNAL_WORKER_TOOLS = new Set([
  TEAM_CREATE_TOOL_NAME,
  TEAM_DELETE_TOOL_NAME,
  SEND_MESSAGE_TOOL_NAME,
  SYNTHETIC_OUTPUT_TOOL_NAME,
])
```

Worker 无法使用内部工具，只能使用 `ASYNC_AGENT_ALLOWED_TOOLS` 中定义的工具。

### 3.3 Coordinator 系统提示

```typescript
// coordinator/coordinatorMode.ts:88-200+
export function getCoordinatorSystemPrompt(): string {
  return `You are Claude Code, an AI assistant that orchestrates software engineering tasks across multiple workers.

## 1. Your Role
You are a **coordinator**. Your job is to:
- Help the user achieve their goal
- Direct workers to research, implement and verify code changes
- Synthesize results and communicate with the user

## 2. Your Tools
- **Agent** - Spawn a new worker
- **SendMessage** - Continue an existing worker
- **TaskStop** - Stop a running worker

### Agent Tool Results
Worker results arrive as **user-role messages** containing \`<task-notification>\` XML.

Format:
\`\`\`xml
<task-notification>
<task-id>{agentId}</task-id>
<status>completed|failed|killed</status>
<summary>{human-readable status summary}</summary>
<result>{agent's final text response}</result>
<usage>
  <total_tokens>N</total_tokens>
  <tool_uses>N</tool_uses>
  <duration_ms>N</duration_ms>
</usage>
</task-notification>
\`\`\`

## 3. Workers
Workers can't see your conversation. Every prompt must be self-contained.

## 4. Task Workflow
| Phase | Who | Purpose |
|-------|-----|---------|
| Research | Workers (parallel) | Investigate codebase |
| Synthesis | **You** (coordinator) | Craft implementation specs |
| Implementation | Workers | Make targeted changes |
| Verification | Workers | Test changes work |

## 5. Writing Worker Prompts
**Workers can't see your conversation.** Every prompt must be self-contained with:
- Specific file paths
- Line numbers
- Error messages
- Clear "done" criteria
\`\`\`
`
}
```

### 3.4 Continue vs Spawn 决策

Coordinator 根据上下文重叠程度决定是继续现有 worker 还是创建新 worker：

| 情况 | 机制 | 原因 |
|------|------|------|
| 研究恰好覆盖需要编辑的文件 | Continue (SendMessage) | Worker 已有文件上下文 |
| 研究广泛但实现狭窄 | Spawn fresh (Agent) | 避免探索噪音 |
| 纠正失败或扩展最近工作 | Continue | Worker 有错误上下文 |
| 验证其他 worker 的代码 | Spawn fresh | 验证者应有新鲜视角 |
| 第一次实现使用了错误方法 | Spawn fresh | 错误上下文污染重试 |
| 完全不相关的任务 | Spawn fresh | 无有用上下文可重用 |

---

## 4. Agent 间通信的上下文

### 4.1 SendMessage 工具

**文件位置**: `tools/SendMessageTool/SendMessageTool.ts`

SendMessage 工具支持以下消息类型：
- 普通文本消息
- Shutdown 请求/响应
- Plan 批准/拒绝
- 广播消息

```typescript
// tools/SendMessageTool/SendMessageTool.ts:45-60
const StructuredMessage = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('shutdown_request'),
    reason: z.string().optional(),
  }),
  z.object({
    type: z.literal('shutdown_response'),
    request_id: z.string(),
    approve: semanticBoolean(),
    reason: z.string().optional(),
  }),
  z.object({
    type: z.literal('plan_approval_response'),
    request_id: z.string(),
    approve: semanticBoolean(),
    feedback: z.string().optional(),
  }),
])
```

### 4.2 Task Notification XML 格式

**文件位置**: `utils/task/framework.ts`

```typescript
// utils/task/framework.ts:195-210
function enqueueTaskNotification(attachment: TaskAttachment): void {
  const statusText = getStatusText(attachment.status)
  const outputPath = getTaskOutputPath(attachment.taskId)
  const toolUseIdLine = attachment.toolUseId
    ? `\n<${TOOL_USE_ID_TAG}>${attachment.toolUseId}</${TOOL_USE_ID_TAG}>`
    : ''
  
  const message = `<${TASK_NOTIFICATION_TAG}>
<${TASK_ID_TAG}>${attachment.taskId}</${TASK_ID_TAG}>${toolUseIdLine}
<${TASK_TYPE_TAG}>${attachment.taskType}</${TASK_TYPE_TAG}>
<${OUTPUT_FILE_TAG}>${outputPath}</${OUTPUT_FILE_TAG}>
<${STATUS_TAG}>${attachment.status}</${STATUS_TAG}>
<${SUMMARY_TAG}>Task "${attachment.description}" ${statusText}</${SUMMARY_TAG}>
</${TASK_NOTIFICATION_TAG}>`

  enqueuePendingNotification({ value: message, mode: 'task-notification' })
}
```

**完整 XML 格式**:
```xml
<task-notification>
<task-id>agent-a1b2c3d4</task-id>
<tool-use-id>tooluse_xyz789</tool-use-id>
<task-type>local_agent</task-type>
<output-file>/path/to/output.txt</output-file>
<status>completed</status>
<summary>Task "Investigate auth bug" completed successfully</summary>
</task-notification>
```

### 4.3 邮箱系统 (Mailbox)

**文件位置**: `utils/teammateMailbox.ts`

邮箱系统用于 Agent 间的异步消息传递：

```typescript
// utils/teammateMailbox.ts:70-100
export async function writeToMailbox(
  recipientName: string,
  message: Omit<TeammateMessage, 'read'>,
  teamName?: string,
): Promise<void> {
  await ensureInboxDir(teamName)
  const inboxPath = getInboxPath(recipientName, teamName)
  
  // 使用文件锁防止并发写入
  let release = await lockfile.lock(inboxPath, { lockfilePath: `${inboxPath}.lock`, ...LOCK_OPTIONS })
  
  const messages = await readMailbox(recipientName, teamName)
  const newMessage: TeammateMessage = { ...message, read: false }
  messages.push(newMessage)
  
  await writeFile(inboxPath, jsonStringify(messages, null, 2), 'utf-8')
  await release()
}
```

**邮箱文件结构**: `~/.claude/teams/{team_name}/inboxes/{agent_name}.json`

### 4.4 结构化协议消息

```typescript
// utils/teammateMailbox.ts:600-625
export function isStructuredProtocolMessage(messageText: string): boolean {
  try {
    const parsed = jsonParse(messageText)
    if (!parsed || typeof parsed !== 'object' || !('type' in parsed)) {
      return false
    }
    const type = (parsed as { type: unknown }).type
    return (
      type === 'permission_request' ||
      type === 'permission_response' ||
      type === 'sandbox_permission_request' ||
      type === 'sandbox_permission_response' ||
      type === 'shutdown_request' ||
      type === 'shutdown_approved' ||
      type === 'team_permission_update' ||
      type === 'mode_set_request' ||
      type === 'plan_approval_request' ||
      type === 'plan_approval_response'
    )
  } catch {
    return false
  }
}
```

---

## 5. AsyncLocalStorage 上下文隔离

### 5.1 AgentContext

**文件位置**: `utils/agentContext.ts`

```typescript
// utils/agentContext.ts:40-65
export type SubagentContext = {
  agentId: string
  parentSessionId?: string
  agentType: 'subagent'
  subagentName?: string
  isBuiltIn?: boolean
  invokingRequestId?: string
  invocationKind?: 'spawn' | 'resume'
  invocationEmitted?: boolean
}

export type TeammateAgentContext = {
  agentId: string
  agentName: string
  teamName: string
  agentColor?: string
  planModeRequired: boolean
  parentSessionId: string
  isTeamLead: boolean
  agentType: 'teammate'
  invokingRequestId?: string
  invocationKind?: 'spawn' | 'resume'
  invocationEmitted?: boolean
}

const agentContextStorage = new AsyncLocalStorage<AgentContext>()

export function runWithAgentContext<T>(context: AgentContext, fn: () => T): T {
  return agentContextStorage.run(context, fn)
}
```

### 5.2 TeammateContext

**文件位置**: `utils/teammateContext.ts`

```typescript
// utils/teammateContext.ts:25-45
export type TeammateContext = {
  agentId: string
  agentName: string
  teamName: string
  color?: string
  planModeRequired: boolean
  parentSessionId: string
  isInProcess: true
  abortController: AbortController
}

const teammateContextStorage = new AsyncLocalStorage<TeammateContext>()

export function runWithTeammateContext<T>(
  context: TeammateContext,
  fn: () => T,
): T {
  return teammateContextStorage.run(context, fn)
}
```

**为什么使用 AsyncLocalStorage**:
- 当 Agent 被后台运行时，多个 Agent 可以在同一进程中并发执行
- AppState 是共享状态，会被覆盖
- AsyncLocalStorage 为每个异步执行链提供隔离，防止并发 Agent 互相干扰

---

## 6. In-Process Teammate 运行器

**文件位置**: `utils/swarm/inProcessRunner.ts`

### 6.1 邮箱轮询机制

```typescript
// utils/swarm/inProcessRunner.ts:300-400
async function waitForNextPromptOrShutdown(
  identity: TeammateIdentity,
  abortController: AbortController,
  taskId: string,
  getAppState: () => AppState,
  setAppState: SetAppStateFn,
  taskListId: string,
): Promise<WaitResult> {
  const POLL_INTERVAL_MS = 500
  let pollCount = 0
  
  while (!abortController.signal.aborted) {
    // 检查内存中的待处理消息
    const appState = getAppState()
    const task = appState.tasks[taskId]
    if (task?.pendingUserMessages.length > 0) {
      const message = task.pendingUserMessages[0]
      setAppState(prev => ({
        ...prev,
        tasks: {
          ...prev.tasks,
          [taskId]: {
            ...prev.tasks[taskId],
            pendingUserMessages: prev.tasks[taskId].pendingUserMessages.slice(1),
          },
        },
      }))
      return { type: 'new_message', message, from: 'user' }
    }

    await sleep(POLL_INTERVAL_MS)
    pollCount++

    // 检查邮箱中的消息
    const allMessages = await readMailbox(identity.agentName, identity.teamName)
    
    // 优先处理 shutdown 请求
    let shutdownIndex = allMessages.findIndex(m => !m.read && isShutdownRequest(m.text))
    if (shutdownIndex !== -1) {
      await markMessageAsReadByIndex(identity.agentName, identity.teamName, shutdownIndex)
      return {
        type: 'shutdown_request',
        request: isShutdownRequest(allMessages[shutdownIndex].text),
        originalMessage: allMessages[shutdownIndex].text,
      }
    }

    // 优先处理 team-lead 消息
    let selectedIndex = allMessages.findIndex(m => !m.read && m.from === TEAM_LEAD_NAME)
    if (selectedIndex === -1) {
      selectedIndex = allMessages.findIndex(m => !m.read)
    }

    if (selectedIndex !== -1) {
      const msg = allMessages[selectedIndex]
      await markMessageAsReadByIndex(identity.agentName, identity.teamName, selectedIndex)
      return {
        type: 'new_message',
        message: msg.text,
        from: msg.from,
        color: msg.color,
        summary: msg.summary,
      }
    }
  }
  
  return { type: 'aborted' }
}
```

### 6.2 权限请求桥接

In-process teammate 使用两种方式进行权限请求：

1. **Leader UI 队列** (首选): 使用领导者的 ToolUseConfirm 对话框
2. **邮箱系统** (回退): 通过邮箱发送权限请求并轮询响应

```typescript
// utils/swarm/inProcessRunner.ts:100-200
function createInProcessCanUseTool(
  identity: TeammateIdentity,
  abortController: AbortController,
  onPermissionWaitMs?: (waitMs: number) => void,
): CanUseToolFn {
  return async (tool, input, toolUseContext, assistantMessage, toolUseID, forceDecision) => {
    const result = forceDecision ?? await hasPermissionsToUseTool(...)
    
    if (result.behavior !== 'ask') return result
    
    const setToolUseConfirmQueue = getLeaderToolUseConfirmQueue()
    
    // 标准路径：使用带 worker 徽章的 ToolUseConfirm 对话框
    if (setToolUseConfirmQueue) {
      return new Promise<PermissionDecision>(resolve => {
        setToolUseConfirmQueue(queue => [...queue, {
          assistantMessage,
          tool,
          description,
          input,
          toolUseContext,
          toolUseID,
          permissionResult: result,
          workerBadge: identity.color
            ? { name: identity.agentName, color: identity.color }
            : undefined,
          onAllow(updatedInput, permissionUpdates, feedback, contentBlocks) {
            persistPermissionUpdates(permissionUpdates)
            resolve({ behavior: 'allow', updatedInput, ... })
          },
          onReject(feedback, contentBlocks) {
            resolve({ behavior: 'ask', message: SUBAGENT_REJECT_MESSAGE, ... })
          },
        }])
      })
    }
    
    // 回退路径：使用邮箱系统
    return new Promise<PermissionDecision>(resolve => {
      const request = createPermissionRequest({ ... })
      registerPermissionCallback({ requestId: request.id, ... })
      void sendPermissionRequestViaMailbox(request)
      // 轮询邮箱获取响应...
    })
  }
}
```

---

## 7. 关键实现细节总结

### 7.1 Prompt Cache 共享策略

| 组件 | Cache 策略 |
|------|-----------|
| Fork Subagent | 使用相同的 `FORK_PLACEHOLDER_RESULT` 确保 prefix 一致 |
| CacheSafeParams | 携带 systemPrompt, userContext, systemContext, toolUseContext, forkContextMessages |
| contentReplacementState | 默认克隆以保持 cache 决策一致性 |

### 7.2 上下文隔离层次

| 状态类型 | Fork | Subagent | Teammate |
|---------|------|----------|----------|
| readFileState | 克隆 | 克隆 | 克隆 |
| setAppState | No-op | No-op (默认) | 共享 (交互式) |
| setResponseLength | No-op | No-op (默认) | 可共享 |
| abortController | 子进程链接 | 子进程链接 (默认) | 可共享 |
| contentReplacementState | 克隆 | 克隆 | 可覆盖 |

### 7.3 Agent 通信机制对比

| 机制 | 用途 | 上下文传递 |
|------|------|-----------|
| Fork Subagent | 并行任务执行 | 完整上下文继承 |
| Coordinator Worker | 任务分片 | 自包含 prompt，无上下文继承 |
| SendMessage | 继续现有 Agent | Agent 保留自身上下文 |
| Mailbox | 异步 Agent 间通信 | 结构化 JSON 消息 |
| Task Notification | 向 Coordinator 报告结果 | XML 格式，包含 usage 统计 |

---

## 8. 相关文件索引

| 文件路径 | 主要内容 |
|---------|---------|
| `tools/AgentTool/forkSubagent.ts` | Fork Subagent 实现，FORK_PLACEHOLDER_RESULT |
| `utils/forkedAgent.ts` | CacheSafeParams, createSubagentContext, runForkedAgent |
| `coordinator/coordinatorMode.ts` | Coordinator Mode 系统提示和配置 |
| `tools/SendMessageTool/SendMessageTool.ts` | SendMessage 工具实现 |
| `utils/task/framework.ts` | Task Notification XML 生成 |
| `utils/teammateMailbox.ts` | 邮箱系统，结构化协议消息 |
| `utils/agentContext.ts` | AsyncLocalStorage Agent 上下文 |
| `utils/teammateContext.ts` | AsyncLocalStorage Teammate 上下文 |
| `utils/swarm/inProcessRunner.ts` | In-process teammate 运行器 |
| `tools/AgentTool/AgentTool.tsx` | Agent 工具主实现 |
| `tools/AgentTool/runAgent.ts` | Agent 查询循环 |

---

## 9. 设计原则

1. **Cache 优先**: Fork Subagent 使用相同的 placeholder 确保 prompt cache 命中
2. **隔离可变状态**: 子 Agent 默认不修改父进程状态
3. **任务注册例外**: `setAppStateForTasks` 始终指向根存储
4. **自包含 Prompt**: Coordinator Worker 的 prompt 必须包含所有必要上下文
5. **结构化通信**: Agent 间使用结构化 JSON/XML 消息而非纯文本
