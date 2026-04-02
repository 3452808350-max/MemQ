# Claude Code 上下文管理 + OpenClaw 短期记忆融合方案

**版本**: 1.0  
**日期**: 2026-04-02  
**目标**: 将 Claude Code 的上下文管理功能融入 OpenClaw 的短期记忆插件

---

## 1. 架构设计图

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     OpenClaw Context Memory Plugin                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    ContextManager (核心协调器)                         │ │
│  │                                                                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │ │
│  │  │ TokenBudget  │  │ MessageHistory│  │MultiAgentCtx │                │ │
│  │  │   模块       │  │    模块      │  │    模块      │                │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │ │
│  │         │                 │                  │                         │ │
│  │         └─────────────────┴──────────────────┘                         │ │
│  │                              │                                          │ │
│  │                    ┌─────────┴─────────┐                               │ │
│  │                    │  ContextStrategy  │                               │ │
│  │                    │   (策略调度器)     │                               │ │
│  │                    └─────────┬─────────┘                               │ │
│  └──────────────────────────────┼─────────────────────────────────────────┘ │
│                                 │                                           │
│  ┌──────────────────────────────┼─────────────────────────────────────────┐ │
│  │         memory-lancedb-pro   │     (现有长期记忆层)                     │ │
│  │  ┌───────────────────────────┴────────────────────────────────────┐   │ │
│  │  │  MemoryStore │ Retriever │ Embedder │ ScopeManager │ Tools    │   │ │
│  │  └─────────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    OpenClaw Plugin SDK / Hooks                          │ │
│  │  before_agent_start │ agent_end │ command:new │ sessions_*             │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Multi-Agent Context Flow

```
Main Session                          Subagent (Fork/Coordinator)
┌─────────────┐                      ┌─────────────┐
│   Context   │ ────── fork ───────► │   Context   │
│   Manager   │   (snapshot)         │   Manager   │
└──────┬──────┘                      └──────┬──────┘
       │                                    │
       │  ◄──── TaskNotification ──────────┤
       │     (result + usage stats)         │
       │                                    │
       ▼                                    ▼
┌─────────────┐                      ┌─────────────┐
│ Merge Result│                      │ Isolated    │
│ into Parent │                      │ Token Budget│
└─────────────┘                      │ Msg History │
                                     │ Scope       │
                                     └─────────────┘
```

### 1.3 Token Budget Allocation

```
Total Budget (200k tokens)
├── Reserve Budget (40k) ──► For response generation
├── Active Context (100k)
│   ├── System Prompt (20k)
│   ├── Conversation History (60k)
│   └── Injected Memories (20k)
└── Buffer (60k) ──► Emergency overflow / compaction headroom
```

---

## 2. 核心类的 TypeScript 接口定义

### 2.1 ContextManager - 核心协调器

