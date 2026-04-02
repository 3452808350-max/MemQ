/**
 * Context Manager - Type Definitions
 * 
 * 基于 Claude Code 上下文管理 + OpenClaw 短期记忆融合方案
 */

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
  text?: string;
}

export interface MessageWithPriority extends UserMessage {
  priority: number; // 1-10
  layer: string;
  ageInTurns: number;
}

// ===== Token 预算配置 =====

export interface TokenBudgetConfig {
  totalBudget: number; // 总预算 (默认 200000)
  reserveBudget: number; // 保留预算 (默认 40000)
  warningThreshold: number; // 警告阈值 0-1 (默认 0.8)
  criticalThreshold: number; // 紧急阈值 0-1 (默认 0.95)
  compactionTarget: number; // 压缩目标 0-1 (默认 0.6)
}

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

// ===== 消息历史配置 =====

export interface MessageHistoryConfig {
  maxMessages: number; // 最大消息数 (默认 200)
  priorityLayers: PriorityLayerConfig[];
  truncationStrategy: "fifo" | "priority" | "semantic";
  compressionTrigger: {
    messageCount: number;
    tokenCount: number;
  };
}

export interface PriorityLayerConfig {
  name: string;
  priority: number; // 1-10, 越高越重要
  selector: MessageSelector;
  minKeep: number; // 最少保留数量
  maxKeep: number; // 最多保留数量
}

export type MessageSelector =
  | { type: "role"; role: "user" | "assistant" | "system" }
  | { type: "keyword"; keywords: string[] }
  | { type: "pattern"; regex: string }
  | { type: "tool"; toolNames: string[] }
  | { type: "custom"; fn: (msg: UserMessage) => boolean };

// ===== 多 Agent 配置 =====

export interface MultiAgentContextConfig {
  isolationMode: "strict" | "shared" | "hybrid";
  forkSnapshotDepth: number; // Fork 时复制的历史深度
  mergeStrategy: "full" | "summary" | "delta";
  coordinatorPhases: WorkflowPhase[];
}

export type WorkflowPhase = "research" | "synthesis" | "implementation" | "verification";

// ===== 任务通知配置 =====

export interface TaskNotificationConfig {
  storageScope: string; // 存储 scope (默认 "task:notifications")
  retentionDays: number; // 保留天数 (默认 7)
  autoArchive: boolean;
}

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
  timestamp: string;
}

export interface ImplementationTask {
  id: string;
  description: string;
  targetFiles: string[];
  estimatedTokens: number;
  priority: number;
}

export interface ImplementationPlan {
  tasks: ImplementationTask[];
  fileGroups: Record<string, ImplementationTask[]>;
  dependencies: Map<string, string[]>;
}

export interface WorkerContext {
  workerId: string;
  role: WorkflowPhase;
  context: AgentContext;
  status: "running" | "completed" | "failed" | "killed";
  result?: TaskResult;
}

export interface CoordinatorState {
  phase: WorkflowPhase;
  workers: Map<string, WorkerContext>;
  completedTasks: TaskResult[];
  currentPlan: ImplementationPlan | null;
}

// ===== 上下文管理配置 =====

export interface ContextManagerConfig {
  tokenBudget: TokenBudgetConfig;
  messageHistory: MessageHistoryConfig;
  multiAgent: MultiAgentContextConfig;
  taskNotification: TaskNotificationConfig;
}

// ===== 处理上下文 =====

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

export type ContextStrategyType = "compress" | "truncate" | "inject_memory" | "snapshot";

// ===== 上下文状态 =====

export interface ContextState {
  currentTokens: number;
  budgetUsage: number; // 0-1
  messageCount: number;
  activeAgents: string[];
  pendingTasks: TaskStatus[];
}

export interface TaskStatus {
  taskId: string;
  status: "running" | "completed" | "failed" | "killed";
  notified: boolean;
}

// ===== Agent 上下文 =====

