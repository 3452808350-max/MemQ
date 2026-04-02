

### 2. PriorityQueue 模块 - 消息优先级管理

```typescript
// src/context/priority-queue.ts

/**
 * 消息优先级级别（5级）
 * - P0 (Critical): 系统提示词、当前指令
 * - P1 (High): 最近的用户消息、关键工具结果
 * - P2 (Medium): 重要的历史消息、Agent 决策
 * - P3 (Low): 一般历史消息、辅助信息
 * - P4 (Compressible): 可压缩/摘要的旧消息
 */

export enum MessagePriority {
  CRITICAL = 0,    // P0 - 绝对不能删除
  HIGH = 1,        // P1 - 优先保留
  MEDIUM = 2,      // P2 - 中等优先级
  LOW = 3,         // P3 - 低优先级
  COMPRESSIBLE = 4, // P4 - 可压缩/摘要
}

export interface PrioritizedMessage {
  id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string | ContentBlock[];
  priority: MessagePriority;
  timestamp: number;
  tokenCount: number;
  metadata?: {
    isSystemPrompt?: boolean;
    isCurrentInstruction?: boolean;
    hasToolUse?: boolean;
    hasToolResult?: boolean;
    isForkBoilerplate?: boolean;
    isCoordinatorDirective?: boolean;
    source?: 'memory' | 'session' | 'user';
  };
}

export type ContentBlock =
  | { type: 'text'; text: string }
  | { type: 'tool_use'; id: string; name: string; input: unknown }
  | { type: 'tool_result'; tool_use_id: string; content: ContentBlock[] };

export interface PriorityQueueConfig {
  maxSize?: number;
  priorityWeights?: Record<MessagePriority, number>;
  autoCompressThreshold?: number; // 队列满时的自动压缩阈值
}

export class PriorityQueue {
  private messages: PrioritizedMessage[] = [];
  private config: PriorityQueueConfig;
  private totalTokens: number = 0;

  constructor(config: PriorityQueueConfig = {}) {
    this.config = {
      maxSize: config.maxSize ?? 1000,
      priorityWeights: config.priorityWeights ?? {
        [MessagePriority.CRITICAL]: 100,
        [MessagePriority.HIGH]: 10,
        [MessagePriority.MEDIUM]: 5,
        [MessagePriority.LOW]: 2,
        [MessagePriority.COMPRESSIBLE]: 1,
      },
      autoCompressThreshold: config.autoCompressThreshold ?? 0.9,
    };
  }

  /**
   * 添加消息到队列
   */
  enqueue(message: Omit<PrioritizedMessage, 'id' | 'timestamp'>): PrioritizedMessage {
    const fullMessage: PrioritizedMessage = {
      ...message,
      id: this.generateId(),
      timestamp: Date.now(),
    };

    // 按优先级和时间排序插入
    const insertIndex = this.findInsertIndex(fullMessage);
    this.messages.splice(insertIndex, 0, fullMessage);
    this.totalTokens += message.tokenCount;

    // 检查是否需要自动压缩
    if (this.shouldAutoCompress()) {
      this.compressLowestPriority();
    }

    return fullMessage;
  }

  /**
   * 查找插入位置（按优先级降序，同优先级按时间升序）
   */
  private findInsertIndex(message: PrioritizedMessage): number {
    for (let i = 0; i < this.messages.length; i++) {
      const existing = this.messages[i];
      if (message.priority < existing.priority) {
        return i;
      }
      if (message.priority === existing.priority && message.timestamp < existing.timestamp) {
        return i;
      }
    }
    return this.messages.length;
  }

  /**
   * 从队列移除消息
   */
  dequeue(): PrioritizedMessage | undefined {
    const message = this.messages.pop();
    if (message) {
      this.totalTokens -= message.tokenCount;
    }
    return message;
  }

  /**
   * 获取指定优先级的所有消息
   */
  getByPriority(priority: MessagePriority): PrioritizedMessage[] {
    return this.messages.filter(m => m.priority === priority);
  }

  /**
   * 获取可压缩的消息（P4）
   */
  getCompressibleMessages(): PrioritizedMessage[] {
    return this.getByPriority(MessagePriority.COMPRESSIBLE);
  }

  /**
   * 获取消息列表（按优先级排序）
   */
  getAll(): PrioritizedMessage[] {
    return [...this.messages];
  }

  /**
   * 获取总 Token 数
   */
  getTotalTokens(): number {
    return this.totalTokens;
  }

  /**
   * 获取特定优先级以上的消息
   */
  getAbovePriority(minPriority: MessagePriority): PrioritizedMessage[] {
    return this.messages.filter(m => m.priority <= minPriority);
  }

  /**
   * 批量更新优先级
   */
  updatePriorities(updates: Array<{ id: string; newPriority: MessagePriority }>): void {
    for (const update of updates) {
      const message = this.messages.find(m => m.id === update.id);
      if (message) {
        message.priority = update.newPriority;
      }
    }
    // 重新排序
    this.messages.sort((a, b) => {
      if (a.priority !== b.priority) {
        return a.priority - b.priority;
      }
      return a.timestamp - b.timestamp;
    });
  }

  /**
   * 移除指定 ID 的消息
   */
  remove(id: string): boolean {
    const index = this.messages.findIndex(m => m.id === id);
    if (index === -1) return false;
    
    const message = this.messages[index];
    this.totalTokens -= message.tokenCount;
    this.messages.splice(index, 1);
    return true;
  }

  /**
   * 批量移除（用于压缩）
   */
  removeBatch(ids: string[]): number {
    let removed = 0;
    for (const id of ids) {
      if (this.remove(id)) removed++;
    }
    return removed;
  }

  /**
   * 检查是否需要自动压缩
   */
  private shouldAutoCompress(): boolean {
    if (!this.config.maxSize) return false;
    return this.messages.length > this.config.maxSize * this.config.autoCompressThreshold!;
  }

  /**
   * 压缩最低优先级消息
   */
  private compressLowestPriority(): void {
    const compressible = this.getCompressibleMessages();
    if (compressible.length === 0) return;

    // 移除最旧的 P4 消息（保留数量的一半）
    const toRemove = compressible.slice(0, Math.floor(compressible.length / 2));
    this.removeBatch(toRemove.map(m => m.id));
  }

  /**
   * 生成唯一 ID
   */
  private generateId(): string {
    return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 清空队列
   */
  clear(): void {
    this.messages = [];
    this.totalTokens = 0;
  }

  /**
   * 获取队列统计
   */
  getStats(): {
    totalMessages: number;
    totalTokens: number;
    byPriority: Record<MessagePriority, number>;
  } {
    const byPriority: Record<MessagePriority, number> = {
      [MessagePriority.CRITICAL]: 0,
      [MessagePriority.HIGH]: 0,
      [MessagePriority.MEDIUM]: 0,
      [MessagePriority.LOW]: 0,
      [MessagePriority.COMPRESSIBLE]: 0,
    };

    for (const message of this.messages) {
      byPriority[message.priority]++;
    }

    return {
      totalMessages: this.messages.length,
      totalTokens: this.totalTokens,
      byPriority,
    };
  }
}

/**
 * 优先级计算器 - 根据消息特征自动计算优先级
 */
export class PriorityCalculator {
  /**
   * 计算消息优先级
   */
  static calculate(
    role: PrioritizedMessage['role'],
    content: string | ContentBlock[],
    metadata?: PrioritizedMessage['metadata'],
    recency: 'new' | 'recent' | 'old' = 'recent'
  ): MessagePriority {
    // P0: 绝对不能删除的消息
    if (metadata?.isSystemPrompt) {
      return MessagePriority.CRITICAL;
    }
    if (metadata?.isCurrentInstruction) {
      return MessagePriority.CRITICAL;
    }
    if (metadata?.isForkBoilerplate) {
      return MessagePriority.CRITICAL;
    }

    // P1: 高优先级
    if (role === 'user' && recency === 'new') {
      return MessagePriority.HIGH;
    }
    if (metadata?.hasToolResult && recency === 'new') {
      return MessagePriority.HIGH;
    }
    if (metadata?.isCoordinatorDirective) {
      return MessagePriority.HIGH;
    }

    // P2: 中等优先级
    if (role === 'assistant' && recency === 'new') {
      return MessagePriority.MEDIUM;
    }
    if (metadata?.hasToolUse && recency === 'recent') {
      return MessagePriority.MEDIUM;
    }

    // P3: 低优先级
    if (recency === 'recent') {
      return MessagePriority.LOW;
    }

    // P4: 可压缩
    return MessagePriority.COMPRESSIBLE;
  }

  /**
   * 根据时间计算消息新旧程度
   */
  static calculateRecency(
    timestamp: number,
    now: number = Date.now()
  ): 'new' | 'recent' | 'old' {
    const age = now - timestamp;
    if (age < 60000) return 'new';        // < 1 minute
    if (age < 600000) return 'recent';    // < 10 minutes
    return 'old';                         // >= 10