```typescript
import type { MemoryStore, MemoryRetriever, ScopeManager } from "memory-lancedb-pro";

// ===== 配置接口 =====

export interface ContextManagerConfig {
  tokenBudget: TokenBudgetConfig;
  messageHistory: MessageHistoryConfig;
  multiAgent: MultiAgentContextConfig;
  taskNotification: TaskNotificationConfig;
  storage: {
    store: MemoryStore;
    retriever: MemoryRetriever;
    scopeManager: ScopeManager;
  };
}

export interface TokenBudgetConfig {
  totalBudget: number;        // 总预算 (默认 200000)
  reserveBudget: number;      // 保留预算 (默认 40000)
  warningThreshold: number;   // 警告阈值 0-1 (默认 0.8)
  criticalThreshold: number;  // 紧急阈值 0-1 (默认 0.95)
  compactionTarget: number;   // 压缩目标 0-1 (默认 0.6)
}

export interface MessageHistoryConfig {
  maxMessages: number;        // 最大消息数 (默认 200)
  priorityLayers: PriorityLayerConfig[];
  truncationStrategy: "fifo" | "priority" | "semantic";
  compressionTrigger: {
    messageCount: number;
    tokenCount: number;
  };
}

export interface PriorityLayerConfig {
  name: string;
  priority: number;           // 1-10, 越高越重要
  selector: MessageSelector;
  minKeep: number;            // 最少保留数量
  maxKeep: number;            // 最多保留数量
}

export type MessageSelector = 
  | { type: "role"; role: "user" | "assistant" | "system" }
  | { type: "keyword"; keywords: string[] }
  | { type: "pattern"; regex: string }
  | { type: "tool"; toolNames: string[] }
  | { type: "custom"; fn: (msg: Message) => boolean };

export interface MultiAgentContextConfig {
  isolationMode: "strict" | "shared" | "hybrid";
  forkSnapshotDepth: number;  // Fork 时复制的历史深度
  mergeStrategy: "full" | "summary" | "delta";
  coordinatorPhases: WorkflowPhase[];
}

export interface TaskNotificationConfig {
  storageScope: string;       // 存储 scope (默认 "task:notifications")
  retentionDays: number;      // 保留天数 (默认 7)
  autoArchive: boolean;
}

// ===== ContextManager 类 =====

export class ContextManager {
  constructor(config: ContextManagerConfig);
  
  // 主入口方法
  processMessage(
    message: UserMessage,
    context: ProcessingContext
  ): Promise<ContextInjectionResult>;
  
  prepareAgentContext(
    agentId: string,
    task: string,
    parentContext?: AgentContext
  ): Promise<AgentContext>;
  
  mergeAgentContext(
    agentId: string,
    result: AgentResult,
    parentContext: AgentContext
  ): Promise<void>;
  
  getContextState(): ContextState;
  
  forceCompaction(): Promise<CompactionResult>;
  
  // 生命周期钩子
  onAgentStart(event: AgentStartEvent): Promise<void>;
  onAgentEnd(event: AgentEndEvent): Promise<void>;
  onSessionReset(event: SessionResetEvent): Promise<void>;
}

// ===== 消息类型 =====

export interface UserMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string | ContentBlock[];
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export interface ContentBlock {
  type: "text" | "image" | "tool_use" | "tool_result";
  content?: unknown;
}

export interface ProcessingContext {
  sessionId: string;
  agentId?: string;
  parentAgentId?: string;
  workflowPhase?: WorkflowPhase;
  isFork?: boolean;
  isCoordinator?: boolean;
}

export interface ContextInjectionResult {
  contextToInject: string;
  injectedTokens: number;
  reason: InjectionReason;
  strategy: ContextStrategyType;
  memoryReferences: MemoryReference[];
}

export interface InjectionReason {
  type: "budget_exceeded" | "topic_change" | "phase_transition" | "manual" | "auto";
  description: string;
}

export interface MemoryReference {
  id: string;
  scope: string;
  relevanceScore: number;
}

export type WorkflowPhase = "research" | "synthesis" | "implementation" | "verification";
export type ContextStrategyType = "compress" | "truncate" | "inject_memory" | "snapshot";

export interface ContextState {
  currentTokens: number;
  budgetUsage: number;      // 0-1
  messageCount: number;
  activeAgents: string[];
  pendingTasks: TaskStatus[];
}

export interface TaskStatus {
  taskId: string;
  status: "running" | "completed" | "failed" | "killed";
  notified: boolean;
}

export interface CompactionResult {
  tokensFreed: number;
  messagesCompressed: number;
  summariesCreated: string[];
}

// ===== Agent 上下文 =====

export interface AgentContext {
  agentId: string;
  sessionId: string;
  tokenBudget: TokenBudget;
  messageHistory: MessageHistory;
  scope: string;
  workflowPhase?: WorkflowPhase;
  parentContextId?: string;
}

export interface AgentResult {
  status: "completed" | "failed" | "killed";
  output: string;
  usage: {
    totalTokens: number;
    toolUses: number;
    durationMs: number;
  };
  worktree?: {
    path: string;
    branch?: string;
  };
}
```

### 2.2 TokenBudget 模块

