/**
 * MultiAgentContext 模块测试 (P2)
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  MultiAgentContext,
  ForkManager,
  CoordinatorManager,
  MergeManager,
} from "../src/core/MultiAgentContext";
import type { AgentContext, AgentResult, TaskResult } from "../src/types";

describe("MultiAgentContext", () => {
  let multiAgentContext: MultiAgentContext;

  const createParentContext = (): AgentContext => ({
    agentId: "parent-agent",
    sessionId: "session-123",
    tokenBudget: {
      totalBudget: 200000,
      usedBudget: 0,
      allocation: {},
    },
    messageHistory: {
      messageCount: 10,
      tokenCount: 5000,
      layerStats: {},
    },
    scope: "agent:parent",
  });

  beforeEach(() => {
    multiAgentContext = new MultiAgentContext();
  });

  describe("Fork 管理", () => {
    it("应该创建 Fork 上下文", () => {
      const parentContext = createParentContext();
      const forkContext = multiAgentContext.createFork(parentContext, "child-1", "test task");

      expect(forkContext.agentId).toContain("child-1");
      expect(forkContext.parentContextId).toBe("parent-agent");
      expect(forkContext.scope).toContain("isolated");
    });

    it("应该获取 Fork 信息", () => {
      const parentContext = createParentContext();
      const forkContext = multiAgentContext.createFork(parentContext, "child-1", "test task");

      const forkInfo = multiAgentContext.getForkInfo(forkContext.agentId);
      expect(forkInfo).not.toBeNull();
      expect(forkInfo?.parentContextId).toBe("parent-agent");
    });

    it("应该正确识别隔离上下文", () => {
      const parentContext = createParentContext();
      const forkContext = multiAgentContext.createFork(parentContext, "child-1", "test task");

      expect(multiAgentContext.isContextIsolated(forkContext.agentId)).toBe(true);
      expect(multiAgentContext.isContextIsolated("non-existent")).toBe(false);
    });

    it("应该获取隔离 Scope", () => {
      const scope = multiAgentContext.getIsolatedScope("agent-1");
      expect(scope).toContain("agent-1");
    });
  });

  describe("Coordinator 管理", () => {
    it("应该初始化 Coordinator", () => {
      const parentContext = createParentContext();
      const state = multiAgentContext.initializeCoordinator("coord-1", "test task", parentContext);

      expect(state.phase).toBe("research");
      expect(state.workers.size).toBe(0);
      expect(state.currentPlan).not.toBeNull();
    });

    it("应该 Spawn Worker", () => {
      const parentContext = createParentContext();
      multiAgentContext.initializeCoordinator("coord-1", "test task", parentContext);

      const worker = multiAgentContext.spawnWorker("coord-1", "research", "research task", parentContext);

      expect(worker.workerId).toContain("research");
      expect(worker.role).toBe("research");
      expect(worker.status).toBe("running");
    });

    it("应该更新 Worker 状态", () => {
      const parentContext = createParentContext();
      multiAgentContext.initializeCoordinator("coord-1", "test task", parentContext);
      const worker = multiAgentContext.spawnWorker("coord-1", "research", "research task", parentContext);

      const taskResult: TaskResult = {
        workerId: worker.workerId,
        status: "completed",
        output: "Research completed",
      };

      multiAgentContext.updateWorkerStatus("coord-1", worker.workerId, "completed", taskResult);

      const state = multiAgentContext.getCoordinatorState("coord-1");
      expect(state?.completedTasks).toHaveLength(1);
    });

    it("应该推进阶段", () => {
      const parentContext = createParentContext();
      multiAgentContext.initializeCoordinator("coord-1", "test task", parentContext);

      const nextPhase = multiAgentContext.advancePhase("coord-1");
      expect(nextPhase).toBe("synthesis");

      const state = multiAgentContext.getCoordinatorState("coord-1");
      expect(state?.phase).toBe("synthesis");
    });

    it("应该清理已完成的 Workers", () => {
      const parentContext = createParentContext();
      multiAgentContext.initializeCoordinator("coord-1", "test task", parentContext);
      const worker = multiAgentContext.spawnWorker("coord-1", "research", "research task", parentContext);

      multiAgentContext.updateWorkerStatus("coord-1", worker.workerId, "completed");
      multiAgentContext.cleanupCompletedWorkers("coord-1");

      const state = multiAgentContext.getCoordinatorState("coord-1");
      expect(state?.workers.size).toBe(0);
    });

    it("应该销毁 Coordinator", () => {
      const parentContext = createParentContext();
      multiAgentContext.initializeCoordinator("coord-1", "test task", parentContext);
      multiAgentContext.spawnWorker("coord-1", "research", "research task", parentContext);

      multiAgentContext.destroyCoordinator("coord-1");

      expect(multiAgentContext.getCoordinatorState("coord-1")).toBeNull();
      expect(multiAgentContext.getActiveCoordinators()).toHaveLength(0);
    });
  });

  describe("Merge 操作", () => {
    it("应该合并 Fork 结果", () => {
      const parentContext = createParentContext();
      const forkContext = multiAgentContext.createFork(parentContext, "child-1", "test task");

      const result: AgentResult = {
        status: "completed",
        output: "Task completed successfully",
        usage: {
          totalTokens: 1000,
          toolUses: 5,
          durationMs: 5000,
        },
      };

      const mergeResult = multiAgentContext.mergeForkResult(parentContext, forkContext, result);

      expect(mergeResult.tokensAdded).toBeGreaterThan(0);
      expect(mergeResult.mergedContext.tokenBudget.usedBudget).toBeGreaterThan(0);
    });

    it("应该合并多个 Worker 结果", () => {
      const workerResults: TaskResult[] = [
        { workerId: "worker-1", status: "completed", output: "Task 1 done" },
        { workerId: "worker-2", status: "completed", output: "Task 2 done" },
      ];

      const merged = multiAgentContext.mergeWorkerResults(workerResults);

      expect(merged).toContain("worker-1");
      expect(merged).toContain("worker-2");
    });
  });

  describe("辅助方法", () => {
    it("应该获取配置", () => {
      const config = multiAgentContext.getConfig();
      expect(config.isolationMode).toBe("strict");
      expect(config.mergeStrategy).toBe("summary");
    });

    it("应该创建默认上下文", () => {
      const context = multiAgentContext.createDefaultContext("session-1", "agent-1");

      expect(context.agentId).toBe("agent-1");
      expect(context.sessionId).toBe("session-1");
      expect(context.tokenBudget.totalBudget).toBe(200000);
    });
  });
});
