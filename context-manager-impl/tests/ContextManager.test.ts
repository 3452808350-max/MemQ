import { describe, it, expect, beforeEach } from "vitest";
import { ContextManager } from "../src/core/ContextManager.js";
import { AgentStartEvent, AgentEndEvent } from "../src/types/index.js";

describe("ContextManager", () => {
  let manager: ContextManager;

  beforeEach(() => {
    manager = new ContextManager({
      tokenBudget: {
        totalBudget: 1000,
        reserveBudget: 200,
        warningThreshold: 0.8,
        criticalThreshold: 0.95,
      },
      messageHistory: {
        maxMessages: 10,
        truncationStrategy: "fifo",
      },
    });
  });

  const createMessage = (id: string, role: string, content: string) => ({
    id,
    role,
    content,
    timestamp: Date.now(),
  });

  describe("Initialization", () => {
    it("should initialize with config", () => {
      const config = manager.getConfig();
      expect(config.tokenBudget.totalBudget).toBe(1000);
      expect(config.messageHistory.maxMessages).toBe(10);
    });

    it("should have empty state initially", () => {
      const state = manager.getContextState();
      expect(state.currentTokens).toBe(0);
      expect(state.messageCount).toBe(0);
      expect(state.activeAgents).toHaveLength(0);
    });
  });

  describe("Message Processing", () => {
    it("should process messages", async () => {
      const result = await manager.processMessage(
        createMessage("1", "user", "Hello"),
        { sessionId: "test-session" }
      );

      expect(result.injectedTokens).toBe(0); // P0: no actual injection
      expect(result.reason.type).toBe("auto");
    });

    it("should track messages in history", async () => {
      await manager.processMessage(
        createMessage("1", "user", "Hello"),
        { sessionId: "test-session" }
      );

      const state = manager.getContextState();
      expect(state.messageCount).toBe(1);
    });

    it("should track token usage", async () => {
      await manager.processMessage(
        createMessage("1", "user", "Hello world, this is a test message"),
        { sessionId: "test-session" }
      );

      const state = manager.getContextState();
      expect(state.currentTokens).toBeGreaterThan(0);
    });

    it("should detect budget alerts", async () => {
      // Create manager with very small budget to trigger alert
      const smallBudgetManager = new ContextManager({
        tokenBudget: {
          totalBudget: 100,  // Very small budget
          reserveBudget: 10,
          warningThreshold: 0.5,  // Alert at 50%
          criticalThreshold: 0.9,
        },
        messageHistory: {
          maxMessages: 100,
          truncationStrategy: "fifo",
        },
      });

      // Directly record tokens to trigger alert
      const budget = smallBudgetManager.getTokenBudget();
      budget.recordConversationHistory(60); // 60% usage

      // Now process a message - should detect budget exceeded
      const result = await smallBudgetManager.processMessage(
        createMessage("last", "user", "Trigger"),
        { sessionId: "test-session" }
      );

      // Should have detected budget issue
      expect(result.reason.type).toBe("budget_exceeded");
    });
  });

  describe("Agent Lifecycle", () => {
    it("should track active agents on start", async () => {
      const event: AgentStartEvent = {
        agentId: "agent-1",
        sessionId: "session-1",
        task: "Test task",
      };

      await manager.onAgentStart(event);

      const state = manager.getContextState();
      expect(state.activeAgents).toContain("agent-1");
    });

    it("should remove agents on end", async () => {
      await manager.onAgentStart({
        agentId: "agent-1",
        sessionId: "session-1",
        task: "Test",
      });

      await manager.onAgentEnd({
        agentId: "agent-1",
        sessionId: "session-1",
        result: {
          status: "completed",
          output: "Done",
          usage: { totalTokens: 100, toolUses: 5, durationMs: 1000 },
        },
      });

      const state = manager.getContextState();
      expect(state.activeAgents).not.toContain("agent-1");
    });

    it("should track fork agents", async () => {
      await manager.onAgentStart({
        agentId: "fork-1",
        sessionId: "session-1",
        task: "Fork task",
        isFork: true,
        parentAgentId: "main-agent",
      });

      const state = manager.getContextState();
      expect(state.activeAgents).toContain("fork-1");
    });

    it("should track coordinator agents", async () => {
      await manager.onAgentStart({
        agentId: "coordinator-1",
        sessionId: "session-1",
        task: "Coordinate task",
        isCoordinator: true,
      });

      const state = manager.getContextState();
      expect(state.activeAgents).toContain("coordinator-1");
    });
  });

  describe("Reset", () => {
    it("should reset all state", async () => {
      await manager.processMessage(
        createMessage("1", "user", "Hello"),
        { sessionId: "test-session" }
      );

      await manager.onAgentStart({
        agentId: "agent-1",
        sessionId: "test-session",
        task: "Test",
      });

      manager.reset();

      const state = manager.getContextState();
      expect(state.messageCount).toBe(0);
      expect(state.activeAgents).toHaveLength(0);
    });
  });

  describe("Component Access", () => {
    it("should provide access to TokenBudget", () => {
      const budget = manager.getTokenBudget();
      expect(budget).toBeDefined();
      expect(budget.getTotalBudget()).toBe(1000);
    });

    it("should provide access to MessageHistory", () => {
      const history = manager.getMessageHistory();
      expect(history).toBeDefined();
      expect(history.getMessageCount()).toBe(0);
    });
  });
});