```typescript
// ============================================================================
// TokenBudget - Token 预算分配和监控
// ============================================================================

export interface TokenUsage {
  systemPrompt: number;
  conversationHistory: number;
  injectedMemories: number;
  toolResults: number;
  thinkingBlocks: number;
  reserved: number;
  total: number;
}

export interface BudgetAlert {
  level: "warning" | "critical";
  currentUsage: number;
  threshold: number;
  recommendedAction: "compress" | "truncate" | "inject_fresh";
}

export class TokenBudget {
  constructor(config: TokenBudgetConfig);
  
  // 预算查询
  getTotalBudget(): number;
  getAvailableBudget(): number;
  getCurrentUsage(): TokenUsage;
  getUsagePercentage(): number;
  
  // 预算分配
  allocateForResponse(estimatedTokens: number): boolean;
  releaseAllocation(tokens: number): void;
  
  // 预算监控
  checkThresholds(): BudgetAlert | null;
  setUsageEstimator(estimator: TokenEstimator): void;
  
  // 预算调整
  adjustReserve(newReserve: number): void;
  emergencyRelease(targetUsage: number): number;
}

export interface TokenEstimator {
  estimateText(text: string): number;
  estimateMessage(msg: UserMessage): number;
  estimateContext(context: string): number;
}

// 默认实现：基于字符数的快速估算
export class DefaultTokenEstimator implements TokenEstimator {
  private charsPerToken: number;  // 默认 4 (英文), 1.5 (中文)
  
  constructor(charsPerToken?: number);
  
  estimateText(text: string): number {
    const hasCJK = /[\u4e00-\u9fff]/.test(text);
    const factor = hasCJK ? 1.5 : this.charsPerToken;
    return Math.ceil(text.length / factor);
  }
  
  estimateMessage(msg: UserMessage): number {
    if (typeof msg.content === "string") {
      return this.estimateText(msg.content);
    }
    // 处理 ContentBlock[]
    return msg.content.reduce((sum, block) => {
      if (block.type === "text" && block.content) {
        return sum + this.estimateText(String(block.content));
      }
      if (block.type === "image") return 1000; // 粗略估算
      return sum + 100; // 其他类型
    }, 0);
  }
  
  estimateContext(context: string): number {
    return this.estimateText(context);
  }
}
```

### 2.3 MessageHistory 模块

```typescript
// ============================================================================
// MessageHistory - 消息历史优先级分层和截断
// ============================================================================

export interface MessageWithPriority extends UserMessage {
  priority: number;  // 1-10
  layer: string;
  ageInTurns: number;
}

export interface TruncationResult {
  removed: UserMessage[];
  retained: UserMessage[];
  summary?: string;
  tokensFreed: number;
}

export interface CompressionResult {
  originalMessages: UserMessage[];
  compressedSummary: string;
  tokensBefore: number;
  tokensAfter: number;
}

export class MessageHistory {
  constructor(config: MessageHistoryConfig);
  
  // 消息管理
  addMessage(message: UserMessage): void;
  getMessages(limit?: number): UserMessage[];
  getMessagesByLayer(layer: string): UserMessage[];
  
  // 优先级计算
  calculatePriority(message: UserMessage): number;
  assignLayers(messages: UserMessage[]): MessageWithPriority[];
  
  // 截断策略
  truncate(targetTokens: number): TruncationResult;
  truncateByCount(maxCount: number): TruncationResult;
  truncateFIFO(count: number): TruncationResult;
  
  // 压缩
  compressMessages(
    messages: UserMessage[],
    compressionPrompt?: string
  ): Promise<CompressionResult>;
  
  // 状态查询
  getMessageCount(): number;
  getTokenCount(): number;
  getLayerStats(): Record<string, number>;
  
  // 清理
  clear(): void;
  removeOlderThan(turns: number): TruncationResult;
}

// ===== 优先级层定义 =====

export const DEFAULT_PRIORITY_LAYERS: PriorityLayerConfig[] = [
  {
    name: "system_critical",
    priority: 10,
    selector: { type: "role", role: "system" },
    minKeep: 1,
    maxKeep: 5,
  },
  {
    name: "tool_results",
    priority: 8,
    selector: { type: "tool", toolNames: ["*"] },
    minKeep: 5,
    maxKeep: 20,
  },
  {
    name: "user_decisions",
    priority: 7,
    selector: { 
      type: "pattern", 
      regex: "(决定|决定用|改用|换成|decided|will use)" 
    },
    minKeep: 3,
    maxKeep: 10,
  },
  {
    name: "user_messages",
    priority: 5,
    selector: { type: "role", role: "user" },
    minKeep: 10,
    maxKeep: 50,
  },
  {
    name: "assistant_responses",
    priority: 3,
    selector: { type: "role", role: "assistant" },
    minKeep: 5,
    maxKeep: 30,
  },
];
```

