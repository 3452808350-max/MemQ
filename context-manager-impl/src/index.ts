/**
 * Context Manager - Main Entry Point
 * 
 * OpenClaw Context Memory Plugin
 * 基于 Claude Code 上下文管理 + OpenClaw 短期记忆融合方案
 */

// 导出核心类
export {
  TokenBudget,
  DefaultTokenEstimator,
  MessageHistory,
  ContextManager,
  MultiAgentContext,
  ForkManager,
  CoordinatorManager,
  MergeManager,
  TaskNotificationService,
  buildTaskNotificationXML,
  parseTaskNotificationXML,
  createTaskNotification,
} from "./core/index.js";

// 导出类型定义
export * from "./types/index.js";

// 导出默认配置
export {
  DEFAULT_TOKEN_BUDGET_CONFIG,
  DEFAULT_MESSAGE_HISTORY_CONFIG,
  DEFAULT_PRIORITY_LAYERS,
  DEFAULT_MULTI_AGENT_CONFIG,
  DEFAULT_TASK_NOTIFICATION_CONFIG,
  DEFAULT_CONTEXT_MANAGER_CONFIG,
  DEFAULT_COMPRESSION_CONFIG,
} from "./types/index.js";