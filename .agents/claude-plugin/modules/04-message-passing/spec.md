# Module 04: Message Passing

## 目标

实现 Agent 间的双向消息传递，支持 teammate 通信和广播。

## 核心设计

### 消息类型

```typescript
type MessageType = 
  | TextMessage
  | StructuredMessage
  | BroadcastMessage

type TextMessage = {
  type: 'text'
  to: string              // 接收者名称
  summary?: string        // 5-10 字摘要
  content: string         // 消息内容
}

type StructuredMessage = 
  | ShutdownRequest
  | ShutdownResponse
  | PlanApprovalResponse

type ShutdownRequest = {
  type: 'shutdown_request'
  to: string
  reason?: string
}

type ShutdownResponse = {
  type: 'shutdown_response'
  to: string              // 必须是 "team-lead"
  requestId: string
  approve: boolean
  reason?: string          // reject 时必需
}

type PlanApprovalResponse = {
  type: 'plan_approval_response'
  to: string
  requestId: string
  approve: boolean
  feedback?: string        // reject 时建议
}

type BroadcastMessage = {
  type: 'broadcast'
  to: '*'                  // 广播标记
  summary: string
  content: string
}
```

### 路由机制

```typescript
interface MessageRouter {
  // 发送消息
  send(message: Message): Promise<SendResult>
  
  // 接收消息
  receive(agentId: string): Promise<Message[]>
  
  // 广播
  broadcast(message: BroadcastMessage): Promise<BroadcastResult>
}

// 实现
class AgentMessageRouter implements MessageRouter {
  private mailboxes: Map<string, Mailbox>
  private registry: AgentRegistry
  
  async send(message: Message): Promise<SendResult> {
    // 1. 解析目标
    const target = this.parseTarget(message.to)
    
    switch (target.scheme) {
      case 'agent':
        return this.sendToAgent(target.name, message)
      case 'broadcast':
        return this.broadcast(message)
      case 'uds':
        return this.sendToUds(target.path, message)
      case 'bridge':
        return this.sendToBridge(target.sessionId, message)
      default:
        throw new Error(`Unknown target scheme: ${target.scheme}`)
    }
  }
  
  private async sendToAgent(name: string, message: Message): Promise<SendResult> {
    // 查找 Agent
    const agentId = this.registry.getAgentId(name)
    
    if (!agentId) {
      return { success: false, error: `Agent "${name}" not found` }
    }
    
    // 获取 Agent 状态
    const task = this.getTask(agentId)
    
    if (isRunning(task)) {
      // 队列消息
      this.queueMessage(agentId, message)
      return { success: true, message: `Queued for ${name}` }
    } else if (isStopped(task)) {
      // 自动恢复
      await this.resumeAgent(agentId, message)
      return { success: true, message: `Resumed ${name} with message` }
    } else {
      // 从磁盘恢复
      await this.resumeFromDisk(agentId, message)
      return { success: true, message: `Resumed ${name} from disk` }
    }
  }
}
```

### Mailbox 实现

```typescript
interface Mailbox {
  agentId: string
  messages: QueuedMessage[]
  lastRead: Date
}

interface QueuedMessage {
  id: string
  from: string
  fromColor?: string
  summary?: string
  content: string
  timestamp: string
  type: 'text' | 'structured'
}

class MailboxManager {
  private mailboxes: Map<string, Mailbox> = new Map()
  
  write(to: string, message: QueuedMessage, teamName?: string): void {
    const mailbox = this.getOrCreateMailbox(to, teamName)
    mailbox.messages.push(message)
  }
  
  read(agentId: string, since?: Date): QueuedMessage[] {
    const mailbox = this.mailboxes.get(agentId)
    if (!mailbox) return []
    
    const messages = mailbox.messages.filter(m => 
      !since || new Date(m.timestamp) > since
    )
    
    mailbox.lastRead = new Date()
    return messages
  }
  
  drain(agentId: string): QueuedMessage[] {
    const mailbox = this.mailboxes.get(agentId)
    if (!mailbox) return []
    
    const messages = [...mailbox.messages]
    mailbox.messages = []
    return messages
  }
}
```

### Team 管理