export interface AgentContext {
  agentId: string;
  sessionId: string;
  tokenBudget: TokenBudgetSnapshot;
  messageHistory: MessageHistorySnapshot;
  scope: string;
  workflowPhase?: WorkflowPhase;
  parentContextId?: string;
}

export interface TokenBudgetSnapshot {
  totalBudget: number;
  usedBudget: number;
  allocation: Record<string, number>;
}

export interface MessageHistorySnapshot {
  messageCount: number;
  tokenCount: number;
  layerStats: Record<string, number>;
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

// ===== 截断结果 =====

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
  compressionRatio?: number;
  preservedMessages?: UserMessage[];
  compressedMessages?: UserMessage[];
}

// ===== 压缩配置 =====

export interface CompressionConfig {
  enabled: boolean;
  minMessages: number;
  maxMessages: number;
  targetRatio: number;
  preserveSystemMessages: boolean;
  preserveToolResults: boolean;
  customPrompt?: string;
}

export const DEFAULT_COMPRESSION_CONFIG: CompressionConfig = {
  enabled: true,
  minMessages: 10,
  maxMessages: 100,
  targetRatio: 0.5,
  preserveSystemMessages: true,
  preserveToolResults: true,
};

// ===== Fork/Merge =====

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

export interface MergeResult {
  mergedContext: AgentContext;
  tokensAdded: number;
  summaryInjected: boolean;
  taskNotificationStored: boolean;
}

// ===== Compaction 结果 =====

export interface CompactionResult {
  tokensFreed: number;
  messagesCompressed: number;
  summariesCreated: string[];
}

// ===== Token 估算器 =====

export interface TokenEstimator {
  estimateText(text: string): number;
  estimateMessage(msg: UserMessage): number;
  estimateContext(context: string): number;
}

// ===== 事件类型 =====

export interface AgentStartEvent {
  agentId: string;
  sessionId: string;
  task: string;
  parentAgentId?: string;
  isFork?: boolean;
  isCoordinator?: boolean;
}

export interface AgentEndEvent {
  agentId: string;
  sessionId: string;
  result: AgentResult;
  parentAgentId?: string;
}

export interface SessionResetEvent {
  sessionId: string;
  previousContext?: AgentContext;
}

// ===== 默认配置 =====

export const DEFAULT_TOKEN_BUDGET_CONFIG: TokenBudgetConfig = {
  totalBudget: 200000,
  reserveBudget: 40000,
  warningThreshold: 0.8,
  criticalThreshold: 0.95,
  compactionTarget: 0.6,
};

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
      regex: "(决定|决定用|改用|换成|decided|will use)",
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

export const DEFAULT_MESSAGE_HISTORY_CONFIG: MessageHistoryConfig = {
  maxMessages: 200,
  priorityLayers: DEFAULT_PRIORITY_LAYERS,
  truncationStrategy: "fifo",
  compressionTrigger: {
    messageCount: 150,
    tokenCount: 160000,
  },
};

export const DEFAULT_MULTI_AGENT_CONFIG: MultiAgentContextConfig = {
  isolationMode: "strict",
  forkSnapshotDepth: 50,
  mergeStrategy: "summary",
  coordinatorPhases: ["research", "synthesis", "implementation", "verification"],
};

export const DEFAULT_TASK_NOTIFICATION_CONFIG: TaskNotificationConfig = {
  storageScope: "task:notifications",
  retentionDays: 7,
  autoArchive: true,
};

export const DEFAULT_CONTEXT_MANAGER_CONFIG: ContextManagerConfig = {
  tokenBudget: DEFAULT_TOKEN_BUDGET_CONFIG,
  messageHistory: DEFAULT_MESSAGE_HISTORY_CONFIG,
  multiAgent: DEFAULT_MULTI_AGENT_CONFIG,
  taskNotification: DEFAULT_TASK_NOTIFICATION_CONFIG,
};