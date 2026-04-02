/**
 * MessageHistory - 消息历史管理模块
 * 
 * 核心功能：
 * 1. 消息存储
 * 2. 消息优先级分层
 * 3. FIFO 截断策略
 */

import {
  UserMessage,
  MessageWithPriority,
  MessageHistoryConfig,
  TruncationResult,
  PriorityLayerConfig,
  DEFAULT_MESSAGE_HISTORY_CONFIG,
} from "../types/index.js";
import { TokenEstimator } from "../types/index.js";
import { DefaultTokenEstimator } from "./TokenBudget.js";
import { PriorityTruncator } from "./PriorityTruncator.js";
import { LLMCompressor } from "./LLMCompressor.js";

/**
 * 消息历史管理器
 */
export class MessageHistory {
  private config: MessageHistoryConfig;
  private messages: MessageWithPriority[];
  private estimator: TokenEstimator;
  private currentTurn: number = 0;
  private priorityTruncator: PriorityTruncator;
  private compressor: LLMCompressor;

  constructor(
    config: Partial<MessageHistoryConfig> = {},
    estimator?: TokenEstimator
  ) {
    this.config = { ...DEFAULT_MESSAGE_HISTORY_CONFIG, ...config };
    this.messages = [];
    this.estimator = estimator || new DefaultTokenEstimator();
    this.priorityTruncator = new PriorityTruncator(
      this.config.priorityLayers,
      this.estimator
    );
    this.compressor = new LLMCompressor();
  }

  /**
   * 添加消息
   */
  addMessage(message: UserMessage): void {
    // 计算优先级
    const priority = this.calculatePriority(message);
    const layer = this.assignLayer(message);

    const messageWithPriority: MessageWithPriority = {
      ...message,
      priority,
      layer,
      ageInTurns: 0,
    };

    // 更新所有消息的 ageInTurns
    this.messages.forEach((msg) => {
      msg.ageInTurns++;
    });

    this.messages.push(messageWithPriority);
    this.currentTurn++;

    // 检查是否需要触发截断
    this.checkAndTruncate();
  }

  /**
   * 批量添加消息
   */
  addMessages(messages: UserMessage[]): void {
    for (const message of messages) {
      this.addMessage(message);
    }
  }

  /**
   * 获取消息列表
   */
  getMessages(limit?: number): MessageWithPriority[] {
    if (limit) {
      return this.messages.slice(-limit);
    }
    return [...this.messages];
  }

  /**
   * 获取消息数量
   */
  getMessageCount(): number {
    return this.messages.length;
  }

  /**
   * 获取总 token 数
   */
  getTokenCount(): number {
    return this.messages.reduce((total, msg) => {
      return total + this.estimator.estimateMessage(msg);
    }, 0);
  }

  /**
   * 清空消息历史
   */
  clear(): void {
    this.messages = [];
    this.currentTurn = 0;
  }

  /**
   * 截断到目标 token 数
   * P0 阶段使用 FIFO 策略
   */
  truncate(targetTokens: number): TruncationResult {
    const currentTokens = this.getTokenCount();
    if (currentTokens <= targetTokens) {
      return {
        removed: [],
        retained: [...this.messages],
        tokensFreed: 0,
      };
    }

    // P0: 使用 FIFO 策略
    return this.truncateFIFO(targetTokens);
  }

  /**
   * FIFO 截断 - 移除最旧的消息
   */
  truncateFIFO(targetTokens: number): TruncationResult {
    const sorted = [...this.messages].sort((a, b) => a.ageInTurns - b.ageInTurns);
    const removed: MessageWithPriority[] = [];
    const retained: MessageWithPriority[] = [];
    let currentTokens = this.getTokenCount();

    for (const msg of sorted) {
      if (currentTokens <= targetTokens) {
        retained.push(msg);
      } else {
        const msgTokens = this.estimator.estimateMessage(msg);
        removed.push(msg);
        currentTokens -= msgTokens;
      }
    }

    // 更新内部状态
    this.messages = retained.sort((a, b) => b.timestamp - a.timestamp);

    return {
      removed,
      retained,
      tokensFreed: this.getTokenCount() - currentTokens,
    };
  }

  /**
   * 按数量截断
   */
  truncateByCount(count: number): TruncationResult {
    if (this.messages.length <= count) {
      return {
        removed: [],
        retained: [...this.messages],
        tokensFreed: 0,
      };
    }

    // P0: FIFO 策略
    const sorted = [...this.messages].sort((a, b) => a.ageInTurns - b.ageInTurns);
    const removed = sorted.slice(0, sorted.length - count);
    const retained = sorted.slice(-count);

    this.messages = retained.sort((a, b) => b.timestamp - a.timestamp);

    const tokensFreed = removed.reduce((total, msg) => {
      return total + this.estimator.estimateMessage(msg);
    }, 0);

    return {
      removed,
      retained,
      tokensFreed,
    };
  }