### 2.4 MultiAgentContext 模块

```typescript
// ============================================================================
// MultiAgentContext - Fork/Coordinator 的上下文隔离
// ============================================================================

export interface ForkContext {
  parentContextId: string;
  forkedAt: number;
  snapshotDepth: number;
  isolatedScope: string;
}

export interface MergeOptions {
  strategy: "full" | "summary" | "delta";
  includeToolResults: boolean;
  includeThinking: boolean;
  maxTokens: number;
}

export interface CoordinatorState {
  phase: WorkflowPhase;
  workers: Map<string, WorkerContext>;
  completedTasks: TaskResult[];
  currentPlan: ImplementationPlan | null;
}

export interface WorkerContext {
  workerId: string;
  role: "research" | "implementation" | "verification";
  context: AgentContext;
  status: "running" | "completed" | "failed" | "killed";
  result?: TaskResult;
}

export class MultiAgentContext {
  constructor(config: MultiAgentContextConfig);
  
  // Fork 操作
  createFork(
    parentContext: AgentContext,
    agentId: string,
    task: string
  ): Promise<AgentContext>;
  
  getForkInfo(contextId: string): ForkContext | null;
  
  // Coordinator 管理
  initializeCoordinator(
    coordinatorId: string,
    task: string
  ): Promise<CoordinatorState>;
  
  spawnWorker(
    coordinatorId: string,
    role: WorkflowPhase,
    task: string
  ): Promise<WorkerContext>;
  
  updateWorkerStatus(
    coordinatorId: string,
    workerId: string,
    status: WorkerContext["status"],
    result?: TaskResult
  ): void;
  
  getCoordinatorState(coordinatorId: string): CoordinatorState | null;
  
  // Merge 操作
  mergeForkResult(
    parentContext: AgentContext,
    forkContext: AgentContext,
    result: AgentResult,
    options: MergeOptions
  ): Promise<MergeResult>;
  
  // 上下文隔离
  getIsolatedScope(agentId: string): string;
  isContextIsolated(contextId: string): boolean;
  
  // 清理
  cleanupCompletedWorkers(coordinatorId: string): void;
  destroyCoordinator(coordinatorId: string): void;
}

export interface MergeResult {
  mergedContext: AgentContext;
  tokensAdded: number;
  summaryInjected: boolean;
  taskNotificationStored: boolean;
}

export interface TaskResult {
  taskId: string;
  workerId: string;
  status: "completed" | "failed" | "killed";
  output: string;
  usage: {
    totalTokens: number;
    toolUses: number;
    durationMs: number;
  };
  timestamp: number;
}

export interface ImplementationPlan {
  tasks: ImplementationTask[];
  fileGroups: Record<string, ImplementationTask[]>;
  dependencies: Map<string, string[]>;
}

export interface ImplementationTask {
  id: string;
  description: string;
  targetFiles: string[];
  estimatedTokens: number;
  priority: number;
}
```

### 2.5 TaskNotification 集成

```typescript
// ============================================================================
// TaskNotification - 任务通知存储和检索
// ============================================================================

export interface TaskNotification {
  type: "task-notification";
  taskId: string;
  toolUseId?: string;
  outputFile?: string;
  status: "completed" | "failed" | "killed";
  summary: string;
  result?: string;
  usage: {
    totalTokens: number;
    toolUses: number;
    durationMs: number;
  };
  worktree?: {
    path: string;
    branch?: string;
  };
  timestamp: string;
  parentSessionKey: string;
}

export interface TaskNotificationQuery {
  taskId?: string;
  status?: TaskNotification["status"];
  parentSessionKey?: string;
  since?: string;
  limit?: number;
}

export class TaskNotificationService {
  constructor(
    store: MemoryStore,
    config: TaskNotificationConfig
  );
  
  // 存储通知
  storeNotification(notification: TaskNotification): Promise<string>;
  
  // 查询通知
  getNotification(taskId: string): Promise<TaskNotification | null>;
  getNotificationsBySession(sessionKey: string): Promise<TaskNotification[]>;
  queryNotifications(query: TaskNotificationQuery): Promise<TaskNotification[]>;
  
  // 状态管理
  markNotified(taskId: string): Promise<void>;
  isNotified(taskId: string): Promise<boolean>;
  
  // 清理
  archiveOldNotifications(olderThanDays: number): Promise<number>;
  deleteNotification(taskId: string): Promise<boolean>;
  
  // 格式转换
  toMemoryEntry(notification: TaskNotification): {
    text: string;
    category: "fact" | "decision";
    scope: string;
    metadata: string;
  };
  
  fromMemoryEntry(entry: MemoryEntry): TaskNotification | null;
}

// XML 格式 (Claude Code 原生)
export function buildTaskNotificationXML(notification: TaskNotification): string {
  return `
