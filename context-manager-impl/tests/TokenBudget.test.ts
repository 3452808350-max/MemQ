import { describe, it, expect, beforeEach } from "vitest";
import { TokenBudget, DefaultTokenEstimator } from "../src/core/TokenBudget.js";

describe("TokenBudget", () => {
  let budget: TokenBudget;

  beforeEach(() => {
    budget = new TokenBudget({
      totalBudget: 1000,
      reserveBudget: 200,
      warningThreshold: 0.8,
      criticalThreshold: 0.95,
    });
  });

  describe("Basic Operations", () => {
    it("should return total budget", () => {
      expect(budget.getTotalBudget()).toBe(1000);
    });

    it("should return available budget", () => {
      budget.recordConversationHistory(100);
      // Available = 1000 - 100 - 200 = 700
      expect(budget.getAvailableBudget()).toBe(700);
    });

    it("should track usage correctly", () => {
      budget.recordSystemPrompt(50);
      budget.recordConversationHistory(100);
      budget.recordToolResults(30);

      const usage = budget.getCurrentUsage();
      expect(usage.systemPrompt).toBe(50);
      expect(usage.conversationHistory).toBe(100);
      expect(usage.toolResults).toBe(30);
      expect(usage.total).toBe(180);
    });

    it("should calculate usage percentage", () => {
      budget.recordConversationHistory(800);
      expect(budget.getUsagePercentage()).toBe(0.8);
    });
  });

  describe("Threshold Detection", () => {
    it("should return null when under warning threshold", () => {
      budget.recordConversationHistory(700); // 70%
      expect(budget.checkThresholds()).toBeNull();
    });

    it("should return warning alert at 80%", () => {
      budget.recordConversationHistory(800); // 80%
      const alert = budget.checkThresholds();
      expect(alert).not.toBeNull();
      expect(alert?.level).toBe("warning");
      expect(alert?.recommendedAction).toBe("compress");
    });

    it("should return critical alert at 95%", () => {
      budget.recordConversationHistory(950); // 95%
      const alert = budget.checkThresholds();
      expect(alert).not.toBeNull();
      expect(alert?.level).toBe("critical");
      expect(alert?.recommendedAction).toBe("truncate");
    });
  });

  describe("Allocation", () => {
    it("should allocate when sufficient budget", () => {
      const result = budget.allocateForResponse(500);
      expect(result).toBe(true);
      expect(budget.getCurrentUsage().reserved).toBe(500);
    });

    it("should fail allocation when insufficient budget", () => {
      budget.recordConversationHistory(700); // 700 used
      // Available = 1000 - 700 - 200 = 100
      const result = budget.allocateForResponse(200);
      expect(result).toBe(false);
    });

    it("should release allocation", () => {
      budget.allocateForResponse(500);
      budget.releaseAllocation(300);
      expect(budget.getCurrentUsage().reserved).toBe(200);
    });

    it("should emergency release", () => {
      budget.allocateForResponse(500);
      const released = budget.emergencyRelease();
      expect(released).toBe(500);
      expect(budget.getCurrentUsage().reserved).toBe(0);
    });
  });

  describe("Reset", () => {
    it("should reset all usage", () => {
      budget.recordConversationHistory(500);
      budget.allocateForResponse(200);
      budget.reset();

      const usage = budget.getCurrentUsage();
      expect(usage.total).toBe(0);
      expect(usage.reserved).toBe(0);
      expect(usage.conversationHistory).toBe(0);
    });
  });
});

describe("DefaultTokenEstimator", () => {
  let estimator: DefaultTokenEstimator;

  beforeEach(() => {
    estimator = new DefaultTokenEstimator();
  });

  it("should estimate English text", () => {
    // "Hello world" = 11 chars, ~4 chars/token = ~3 tokens
    const tokens = estimator.estimateText("Hello world");
    expect(tokens).toBeGreaterThan(0);
  });

  it("should estimate Chinese text", () => {
    // "你好世界" = 4 chars, ~1.5 chars/token = ~3 tokens
    const tokens = estimator.estimateText("你好世界");
    expect(tokens).toBeGreaterThan(0);
  });

  it("should estimate mixed content", () => {
    const tokens = estimator.estimateText("Hello 你好 world 世界");
    expect(tokens).toBeGreaterThan(0);
  });
});