  /**
   * 检查并触发截断
   */
  private checkAndTruncate(): void {
    // 检查消息数
    if (this.messages.length > this.config.maxMessages) {
      this.truncateByCount(this.config.maxMessages);
    }

    // 检查 token 数
    const currentTokens = this.getTokenCount();
    if (currentTokens > this.config.compressionTrigger.tokenCount) {
      const targetTokens = Math.floor(
        this.config.compressionTrigger.tokenCount * 0.8
      );
      this.truncate(targetTokens);
    }
  }

  /**
   * 计算消息优先级
   * P0: 简单基于角色和内容的优先级
   */
  private calculatePriority(message: UserMessage): number {
    // 系统消息最高优先级
    if (message.role === "system") {
      return 10;
    }

    // 用户消息中等优先级
    if (message.role === "user") {
      // 检查是否包含决策关键词
      const content = typeof message.content === "string" ? message.content : "";
      if (/决定|decided|will use|改用|换成/i.test(content)) {
        return 7;
      }
      return 5;
    }

    // Assistant 消息基础优先级
    return 3;
  }

  /**
   * 分配消息到层级
   */
  private assignLayer(message: UserMessage): string {
    for (const layer of this.config.priorityLayers) {
      if (this.matchesSelector(message, layer.selector)) {
        return layer.name;
      }
    }
    return "default";
  }

  /**
   * 检查消息是否匹配选择器
   */
  private matchesSelector(
    message: UserMessage,
    selector: PriorityLayerConfig["selector"]
  ): boolean {
    switch (selector.type) {
      case "role":
        return message.role === selector.role;
      case "keyword":
        const content = typeof message.content === "string" ? message.content : "";
        return selector.keywords.some((kw) => content.includes(kw));
      case "pattern":
        const patternContent = typeof message.content === "string" ? message.content : "";
        return new RegExp(selector.regex).test(patternContent);
      case "tool":
        // P0: 简化处理，不检查 tool
        return false;
      case "custom":
        // P0: 不支持自定义函数
        return false;
      default:
        return false;
    }
  }

  /**
   * 获取配置
   */
  getConfig(): MessageHistoryConfig {
    return { ...this.config };
  }

  /**
   * 获取统计信息
   */
  getStats(): {
    messageCount: number;
    tokenCount: number;
    layerDistribution: Record<string, number>;
  } {
    const layerDistribution: Record<string, number> = {};
    this.messages.forEach((msg) => {
      layerDistribution[msg.layer] = (layerDistribution[msg.layer] || 0) + 1;
    });

    return {
      messageCount: this.messages.length,
      tokenCount: this.getTokenCount(),
      layerDistribution,
    };
  }

  // ==================== P1: 优先级截断 ====================

  /**
   * 使用优先级策略截断
   * 
   * P1: 替代 FIFO，按优先级层保留消息
   */
  truncateByPriority(targetTokens: number): TruncationResult {
    return this.priorityTruncator.truncate(this.messages, targetTokens);
  }

  /**
   * 压缩消息
   * 
   * P1: 使用 LLM 压缩长对话
   */
  async compressMessages(
    messages?: MessageWithPriority[],
    _compressionPrompt?: string
  ): Promise<{
    compressedSummary: string;
    tokensBefore: number;
    tokensAfter: number;
    compressionRatio: number;
  }> {
    const msgsToCompress = messages || this.messages;
    const result = await this.compressor.compress(msgsToCompress);
    return {
      compressedSummary: result.compressedSummary,
      tokensBefore: result.tokensBefore,
      tokensAfter: result.tokensAfter,
      compressionRatio: result.compressionRatio ?? 1,
    };
  }

  /**
   * 获取层统计
   * 
   * P1: 按优先级层统计消息分布
   */
  getLayerStats(): Record<string, number> {
    const stats: Record<string, number> = {};
    for (const msg of this.messages) {
      const layer = msg.layer || "unknown";
      stats[layer] = (stats[layer] || 0) + 1;
    }
    return stats;
  }

  /**
   * 移除指定轮次之前的消息
   * 
   * P1: 按年龄清理旧消息
   */
  removeOlderThan(turns: number): TruncationResult {
    const removed: MessageWithPriority[] = [];
    const retained: MessageWithPriority[] = [];

    for (const msg of this.messages) {
      if (msg.ageInTurns > turns) {
        removed.push(msg);
      } else {
        retained.push(msg);
      }
    }

    this.messages = retained;

    const tokensFreed = removed.reduce(
      (sum, m) => sum + this.estimator.estimateMessage(m),
      0
    );

    return {
      removed,
      retained,
      tokensFreed,
    };
  }
}

export default MessageHistory;
