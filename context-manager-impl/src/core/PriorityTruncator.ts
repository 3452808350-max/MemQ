/**
 * Priority Truncation Strategy
 * 
 * P1: 基于优先级的智能截断策略
 * - 按优先级层保留消息
 * - 每层内按时间/重要性排序
 * - 支持 minKeep/maxKeep 约束
 */

import {
  MessageWithPriority,
  PriorityLayerConfig,
  TruncationResult,
  DEFAULT_PRIORITY_LAYERS,
} from "../types/index.js";
import { TokenEstimator } from "../types/index.js";

/**
 * 优先级截断器
 */
export class PriorityTruncator {
  private layers: PriorityLayerConfig[];
  private estimator: TokenEstimator;

  constructor(
    layers: PriorityLayerConfig[] = DEFAULT_PRIORITY_LAYERS,
    estimator: TokenEstimator
  ) {
    this.layers = layers;
    this.estimator = estimator;
  }

  /**
   * 执行优先级截断
   * 
   * 策略：
   * 1. 按优先级排序层（高优先级优先保留）
   * 2. 每层保留消息直到达到 minKeep
   * 3. 如果还有空间，按优先级顺序填充到 maxKeep
   * 4. 最后按 token 目标微调
   */
  truncate(
    messages: MessageWithPriority[],
    targetTokens: number
  ): TruncationResult {
    if (messages.length === 0) {
      return { removed: [], retained: [], tokensFreed: 0 };
    }

    const currentTokens = messages.reduce(
      (sum, m) => sum + this.estimator.estimateMessage(m),
      0
    );

    if (currentTokens <= targetTokens) {
      return {
        removed: [],
        retained: [...messages],
        tokensFreed: 0,
      };
    }

    // 按层分组消息
    const messagesByLayer = this.groupByLayer(messages);
    
    // 按优先级排序层
    const sortedLayers = [...this.layers].sort((a, b) => b.priority - a.priority);
    
    const retained: MessageWithPriority[] = [];
    const removed: MessageWithPriority[] = [];
    let currentTokenCount = 0;

    // 阶段 1: 确保每层至少保留 minKeep
    for (const layer of sortedLayers) {
      const layerMessages = messagesByLayer.get(layer.name) || [];
      const toKeep = Math.min(layer.minKeep, layerMessages.length);
      
      // 按时间排序（最新的优先）
      const sortedMessages = [...layerMessages].sort(
        (a, b) => b.timestamp - a.timestamp
      );
      
      for (let i = 0; i < toKeep; i++) {
        const msg = sortedMessages[i];
        const tokens = this.estimator.estimateMessage(msg);
        
        if (currentTokenCount + tokens <= targetTokens) {
          retained.push(msg);
          currentTokenCount += tokens;
        } else {
          // 空间不足，移到 removed
          removed.push(...sortedMessages.slice(i));
          break;
        }
      }
    }

    // 阶段 2: 如果还有空间，按优先级填充到 maxKeep
    if (currentTokenCount < targetTokens) {
      for (const layer of sortedLayers) {
        const layerMessages = messagesByLayer.get(layer.name) || [];
        const alreadyKept = retained.filter(m => m.layer === layer.name).length;
        const canAdd = Math.min(layer.maxKeep - alreadyKept, layerMessages.length - alreadyKept);
        
        if (canAdd <= 0) continue;
        
        // 获取尚未保留的消息
        const remaining = layerMessages.filter(
          m => !retained.some(r => r.id === m.id)
        );
        
        // 按时间排序
        const sorted = [...remaining].sort((a, b) => b.timestamp - a.timestamp);
        
        for (const msg of sorted) {
          const tokens = this.estimator.estimateMessage(msg);
          
          if (currentTokenCount + tokens <= targetTokens) {
            retained.push(msg);
            currentTokenCount += tokens;
          } else {
            removed.push(msg);
          }
        }
      }
    }

    // 阶段 3: 将未保留的消息加入 removed
    for (const msg of messages) {
      if (!retained.some(r => r.id === msg.id) && !removed.some(r => r.id === msg.id)) {
        removed.push(msg);
      }
    }

    return {
      removed,
      retained,
      tokensFreed: removed.reduce(
        (sum, m) => sum + this.estimator.estimateMessage(m),
        0
      ),
    };
  }

  /**
   * 按层分组消息
   */
  private groupByLayer(
    messages: MessageWithPriority[]
  ): Map<string, MessageWithPriority[]> {
    const groups = new Map<string, MessageWithPriority[]>();
    
    for (const msg of messages) {
      const layer = msg.layer || "unknown";
      if (!groups.has(layer)) {
        groups.set(layer, []);
      }
      groups.get(layer)!.push(msg);
    }
    
    return groups;
  }

  /**
   * 计算截断后的 token 数
   */
  calculateTokenCount(messages: MessageWithPriority[]): number {
    return messages.reduce(
      (sum, m) => sum + this.estimator.estimateMessage(m),
      0
    );
  }
}