<task-notification>
  <task-id>${notification.taskId}</task-id>
  <tool-use-id>${notification.toolUseId || ""}</tool-use-id>
  <output-file>${notification.outputFile || ""}</output-file>
  <status>${notification.status}</status>
  <summary>${escapeXml(notification.summary)}</summary>
  <result>${escapeXml(notification.result || "")}</result>
  <usage>
    <total-tokens>${notification.usage.totalTokens}</total-tokens>
    <tool-uses>${notification.usage.toolUses}</tool-uses>
    <duration-ms>${notification.usage.durationMs}</duration-ms>
  </usage>
  ${notification.worktree ? `
  <worktree>
    <worktree-path>${escapeXml(notification.worktree.path)}</worktree-path>
    <worktree-branch>${escapeXml(notification.worktree.branch || "")}</worktree-branch>
  </worktree>` : ""}
  <timestamp>${notification.timestamp}</timestamp>
</task-notification>`.trim();
}

// JSON 格式 (OpenClaw 适配)
export function buildTaskNotificationJSON(notification: TaskNotification): string {
  return JSON.stringify(notification, null, 2);
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
```

---

## 3. 与现有 memory-lancedb-pro 的集成点

### 3.1 存储层集成

```typescript
// 使用现有的 MemoryStore 存储 TaskNotification
class TaskNotificationStorage {
  constructor(private store: MemoryStore) {}
  
  async store(notification: TaskNotification): Promise<string> {
    const entry = this.toMemoryEntry(notification);
    const vector = await this.embedder.embedPassage(entry.text);
    
    return this.store.store({
      text: entry.text,
      vector,
      category: entry.category,
      scope: entry.scope,
      importance: 0.8,  // 任务通知较重要
      metadata: entry.metadata,
    });
  }
  
  private toMemoryEntry(notification: TaskNotification): {
    text: string;
    category: "fact" | "decision";
    scope: string;
    metadata: string;
  } {
    const text = `Task ${notification.taskId} ${notification.status}: ${notification.summary}. ${notification.result || ""}`;
    
    return {
      text,
      category: notification.status === "completed" ? "fact" : "decision",
      scope: "task:notifications",
      metadata: JSON.stringify({
        type: "task-notification",
        taskId: notification.taskId,
        status: notification.status,
        usage: notification.usage,
        timestamp: notification.timestamp,
      }),
    };
  }
}
```

### 3.2 检索层集成

```typescript
// 使用现有的 Retriever 检索相关上下文
class ContextRetrievalService {
  constructor(private retriever: MemoryRetriever) {}
  
  async retrieveRelevantContext(
    query: string,
    options: {
      limit?: number;
      scopeFilter?: string[];
      category?: string;
      minScore?: number;
    }
  ): Promise<ContextSnippet[]> {
    const results = await this.retriever.retrieve({
      query,
      limit: options.limit || 5,
      scopeFilter: options.scopeFilter,
      category: options.category,
    });
    
    return results
      .filter(r => r.score >= (options.minScore || 0.3))
      .map(r => ({
        id: r.entry.id,
        text: r.entry.text,
        score: r.score,
        category: r.entry.category,
        scope: r.entry.scope,
      }));
  }
}
```

### 3.3 Scope 集成

