# Module 03: Task Notification

## 目标

建立 Agent 向父 Agent 报告完成状态的标准协议。

## 核心设计

### XML 协议格式

```xml
<task-notification>
  <task-id>{agentId}</task-id>
  <tool-use-id>{toolUseId}</tool-use-id>
  <output-file>/path/to/output.jsonl</output-file>
  <status>completed|failed|killed</status>
  <summary>Agent "description" completed</summary>
  <result>{agent's final text response}</result>
  <usage>
    <total-tokens>1523</total-tokens>
    <tool-uses>12</tool-uses>
    <duration-ms>45000</duration-ms>
  </usage>
  <worktree>
    <worktree-path>/path/to/worktree</worktree-path>
    <worktree-branch>feature-branch</worktree-branch>
  </worktree>
</task-notification>
```

### JSON 格式 (OpenClaw 适配)

```json
{
  "type": "task-notification",
  "taskId": "agent-uuid",
  "toolUseId": "tool-use-uuid",
  "outputFile": "/path/to/output.jsonl",
  "status": "completed",
  "summary": "Agent \"code-explorer\" completed",
  "result": "Found 15 TODO comments...",
  "usage": {
    "totalTokens": 1523,
    "toolUses": 12,
    "durationMs": 45000
  },
  "worktree": {
    "path": "/path/to/worktree",
    "branch": "feature-branch"
  },
  "timestamp": "2026-04-02T07:30:00Z"
}
```

### 状态机

```
┌─────────┐    spawn     ┌─────────┐
│  idle   │ ────────────►│ running │
└─────────┘              └────┬────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │completed│    │ failed  │    │ killed  │
        └────┬────┘    └─────────┘    └─────────┘
             │
             ▼
        ┌─────────┐
        │notified │
        └─────────┘
```

### 原子性通知

```typescript
interface TaskState {
  taskId: string
  status: 'running' | 'completed' | 'failed' | 'killed'
  notified: boolean           // 原子性标志
  result?: string
  error?: string
  usage?: UsageStats
}

async function notifyTaskComplete(
  taskId: string,
  result: TaskResult
): Promise<void> {
  // 原子性检查并设置 notified 标志
  const task = getTask(taskId)
  
  if (task.notified) {
    return  // 已通知，跳过
  }
  
  task.notified = true
  
  // 构建通知消息
  const notification = buildTaskNotification(taskId, result)
  
  // 发送到父 Agent
  await sendToParent(notification)
}
```

### 与 OpenClaw 集成

```typescript
// 包装 sessions_send
interface TaskNotificationOptions {
  // 目标父会话
  parentSessionKey: string
  
  // 任务信息
  taskId: string
  toolUseId?: string
  
  // 状态
  status: 'completed' | 'failed' | 'killed'
  
  // 结果
  summary: string
  result?: string
  error?: string
  
  // 统计
  usage: {
    totalTokens: number
    toolUses: number
    durationMs: number
  }
  
  // Worktree 信息 (可选)
  worktree?: {
    path: string
    branch?: string
  }
}

// Agent 侧发送
await sendTaskNotification({
  parentSessionKey: parentKey,
  taskId: agentId,
  status: 'completed',
  summary: 'Agent "code-explorer" completed',
  result: 'Found 15 TODOs...',
  usage: { totalTokens: 1523, toolUses: 12, durationMs: 45000 }
})

// 父 Agent 侧接收
// 通过 sessions_send 接收，自动解析为 TaskNotification
```

### 消息队列

```typescript
interface MessageQueue {
  // 队列消息
  enqueue(notification: TaskNotification): void
  
  // 批量处理
  dequeueAll(): TaskNotification[]
  
  // 按 taskId 过滤
  getByTaskId(taskId: string): TaskNotification | undefined
  
  // 清理已完成
  cleanup(completedIds: string[]): void
}

// 使用
const queue = new MessageQueue()

// Agent 完成时
queue.enqueue({
  type: 'task-notification',
  taskId: 'agent-1',
  status: 'completed',
  // ...
})

// 父 Agent 定期检查
const notifications = queue.dequeueAll()
for (const n of notifications) {
  handleTaskComplete(n)
}
```

### 推测中止

当背景任务状态改变时，丢弃推测结果:

```typescript
function abortSpeculation(taskId: string): void {
  const speculated = getSpeculatedResults(taskId)
  
  if (speculated) {
    // 丢弃推测结果
    discardSpeculation(taskId)
    
    // 保留提示词建议文本
    preserveSuggestionText(taskId)
  }
}

// 在任务状态改变时调用
onTaskStatusChange(taskId, (newStatus) => {
  abortSpeculation(taskId)
})
```

## 与 Coordinator Mode 的关系

Task Notification 是 Coordinator Mode 的核心通信机制:

```
Coordinator
    │
    ├── spawn Worker 1 ──► Worker runs ──► Task Notification ──┐
    ├── spawn Worker 2 ──► Worker runs ──► Task Notification ──┤
    ├── spawn Worker 3 ──► Worker runs ──► Task Notification ──┼──► Coordinator processes
    │                                                          │    (Synthesis phase)
    └── ...                                                    │
                                                               ▼
                                                    Research phase complete
```

## 测试计划

- [ ] XML 格式生成/解析
- [ ] JSON 格式生成/解析
- [ ] 原子性通知 (防重复)
- [ ] 消息队列管理
- [ ] 推测中止
- [ ] 状态机转换
- [ ] Worktree 信息传递
