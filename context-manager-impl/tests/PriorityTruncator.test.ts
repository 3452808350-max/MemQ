/**
 * PriorityTruncator 模块测试 (P1)
 */

import { describe, it, expect, beforeEach } from "vitest";
import { PriorityTruncator } from "../src/core/PriorityTruncator";
import { DefaultTokenEstimator } from "../src/core/TokenBudget";
import type { MessageWithPriority, PriorityLayerConfig } from "../src/types";

describe("PriorityTruncator", () => {
  const estimator = new DefaultTokenEstimator();

  const createMessage = (
    id: string,
    role: "user" | "assistant" | "system",
    content: string,
    layer: string,
    priority: number
  ): MessageWithPriority => ({
    id,
    role,
    content,
    timestamp: Date.now(),
    layer,
    priority,
    ageInTurns: 0,
  });

  const testLayers: PriorityLayerConfig[] = [
    { name: "system_critical", priority: 10, selector: { type: "role", role: "system" }, minKeep: 1, maxKeep: 5 },
    { name: "user_decisions", priority: 7, selector: { type: "pattern", regex: "决定" }, minKeep: 2, maxKeep: 5 },
    { name: "user_messages", priority: 5, selector: { type: "role", role: "user" }, minKeep: 3, maxKeep: 10 },
    { name: "assistant_responses", priority: 3, selector: { type: "role", role: "assistant" }, minKeep: 2, maxKeep: 8 },
  ];

  describe("基本功能", () => {
    it("应该保留空消息列表", () => {
      const truncator = new PriorityTruncator(testLayers, estimator);
      const result = truncator.truncate([], 1000);
      expect(result.removed).toHaveLength(0);
      expect(result.retained).toHaveLength(0);
      expect(result.tokensFreed).toBe(0);
    });

    it("如果 token 在目标内，不应截断", () => {
      const truncator = new PriorityTruncator(testLayers, estimator);
      const messages = [
        createMessage("1", "user", "Hello", "user_messages", 5),
        createMessage("2", "assistant", "Hi", "assistant_responses", 3),
      ];

      const result = truncator.truncate(messages, 10000);
      expect(result.removed).toHaveLength(0);
      expect(result.retained).toHaveLength(2);
    });

    it("应该按优先级保留消息", () => {
      const truncator = new PriorityTruncator(testLayers, estimator);
      const messages = [
        createMessage("1", "system", "System prompt", "system_critical", 10),
        createMessage("2", "user", "Hello", "user_messages", 5),
        createMessage("3", "assistant", "Hi", "assistant_responses", 3),
      ];

      // 设置很小的目标，强制截断
      const result = truncator.truncate(messages, 10);

      // 系统消息应该被保留（最高优先级）
      const retainedIds = result.retained.map(m => m.id);
      expect(retainedIds).toContain("1");
    });
  });

  describe("优先级层约束", () => {
    it("应该保留每层至少 minKeep 条消息", () => {
      const truncator = new PriorityTruncator(testLayers, estimator);
      const messages = [
        createMessage("1", "system", "System 1", "system_critical", 10),
        createMessage("2", "system", "System 2", "system_critical", 10),
        createMessage("3", "user", "User 1", "user_messages", 5),
        createMessage("4", "user", "User 2", "user_messages", 5),
        createMessage("5", "user", "User 3", "user_messages", 5),
        createMessage("6", "assistant", "Assistant 1", "assistant_responses", 3),
        createMessage("7", "assistant", "Assistant 2", "assistant_responses", 3),
      ];

      const result = truncator.truncate(messages, 500);

      // 统计每层保留的数量
      const layerCounts: Record<string, number> = {};
      result.retained.forEach(m => {
        layerCounts[m.layer] = (layerCounts[m.layer] || 0) + 1;
      });

      // 验证 minKeep 约束
      expect(layerCounts["system_critical"] || 0).toBeGreaterThanOrEqual(1);
      expect(layerCounts["user_messages"] || 0).toBeGreaterThanOrEqual(3);
      expect(layerCounts["assistant_responses"] || 0).toBeGreaterThanOrEqual(2);
    });

    it("不应超过每层 maxKeep 条消息", () => {
      const truncator = new PriorityTruncator(testLayers, estimator);
      const messages: MessageWithPriority[] = [];

      // 创建大量用户消息
      for (let i = 0; i < 20; i++) {
        messages.push(createMessage(
          `user${i}`,
          "user",
          `Message ${i} with some longer content to consume tokens`,
          "user_messages",
          5
        ));
      }

      // 设置较小的目标，强制截断
      const result = truncator.truncate(messages, 100);

      // 统计用户消息层
      const userMsgCount = result.retained.filter(m => m.layer === "user_messages").length;
      expect(userMsgCount).toBeLessThanOrEqual(10); // maxKeep for user_messages
    });
  });

  describe("token 计算", () => {
    it("应该正确计算截断后的 token 数", () => {
      const truncator = new PriorityTruncator(testLayers, estimator);
      const messages = [
        createMessage("1", "user", "Hello world", "user_messages", 5),
        createMessage("2", "assistant", "Hi there", "assistant_responses", 3),
      ];

      const result = truncator.truncate(messages, 5);

      // 验证 tokensFreed 计算
      const removedTokens = result.removed.reduce(
        (sum, m) => sum + estimator.estimateMessage(m),
        0
      );
      expect(result.tokensFreed).toBe(removedTokens);
    });
  });
});