```typescript
// 扩展现有的 ScopeManager 支持多 Agent 隔离
class AgentScopeManager {
  constructor(private scopeManager: ScopeManager) {}
  
  getAgentScope(agentId: string): string {
    // 为每个 Agent 创建独立的 scope
    return `agent:${agentId}`;
  }
  
  getCoordinatorScope(coordinatorId: string): string {
    return `coordinator:${coordinatorId}`;
  }
  
  getWorkerScope(coordinatorId: string, workerId: string): string {
    return `worker:${coordinatorId}:${workerId}`;
  }
  
  // 配置 Worker 只能访问自己的 scope + coordinator scope
  configureWorkerAccess(coordinatorId: string, workerId: string): void {
    const workerScope = this.getWorkerScope(coordinatorId, workerId);
    const coordinatorScope = this.getCoordinatorScope(coordinatorId);
    
    this.scopeManager.setAgentAccess(workerId, [
      workerScope,
      coordinatorScope,
      "global",  // 始终可访问全局
    ]);
  }
}
```

### 3.4 Hook 集成

```typescript
// 在 OpenClaw Plugin SDK 中注册钩子
export function registerContextMemoryHooks(
  api: OpenClawPluginApi,
  contextManager: ContextManager
): void {
  // Agent 启动前：准备上下文
  api.on("before_agent_start", async (event) => {
    const agentContext = await contextManager.prepareAgentContext(
      event.agentId || "main",
      event.prompt || ""
    );
    
    // 注入相关记忆到 prompt
    if (agentContext.injectedMemories) {
      event.prompt = `${agentContext.injectedMemories}\n\n${event.prompt}`;
    }
  });
  
  // Agent 结束后：合并上下文
  api.on("agent_end", async (event) => {
    if (!event.success) return;
    
    await contextManager.mergeAgentContext(
      event.agentId || "main",
      {
        status: event.success ? "completed" : "failed",
        output: event.response || "",
        usage: event.usage || { totalTokens: 0, toolUses: 0, durationMs: 0 },
      },
      event.context
    );
  });
  
  // 会话重置时：保存上下文
  api.on("command:new", async (event) => {
    await contextManager.onSessionReset(event);
  });
}
```

---

## 4. 实现优先级建议

### 4.1 Phase 1: 核心基础 (优先级: P0)

| 模块 | 任务 | 预估工作量 |
|------|------|-----------|
| TokenBudget | 基础预算跟踪 + 阈值检测 | 2 天 |
| MessageHistory | 消息存储 + 基础截断 (FIFO) | 2 天 |
| ContextManager | 基础协调器 + Hook 注册 | 3 天 |
| 集成测试 | 与 memory-lancedb-pro 联调 | 2 天 |

**里程碑**: 实现基本的 Token 预算监控和消息截断

### 4.2 Phase 2: 优先级分层 (优先级: P1)

| 模块 | 任务 | 预估工作量 |
|------|------|-----------|
| MessageHistory | 优先级层 + 智能截断 | 3 天 |
| TokenBudget | Token 估算器 + 动态调整 | 2 天 |
| ContextManager | 自动压缩触发 | 2 天 |

**里程碑**: 实现智能消息优先级管理

### 4.3 Phase 3: 多 Agent 支持 (优先级: P2)

| 模块 | 任务 | 预估工作量 |
|------|------|-----------|
| MultiAgentContext | Fork 上下文隔离 | 3 天 |
| MultiAgentContext | Coordinator 状态管理 | 3 天 |
| TaskNotification | 通知存储 + 查询 | 2 天 |
| 集成 | 与 OpenClaw sessions_* 集成 | 3 天 |

**里程碑**: 支持完整的 Fork/Coordinator 工作流

### 4.4 Phase 4: 优化和增强 (优先级: P3)

| 模块 | 任务 | 预估工作量 |
|------|------|-----------|
| MessageHistory | 语义压缩 (LLM 总结) | 3 天 |
| TokenBudget | 自适应预算分配 | 2 天 |
| MultiAgentContext | Merge 策略优化 | 2 天 |
| 文档和测试 | 完整文档 + 单元测试 | 3 天 |

**里程碑**: 生产就绪

### 4.5 总体时间线

```
Week 1-2: Phase 1 (核心基础)
Week 3-4: Phase 2 (优先级分层)
Week 5-7: Phase 3 (多 Agent 支持)
Week 8:   Phase 4 (优化和增强)
```

