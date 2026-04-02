/**
 * ContextManager - 上下文管理核心协调器
 * 
 * 核心功能：
 * 1. 初始化 TokenBudget 和 MessageHistory
 * 2. 处理消息注入上下文
 * 3. 生命周期钩子（Agent Start/End/Reset）
 * 4. 状态查询
 */

import {
  ContextManagerConfig,
  ProcessingContext,
  ContextInjectionResult,
  ContextState,
  AgentStartEvent,
  AgentEndEvent,
  SessionResetEvent,
  DEFAULT_CONTEXT_MANAGER_CONFIG,
} from "../types/index.js";
import { TokenBudget, DefaultTokenEstimator } from "./TokenBudget.js";
import { MessageHistory } from "./MessageHistory.js";

/**
 * 上下文管理器
 */
export class ContextManager {
  private config: ContextManagerConfig;
  private tokenBudget: TokenBudget;
  private messageHistory: MessageHistory;
  private activeAgents: Map<string, ProcessingContext> = new Map();

  constructor(config: Partial<ContextManagerConfig> = {}) {
    this.config = { ...DEFAULT_CONTEXT_MANAGER_CONFIG, ...config };
    const estimator = new DefaultTokenEstimator();
    this.tokenBudget = new TokenBudget(this.config.tokenBudget, estimator);
    this.messageHistory = new MessageHistory(this.config.messageHistory, estimator);
  }

  /**
   * 处理消息 - 主入口
   * P0: 简化版，只记录消息和检查预算
   */
  async processMessage(
    message: { id: string; role: string; content: string | unknown; timestamp: number },
    _context: ProcessingContext
  ): Promise<ContextInjectionResult> {
    // 记录消息到历史
    this.messageHistory.addMessage(message as any);

    // 估算消息 token
    const messageTokens = this.tokenBudget.estimate(
      typeof message.content === "string" ? message.content : JSON.stringify(message.content)
    );
    this.tokenBudget.recordConversationHistory(messageTokens);

    // 检查预算阈值
    const alert = this.tokenBudget.checkThresholds();

    // P0: 简化处理，不实际注入上下文
    const result: ContextInjectionResult = {
      contextToInject: "",
      injectedTokens: 0,
      reason: {
        type: alert ? "budget_exceeded" : "auto",
        description: alert
          ? `Budget ${alert.level}: ${alert.recommendedAction}`
          : "Normal processing",
      },
      strategy: alert?.recommendedAction === "truncate" ? "truncate" : "inject_memory",
      memoryReferences: [],
    };

    return result;
  }

  /**
   * 获取上下文状态
   */
  getContextState(): ContextState {
    const stats = this.messageHistory.getStats();
    return {
      currentTokens: stats.tokenCount,
      budgetUsage: this.tokenBudget.getUsagePercentage(),
      messageCount: stats.messageCount,
      activeAgents: Array.from(this.activeAgents.keys()),
      pendingTasks: [], // P0: 暂不实现任务追踪
    };
  }

  /**
   * Agent 启动钩子
   * P0: 记录活跃 Agent
   */
  async onAgentStart(event: AgentStartEvent): Promise<void> {
    const context: ProcessingContext = {
      sessionId: event.sessionId,
      agentId: event.agentId,
      parentAgentId: event.parentAgentId,
      isFork: event.isFork,
      isCoordinator: event.isCoordinator,
    };

    this.activeAgents.set(event.agentId, context);

    // 记录系统提示词（如果有）
    if (event.task) {
      const taskTokens = this.tokenBudget.estimate(event.task);
      this.tokenBudget.recordSystemPrompt(taskTokens);
    }
  }

  /**
   * Agent 结束钩子
   * P0: 移除活跃 Agent
   */
  async onAgentEnd(event: AgentEndEvent): Promise<void> {
    this.activeAgents.delete(event.agentId);

    // 记录结果
    if (event.result.output) {
      const outputTokens = this.tokenBudget.estimate(event.result.output);
      this.tokenBudget.recordToolResults(outputTokens);
    }
  }

  /**
   * 会话重置钩子
   */
  async onSessionReset(event: SessionResetEvent): Promise<void> {
    // 清空当前会话相关的 Agent
    for (const [agentId, context] of this.activeAgents) {
      if (context.sessionId === event.sessionId) {
        this.activeAgents.delete(agentId);
      }
    }

    // P0: 不重置预算和历史，保持跨会话连续性
    // P1: 可以考虑部分重置
  }

  /**
   * 获取 TokenBudget 实例
   */
  getTokenBudget(): TokenBudget {
    return this.tokenBudget;
  }

  /**
   * 获取 MessageHistory 实例
   */
  getMessageHistory(): MessageHistory {
    return this.messageHistory;
  }

  /**
   * 获取配置
   */
  getConfig(): ContextManagerConfig {
    return { ...this.config };
  }

  /**
   * 重置所有状态
   */
  reset(): void {
    this.tokenBudget.reset();
    this.messageHistory.clear();
    this.activeAgents.clear();
  }
}

export default ContextManager;
