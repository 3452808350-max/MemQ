/**
 * Context Manager - Core Exports
 */

export { TokenBudget, DefaultTokenEstimator } from "./TokenBudget.js";
export { MessageHistory } from "./MessageHistory.js";
export { ContextManager } from "./ContextManager.js";
export { PriorityTruncator } from "./PriorityTruncator.js";
export { LLMCompressor } from "./LLMCompressor.js";
export {
  MultiAgentContext,
  ForkManager,
  CoordinatorManager,
  MergeManager,
} from "./MultiAgentContext.js";
export {
  TaskNotificationService,
  TaskNotificationStorage,
} from "./TaskNotificationService.js";
export { LanceDBStorageAdapter } from "./LanceDBStorageAdapter.js";

// Re-export types
export type {
  TokenBudgetConfig,
  TokenUsage,
  BudgetAlert,
  MessageHistoryConfig,
  ContextManagerConfig,
  UserMessage,
  ContextState,
  ContextInjectionResult,
  ProcessingContext,
  AgentStartEvent,
  AgentEndEvent,
  SessionResetEvent,
  CompressionResult,
  CompressionConfig,
  MultiAgentContextConfig,
  AgentContext,
  AgentResult,
  ForkContext,
  MergeOptions,
  MergeResult,
  CoordinatorState,
  WorkerContext,
  TaskResult,
  WorkflowPhase,
  TaskNotification,
  TaskNotificationConfig,
  TaskNotificationQuery,
} from "../types/index.js";
