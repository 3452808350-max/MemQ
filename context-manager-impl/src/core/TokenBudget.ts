/**
 * TokenBudget - Token 预算管理模块
 * 
 * 核心功能：
 * 1. 预算分配和跟踪
 * 2. 阈值检测（warning/critical）
 * 3. 紧急释放机制
 */

import {
  TokenBudgetConfig,
  TokenUsage,
  BudgetAlert,
  TokenEstimator,
  DEFAULT_TOKEN_BUDGET_CONFIG,
} from "../types/index.js";

/**
 * 默认 Token 估算器
 * 基于字符数的快速估算
 */
export class DefaultTokenEstimator implements TokenEstimator {
  estimateText(text: string): number {
    // 简单估算：英文约 4 字符/token，中文约 1.5 字符/token
    // 混合内容使用保守估算
    const charCount = text.length;
    // 检测中文字符比例
    const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
    const chineseRatio = chineseChars / charCount;
    
    // 混合估算
    const avgCharsPerToken = 4 * (1 - chineseRatio) + 1.5 * chineseRatio;
    return Math.ceil(charCount / avgCharsPerToken);
  }

  estimateMessage(msg: { content: string | unknown }): number {
    if (typeof msg.content === "string") {
      return this.estimateText(msg.content);
    }
    // 处理复杂内容结构
    return this.estimateText(JSON.stringify(msg.content));
  }

  estimateContext(context: string): number {
    return this.estimateText(context);
  }
}

/**
 * Token 预算管理器
 */
export class TokenBudget {
  private config: TokenBudgetConfig;
  private usage: TokenUsage;
  private estimator: TokenEstimator;
  private allocations: Map<string, number> = new Map();

  constructor(
    config: Partial<TokenBudgetConfig> = {},
    estimator?: TokenEstimator
  ) {
    this.config = { ...DEFAULT_TOKEN_BUDGET_CONFIG, ...config };
    this.estimator = estimator || new DefaultTokenEstimator();
    this.usage = {
      systemPrompt: 0,
      conversationHistory: 0,
      injectedMemories: 0,
      toolResults: 0,
      thinkingBlocks: 0,
      reserved: 0,
      total: 0,
    };
  }

  /**
   * 获取总预算
   */
  getTotalBudget(): number {
    return this.config.totalBudget;
  }

  /**
   * 获取可用预算（总预算 - 已用 - 保留）
   */
  getAvailableBudget(): number {
    return this.config.totalBudget - this.usage.total - this.config.reserveBudget;
  }

  /**
   * 获取当前使用量
   */
  getCurrentUsage(): TokenUsage {
    return { ...this.usage };
  }

  /**
   * 获取使用百分比
   */
  getUsagePercentage(): number {
    return this.usage.total / this.config.totalBudget;
  }

  /**
   * 检查阈值
   * 返回警告信息或 null
   */
  checkThresholds(): BudgetAlert | null {
    const percentage = this.getUsagePercentage();

    if (percentage >= this.config.criticalThreshold) {
      return {
        level: "critical",
        currentUsage: this.usage.total,
        threshold: this.config.criticalThreshold,
        recommendedAction: "truncate",
      };
    }

    if (percentage >= this.config.warningThreshold) {
      return {
        level: "warning",
        currentUsage: this.usage.total,
        threshold: this.config.warningThreshold,
        recommendedAction: "compress",
      };
    }

    return null;
  }

  /**
   * 为响应分配预算
   */
  allocateForResponse(estimatedTokens: number): boolean {
    const available = this.getAvailableBudget();
    if (estimatedTokens > available) {
      return false;
    }
    this.usage.reserved += estimatedTokens;
    this.usage.total += estimatedTokens;
    return true;
  }

  /**
   * 释放分配的预算
   */
  releaseAllocation(tokens: number): void {
    this.usage.reserved = Math.max(0, this.usage.reserved - tokens);
    this.usage.total = Math.max(0, this.usage.total - tokens);
  }

  /**
   * 紧急释放 - 释放保留预算
   */
  emergencyRelease(): number {
    const released = this.usage.reserved;
    this.usage.total -= released;
    this.usage.reserved = 0;
    return released;
  }

  /**
   * 记录系统提示词使用
   */
  recordSystemPrompt(tokens: number): void {
    this.usage.systemPrompt += tokens;
    this.usage.total += tokens;
  }

  /**
   * 记录对话历史使用
   */
  recordConversationHistory(tokens: number): void {
    this.usage.conversationHistory += tokens;
    this.usage.total += tokens;
  }

  /**
   * 记录注入记忆使用
   */
  recordInjectedMemories(tokens: number): void {
    this.usage.injectedMemories += tokens;
    this.usage.total += tokens;
  }

  /**
   * 记录工具结果使用
   */
  recordToolResults(tokens: number): void {
    this.usage.toolResults += tokens;
    this.usage.total += tokens;
  }

  /**
   * 记录思考块使用
   */
  recordThinkingBlocks(tokens: number): void {
    this.usage.thinkingBlocks += tokens;
    this.usage.total += tokens;
  }

  /**
   * 估算文本 token 数
   */
  estimate(text: string): number {
    return this.estimator.estimateText(text);
  }

  /**
   * 获取配置
   */
  getConfig(): TokenBudgetConfig {
    return { ...this.config };
  }

  /**
   * 重置预算
   */
  reset(): void {
    this.usage = {
      systemPrompt: 0,
      conversationHistory: 0,
      injectedMemories: 0,
      toolResults: 0,
      thinkingBlocks: 0,
      reserved: 0,
      total: 0,
    };
    this.allocations.clear();
  }
}

export default TokenBudget;
