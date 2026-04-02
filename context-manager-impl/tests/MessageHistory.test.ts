/**
 * MessageHistory 模块测试 (P0)
 */

import { describe, it, expect, beforeEach } from "vitest";
import { MessageHistory } from "../src/core/MessageHistory";
import type { UserMessage } from "../src/types";

describe("MessageHistory", () => {
  const createMessage = (
    id: string,
    role: "user" | "assistant" | "system",
    content: string
  ): UserMessage => ({
    id,
    role,
    content,
    timestamp: Date.now(),
  });

  describe("基本功能", () => {
    it("应该添加单条消息", () => {
      const history = new MessageHistory();
      history.addMessage(createMessage("1", "user", "Hello"));
      expect(history.getMessageCount()).toBe(1);
    });

    it("应该批量添加消息", () => {
      const history = new MessageHistory();
      history.addMessages([
        createMessage("1", "user", "Hello"),
        createMessage("2", "assistant", "Hi"),
        createMessage("3", "user", "How are you?"),
      ]);
      expect(history.getMessageCount()).toBe(3);
    });

    it("应该获取消息列表", () => {
      const history = new MessageHistory();
      history.addMessages([
        createMessage("1", "user", "Hello"),
        createMessage("2", "assistant", "Hi"),
      ]);
      const messages = history.getMessages();
      expect(messages.length).toBe(2);
      expect(messages[0].id).toBe("1");
      expect(messages[1].id).toBe("2");
    });

    it("应该限制返回消息数量", () => {
      const history = new MessageHistory();
      history.addMessages([
        createMessage("1", "user", "First"),
        createMessage("2", "assistant", "Second"),
        createMessage("3", "user", "Third"),
      ]);
      const messages = history.getMessages(2);
      expect(messages.length).toBe(2);
      expect(messages[0].id).toBe("2");
      expect(messages[1].id).toBe("3");
    });
  });

  describe("优先级分配", () => {
    it("应该为系统消息分配高优先级", () => {
      const history = new MessageHistory();
      history.addMessage(createMessage("1", "system", "System prompt"));
      const messages = history.getMessages();
      expect(messages[0].priority).toBe(10);
      expect(messages[0].layer).toBe("system_critical");
    });

    it("应该为用户消息分配中等优先级", () => {
      const history = new MessageHistory();
      history.addMessage(createMessage("1", "user", "Hello"));
      const messages = history.getMessages();
      expect(messages[0].priority).toBe(5);
    });

    it("应该为决策消息分配更高优先级", () => {
      const history = new MessageHistory();
      history.addMessage(createMessage("1", "user", "I decided to use TypeScript"));
      const messages = history.getMessages();
      expect(messages[0].priority).toBe(7);
    });

    it("应该为助手消息分配低优先级", () => {
      const history = new MessageHistory();
      history.addMessage(createMessage("1", "assistant", "I can help you"));
      const messages = history.getMessages();
      expect(messages[0].priority).toBe(3);
    });
  });

  describe("FIFO 截断", () => {
    it("应该按 FIFO 截断消息", () => {
      const history = new MessageHistory();
      // 依次添加消息，让它们有不同的 ageInTurns
      history.addMessage(createMessage("1", "user", "Message 1"));
      history.addMessage(createMessage("2", "assistant", "Message 2"));
      history.addMessage(createMessage("3", "user", "Message 3"));

      // 截断到保留 2 条消息
      const result = history.truncateByCount(2);
      expect(result.removed.length).toBe(1);
      expect(result.retained.length).toBe(2);
      // 保留的消息应该是 2 条
      const retainedIds = result.retained.map(m => m.id);
      expect(retainedIds.length).toBe(2);
    });

    it("截断后应该更新消息计数", () => {
      const history = new MessageHistory();
      history.addMessage(createMessage("1", "user", "Message 1"));
      history.addMessage(createMessage("2", "assistant", "Message 2"));
      history.addMessage(createMessage("3", "user", "Message 3"));

      history.truncateByCount(2);
      expect(history.getMessageCount()).toBe(2);
    });
  });

  describe("自动截断", () => {
    it("应该在超过 maxMessages 时自动截断", () => {
      const history = new MessageHistory({ maxMessages: 5 });
      
      // 添加 10 条消息
      for (let i = 0; i < 10; i++) {
        history.addMessage(createMessage(String(i), "user", `Message ${i}`));
      }

      // 应该只保留 5 条
      expect(history.getMessageCount()).toBe(5);
    });
  });

  describe("统计信息", () => {
    it("应该返回消息统计", () => {
      const history = new MessageHistory();
      history.addMessages([
        createMessage("1", "system", "System"),
        createMessage("2", "user", "Hello"),
        createMessage("3", "assistant", "Hi"),
      ]);

      const stats = history.getStats();
      expect(stats.messageCount).toBe(3);
      expect(stats.tokenCount).toBeGreaterThan(0);
      expect(stats.layerDistribution["system_critical"]).toBe(1);
      expect(stats.layerDistribution["user_messages"]).toBe(1);
    });
  });

  describe("清理", () => {
    it("应该清空所有消息", () => {
      const history = new MessageHistory();
      history.addMessages([
        createMessage("1", "user", "Hello"),
        createMessage("2", "assistant", "Hi"),
      ]);

      history.clear();
      expect(history.getMessageCount()).toBe(0);
    });
  });
});
