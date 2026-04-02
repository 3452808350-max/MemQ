/**
 * LLMCompressor 模块测试 (P1)
 */

import { describe, it, expect, beforeEach } from "vitest";
import { LLMCompressor } from "../src/core/LLMCompressor";
import type { UserMessage } from "../src/types";

describe("LLMCompressor", () => {
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
    it("应该处理空消息列表", async () => {
      const compressor = new LLMCompressor();
      const result = await compressor.compress([]);

      expect(result.compressedSummary).toBe("");
      expect(result.tokensBefore).toBe(0);
      expect(result.tokensAfter).toBe(0);
      expect(result.compressionRatio).toBe(1);
    });

    it("应该生成摘要", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "Hello, how are you?"),
        createMessage("2", "assistant", "I'm doing well, thanks!"),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toBeTruthy();
      expect(result.compressedSummary.length).toBeGreaterThan(0);
    });

    it("应该计算压缩比率", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "This is a test message with some content"),
        createMessage("2", "assistant", "This is a response with even more content here"),
      ];

      const result = await compressor.compress(messages);

      expect(result.tokensBefore).toBeGreaterThan(0);
      expect(result.tokensAfter).toBeGreaterThan(0);
      expect(result.compressionRatio).toBeGreaterThan(0);
    });
  });

  describe("决策提取", () => {
    it("应该提取用户决策", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "我决定使用 TypeScript"),
        createMessage("2", "assistant", "好的，TypeScript 是个不错的选择"),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toContain("关键决策");
      expect(result.compressedSummary).toContain("TypeScript");
    });

    it("应该提取改用决策", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "我们改用新的方案"),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toContain("关键决策");
    });

    it("应该识别英文决策", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "I decided to use React"),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toContain("关键决策");
      expect(result.compressedSummary).toContain("React");
    });
  });

  describe("错误提取", () => {
    it("应该提取错误信息", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "I got an error: connection failed"),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toContain("错误与修复");
      expect(result.compressedSummary).toContain("connection failed");
    });

    it("应该提取中文错误", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "出现错误：网络连接失败"),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toContain("错误与修复");
    });
  });

  describe("主题提取", () => {
    it("应该识别代码相关主题", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "Let's write a function to handle this"),
        createMessage("2", "assistant", "Here's the code..."),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toContain("代码");
    });

    it("应该识别测试相关主题", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "We need to add more tests"),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toContain("测试");
    });

    it("应该识别调试相关主题", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "There's a bug in the code"),
      ];

      const result = await compressor.compress(messages);

      expect(result.compressedSummary).toContain("调试");
    });
  });

  describe("消息保留", () => {
    it("应该保留系统消息", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "system", "You are a helpful assistant"),
        createMessage("2", "user", "Hello"),
      ];

      const result = await compressor.compress(messages);

      expect(result.preservedMessages.length).toBeGreaterThanOrEqual(1);
      expect(result.preservedMessages.some(m => m.role === "system")).toBe(true);
    });

    it("应该保留包含决策的用户消息", async () => {
      const compressor = new LLMCompressor();
      const messages = [
        createMessage("1", "user", "我决定使用新的方案"),
        createMessage("2", "user", "普通消息"),
      ];

      const result = await compressor.compress(messages);

      expect(result.preservedMessages.some(m => m.id === "1")).toBe(true);
    });
  });

  describe("增量压缩", () => {
    it("应该合并现有摘要和新消息", async () => {
      const compressor = new LLMCompressor();
      const existingSummary = "## 之前的对话\n已完成初始设置";
      const newMessages = [
        createMessage("1", "user", "现在添加新功能"),
      ];

      const result = await compressor.compressIncremental(existingSummary, newMessages);

      expect(result.compressedSummary).toContain("之前的对话");
      expect(result.compressedSummary).toContain("新增内容");
    });

    it("应该处理空摘要", async () => {
      const compressor = new LLMCompressor();
      const newMessages = [
        createMessage("1", "user", "Hello"),
      ];

      const result = await compressor.compressIncremental("", newMessages);

      expect(result.compressedSummary).toBeTruthy();
      expect(result.compressedSummary).not.toContain("新增内容");
    });
  });
});