### 4.6 风险缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Token 估算不准确 | 中 | 使用保守估算，预留 buffer |
| 压缩质量差 | 高 | 提供手动压缩选项，可配置 prompt |
| 多 Agent 上下文污染 | 高 | 严格 scope 隔离，默认 strict 模式 |
| 性能开销 | 中 | 异步处理，缓存频繁查询 |

---

## 5. 配置示例

```json
{
  "contextMemory": {
    "tokenBudget": {
      "totalBudget": 200000,
      "reserveBudget": 40000,
      "warningThreshold": 0.8,
      "criticalThreshold": 0.95,
      "compactionTarget": 0.6
    },
    "messageHistory": {
      "maxMessages": 200,
      "truncationStrategy": "priority",
      "compressionTrigger": {
        "messageCount": 150,
        "tokenCount": 160000
      },
      "priorityLayers": [
        {
          "name": "system_critical",
          "priority": 10,
          "selector": { "type": "role", "role": "system" },
          "minKeep": 1,
          "maxKeep": 5
        },
        {
          "name": "user_decisions",
          "priority": 7,
          "selector": { 
            "type": "pattern", 
            "regex": "(决定 | 改用 | 换成|decided|will use)" 
          },
          "minKeep": 3,
          "maxKeep": 10
        }
      ]
    },
    "multiAgent": {
      "isolationMode": "strict",
      "forkSnapshotDepth": 50,
      "mergeStrategy": "summary",
      "coordinatorPhases": ["research", "synthesis", "implementation", "verification"]
    },
    "taskNotification": {
      "storageScope": "task:notifications",
      "retentionDays": 7,
      "autoArchive": true
    }
  }
}
```

---

## 6. 测试计划

### 6.1 单元测试

```typescript
// TokenBudget 测试
describe("TokenBudget", () => {
  it("should track usage correctly", () => {});
  it("should trigger warning at threshold", () => {});
  it("should emergency release when critical", () => {});
});

// MessageHistory 测试
describe("MessageHistory", () => {
  it("should assign priorities correctly", () => {});
  it("should truncate by token target", () => {});
  it("should preserve high-priority messages", () => {});
});

// MultiAgentContext 测试
describe("MultiAgentContext", () => {
  it("should create isolated fork context", () => {});
  it("should merge results correctly", () => {});
  it("should manage coordinator phases", () => {});
});
```

### 6.2 集成测试

```typescript
// 与 memory-lancedb-pro 集成测试
describe("ContextManager Integration", () => {
  it("should inject relevant memories before agent start", () => {});
  it("should store task notifications after completion", () => {});
  it("should handle fork/merge workflow", () => {});
});
```

### 6.3 端到端测试

```typescript
// 完整工作流测试
describe("End-to-End Workflow", () => {
  it("should handle multi-agent research task", async () => {
    // 1. Coordinator 启动
    // 2. Spawn Research Workers
    // 3. Collect results via TaskNotification
    // 4. Synthesis phase
    // 5. Implementation Workers
    // 6. Verification
    // 7. Merge all results
  });
});
```

---

## 7. 与 Claude Code 的兼容性

| Claude Code 功能 | 融合方案支持 | 备注 |
|-----------------|-------------|------|
| Context Window 管理 | ✅ | TokenBudget + MessageHistory |
| Server-side Compaction | ✅ | MessageHistory.compressMessages |
| Extended Thinking 支持 | ✅ | TokenBudget 自动排除 thinking tokens |
| Tool Result 管理 | ✅ | MessageHistory 优先级层 |
| Fork Subagent | ✅ | MultiAgentContext.createFork |
| Coordinator Mode | ✅ | MultiAgentContext + WorkflowPhase |
| Task Notification | ✅ | TaskNotificationService |
| Permission System | ✅ | 通过 ScopeManager 集成 |

---

## 8. 总结

本融合方案将 Claude Code 的上下文管理能力与 OpenClaw 的 memory-lancedb-pro 插件深度集成，提供：

1. **Token 预算管理** - 智能分配、监控和紧急释放
2. **消息历史分层** - 基于优先级的智能截断和压缩
3. **多 Agent 隔离** - Fork/Coordinator 的完整上下文隔离
4. **任务通知集成** - 在记忆系统中存储和检索任务状态

实现分为 4 个 Phase，总计约 8 周，优先级从核心基础到优化增强逐步推进。