```typescript
interface Team {
  name: string
  members: TeamMember[]
  lead: string            // team-lead agentId
}

interface TeamMember {
  agentId: string
  name: string
  color?: string
  role: 'lead' | 'member'
  backendType: 'in-process' | 'remote'
  tmuxPaneId?: string
}

class TeamManager {
  private teams: Map<string, Team> = new Map()
  
  createTeam(name: string, leadAgentId: string): Team {
    const team: Team = {
      name,
      members: [{
        agentId: leadAgentId,
        name: 'team-lead',
        role: 'lead',
        backendType: 'in-process'
      }],
      lead: leadAgentId
    }
    
    this.teams.set(name, team)
    return team
  }
  
  addMember(teamName: string, member: TeamMember): void {
    const team = this.teams.get(teamName)
    if (!team) throw new Error(`Team ${teamName} not found`)
    
    team.members.push(member)
  }
  
  broadcast(teamName: string, message: Message, excludeSender?: string): void {
    const team = this.teams.get(teamName)
    if (!team) throw new Error(`Team ${teamName} not found`)
    
    for (const member of team.members) {
      if (member.agentId !== excludeSender) {
        this.mailboxManager.write(member.name, message, teamName)
      }
    }
  }
}
```

### 与 OpenClaw 集成

```typescript
// 扩展现有 sessions_send
interface AgentMessageOptions {
  // 基础
  to: string              // agent-name | "*" | "uds://path" | "bridge://id"
  
  // 消息内容
  type?: 'text' | 'shutdown_request' | 'shutdown_response' | 'plan_approval'
  content?: string
  summary?: string          // text 消息必需
  
  // Structured 消息
  requestId?: string
  approve?: boolean
  reason?: string
  feedback?: string
  
  // 选项
  requireResponse?: boolean // 等待响应
  timeout?: number          // 超时 ms
}

// 使用示例

// 1. 发送文本消息
await sessions_send({
  sessionKey: targetAgent,
  message: JSON.stringify({
    to: 'researcher-1',
    type: 'text',
    summary: 'Need file list',
    content: 'Please provide the list of files in src/'
  })
})

// 2. 广播
await sessions_send({
  sessionKey: '*',
  message: JSON.stringify({
    to: '*',
    type: 'broadcast',
    summary: 'Project update',
    content: 'All workers pause for sync'
  })
})

// 3. 关闭请求 (Team Lead → Member)
await sessions_send({
  sessionKey: 'worker-1',
  message: JSON.stringify({
    to: 'worker-1',
    type: 'shutdown_request',
    reason: 'Task complete'
  })
})

// 4. 关闭响应 (Member → Team Lead)
await sessions_send({
  sessionKey: 'team-lead',
  message: JSON.stringify({
    to: 'team-lead',
    type: 'shutdown_response',
    requestId: 'req-123',
    approve: true
  })
})
```

### 特殊路由

```typescript
// UDS 跨会话通信
if (target.scheme === 'uds') {
  await sendToUdsSocket(target.path, message)
}

// Remote Control 桥接
if (target.scheme === 'bridge') {
  await postInterClaudeMessage(target.sessionId, message)
}

// In-process 队友
if (target.backendType === 'in-process') {
  // 直接内存通信
  queuePendingMessage(agentId, message)
}
```

## 与 Task Notification 的区别

| 特性 | Task Notification | Message Passing |
|------|-------------------|-----------------|
| 方向 | Agent → Parent (单向) | Agent ↔ Agent (双向) |
| 时机 | 任务完成时 | 任意时刻 |
| 内容 | 结果 + 统计 | 任意消息 |
| 协议 | XML/JSON 标准格式 | 灵活格式 |
| 队列 | 一次性通知 | 持久化 Mailbox |
| 用途 | 状态报告 | 协作通信 |

## 测试计划

- [ ] 文本消息发送/接收
- [ ] Structured 消息 (shutdown/plan)
- [ ] 广播机制
- [ ] Mailbox 队列管理
- [ ] 自动恢复已停止 Agent
- [ ] 从磁盘恢复
- [ ] UDS 跨会话通信
- [ ] Team 管理
- [ ] 权限检查 (只有 lead 可批准 plan)
