/**
 * MultiAgentContext - Fork/Coordinator 上下文隔离模块 (P2)
 */

import {
  MultiAgentContextConfig,
  AgentContext,
  AgentResult,
  ForkContext,
  MergeOptions,
  MergeResult,
  CoordinatorState,
  WorkerContext,
  TaskResult,
  WorkflowPhase,
  ImplementationPlan,
  ImplementationTask,
  DEFAULT_MULTI_AGENT_CONFIG,
} from "../types/index.js";
import { DefaultTokenEstimator } from "./TokenBudget.js";
import { MessageHistory } from "./MessageHistory.js";

export class ForkManager {
  private forks: Map<string, ForkContext> = new Map();
  private forkContexts: Map<string, AgentContext> = new Map();
  private config: MultiAgentContextConfig;

  constructor(config: MultiAgentContextConfig) {
    this.config = config;
  }

  createFork(parentContext: AgentContext, agentId: string, task: string, messageHistory: MessageHistory): AgentContext {
    const forkId = `${parentContext.agentId}-fork-${agentId}`;
    const isolatedScope = this.getIsolatedScope(agentId);

    const forkInfo: ForkContext = {
      parentContextId: parentContext.agentId,
      forkedAt: Date.now(),
      snapshotDepth: this.config.forkSnapshotDepth,
      isolatedScope,
    };

    this.forks.set(forkId, forkInfo);

    const forkContext: AgentContext = {
      agentId: forkId,
      sessionId: parentContext.sessionId,
      tokenBudget: {
        totalBudget: parentContext.tokenBudget.totalBudget,
        usedBudget: 0,
        allocation: {},
      },
      messageHistory: {
        messageCount: 0,
        tokenCount: 0,
        layerStats: {},
      },
      scope: isolatedScope,
      parentContextId: parentContext.agentId,
    };

    this.forkContexts.set(forkId, forkContext);
    return forkContext;
  }

  getForkInfo(contextId: string): ForkContext | null {
    return this.forks.get(contextId) || null;
  }

  getIsolatedScope(agentId: string): string {
    if (this.config.isolationMode === "strict") {
      return `agent:${agentId}:isolated`;
    } else if (this.config.isolationMode === "shared") {
      return `agent:${agentId}:shared`;
    } else {
      return `agent:${agentId}:hybrid`;
    }
  }

  isContextIsolated(contextId: string): boolean {
    const forkInfo = this.forks.get(contextId);
    if (!forkInfo) return false;
    return this.config.isolationMode === "strict" || forkInfo.isolatedScope.includes(":isolated");
  }

  cleanupFork(forkId: string): void {
    this.forks.delete(forkId);
    this.forkContexts.delete(forkId);
  }

  getAllForks(): ForkContext[] {
    return Array.from(this.forks.values());
  }
}

export class CoordinatorManager {
  private coordinators: Map<string, CoordinatorState> = new Map();
  private workers: Map<string, WorkerContext> = new Map();
  private config: MultiAgentContextConfig;

  constructor(config: MultiAgentContextConfig) {
    this.config = config;
  }

  initializeCoordinator(coordinatorId: string, task: string, parentContext: AgentContext): CoordinatorState {
    const state: CoordinatorState = {
      phase: "research",
      workers: new Map(),
      completedTasks: [],
      currentPlan: null,
    };

    this.coordinators.set(coordinatorId, state);
    state.currentPlan = this.createInitialPlan(task);
    return state;
  }

  private createInitialPlan(task: string): ImplementationPlan {
    const phases = this.config.coordinatorPhases;
    const tasks: ImplementationTask[] = phases.map((phase, index) => ({
      id: `task-${phase}-${index}`,
      description: `${phase} phase for: ${task}`,
      targetFiles: [],
      estimatedTokens: 20000,
      priority: 10 - index,
    }));

    const fileGroups: Record<string, ImplementationTask[]> = {};
    phases.forEach((phase, index) => {
      fileGroups[phase] = [tasks[index]];
    });

    const dependencies = new Map<string, string[]>();
    if (phases.includes("synthesis") && phases.includes("implementation")) {
      dependencies.set("task-implementation-2", ["task-synthesis-1"]);
    }
    if (phases.includes("implementation") && phases.includes("verification")) {
      dependencies.set("task-verification-3", ["task-implementation-2"]);
    }

    return { tasks, fileGroups, dependencies };
  }

  spawnWorker(coordinatorId: string, role: WorkflowPhase, task: string, parentContext: AgentContext): WorkerContext {
    const workerId = `${coordinatorId}-worker-${role}-${Date.now()}`;

    const workerContext: AgentContext = {
      agentId: workerId,
      sessionId: parentContext.sessionId,
      tokenBudget: {
        totalBudget: Math.floor(parentContext.tokenBudget.totalBudget * 0.5),
        usedBudget: 0,
        allocation: {},
      },
      messageHistory: {
        messageCount: 0,
        tokenCount: 0,
        layerStats: {},
      },
      scope: this.getWorkerScope(coordinatorId, workerId),
      workflowPhase: role,
      parentContextId: coordinatorId,
    };

    const worker: WorkerContext = {
      workerId,
      role,
      context: workerContext,
      status: "running",
    };

    this.workers.set(workerId, worker);
    const coordinatorState = this.coordinators.get(coordinatorId);
    if (coordinatorState) {
      coordinatorState.workers.set(workerId, worker);
    }

    return worker;
  }

  updateWorkerStatus(coordinatorId: string, workerId: string, status: WorkerContext["status"], result?: TaskResult): void {
    const worker = this.workers.get(workerId);
    if (!worker) return;

    worker.status = status;
    if (result) {
      worker.result = result;
    }

    const coordinatorState = this.coordinators.get(coordinatorId);
    if (coordinatorState) {
      coordinatorState.workers.set(workerId, worker);
      if (status === "completed" && result) {
        coordinatorState.completedTasks.push(result);
      }
    }
  }

  getCoordinatorState(coordinatorId: string): CoordinatorState | null {
    return this.coordinators.get(coordinatorId) || null;
  }

  getWorkerScope(coordinatorId: string, workerId: string): string {
    if (this.config.isolationMode === "strict") {
      return `worker:${coordinatorId}:${workerId}:isolated`;
    } else if (this.config.isolationMode === "shared") {
      return `coordinator:${coordinatorId}:shared`;
    } else {
      return `worker:${coordinatorId}:${workerId}:hybrid`;
    }
  }

  advancePhase(coordinatorId: string): WorkflowPhase | null {
    const state = this.coordinators.get(coordinatorId);
    if (!state) return null;

    const phases = this.config.coordinatorPhases;
    const currentIndex = phases.indexOf(state.phase);

    if (currentIndex < phases.length - 1) {
      state.phase = phases[currentIndex + 1];
      return state.phase;
    }

    return null;
  }

  cleanupCompletedWorkers(coordinatorId: string): void {
    const state = this.coordinators.get(coordinatorId);
    if (!state) return;

    for (const [workerId, worker] of state.workers) {
      if (worker.status === "completed" || worker.status === "failed" || worker.status === "killed") {
        this.workers.delete(workerId);
        state.workers.delete(workerId);
      }
    }
  }

  destroyCoordinator(coordinatorId: string): void {
    const state = this.coordinators.get(coordinatorId);
    if (!state) return;

    for (const workerId of state.workers.keys()) {
      this.workers.delete(workerId);
    }
    this.coordinators.delete(coordinatorId);
  }

  getActiveCoordinators(): string[] {
    return Array.from(this.coordinators.keys());
  }
}

export class MergeManager {
  private config: MultiAgentContextConfig;
  private estimator: DefaultTokenEstimator;

  constructor(config: MultiAgentContextConfig) {
    this.config = config;
    this.estimator = new DefaultTokenEstimator();
  }

  mergeForkResult(parentContext: AgentContext, forkContext: AgentContext, result: AgentResult, options: MergeOptions): MergeResult {
    let tokensAdded = 0;
    let summaryInjected = false;

    if (this.config.mergeStrategy === "full") {
      tokensAdded = this.estimator.estimateText(result.output);
    } else if (this.config.mergeStrategy === "summary") {
      const summary = this.generateSummary(result);
      tokensAdded = this.estimator.estimateText(summary);
      summaryInjected = true;
    } else {
      const delta = this.extractDelta(result);
      tokensAdded = this.estimator.estimateText(delta);
    }

    if (tokensAdded > options.maxTokens) {
      tokensAdded = options.maxTokens;
    }

    const updatedParentContext: AgentContext = {
      ...parentContext,
      tokenBudget: {
        ...parentContext.tokenBudget,
        usedBudget: parentContext.tokenBudget.usedBudget + tokensAdded,
      },
    };

    return {
      mergedContext: updatedParentContext,
      tokensAdded,
      summaryInjected,
      taskNotificationStored: false,
    };
  }

  private generateSummary(result: AgentResult): string {
    const statusEmoji = result.status === "completed" ? "✅" : result.status === "failed" ? "❌" : "⏹️";
    return `${statusEmoji} Task completed with status: ${result.status}\n` +
      `Output: ${result.output.slice(0, 200)}${result.output.length > 200 ? "..." : ""}\n` +
      `Tokens: ${result.usage.totalTokens}, Tools: ${result.usage.toolUses}, Duration: ${result.usage.durationMs}ms`;
  }

  private extractDelta(result: AgentResult): string {
    if (result.worktree) {
      return `Worktree created at ${result.worktree.path}` +
        (result.worktree.branch ? ` on branch ${result.worktree.branch}` : "");
    }
    return result.output.slice(0, 100);
  }

  mergeWorkerResults(workerResults: TaskResult[], options: MergeOptions): string {
    if (this.config.mergeStrategy === "full") {
      return workerResults.map(r => `[${r.workerId}] ${r.output}`).join("\n\n");
    }

    const successful = workerResults.filter(r => r.status === "completed");
    const failed = workerResults.filter(r => r.status === "failed");

    let summary = "";

    if (successful.length > 0) {
      summary += `✅ ${successful.length} tasks completed:\n`;
      summary += successful.map(r => `  - ${r.workerId}: ${r.output.slice(0, 50)}...`).join("\n");
    }

    if (failed.length > 0) {
      summary += `\n❌ ${failed.length} tasks failed:\n`;
      summary += failed.map(r => `  - ${r.workerId}: ${r.status}`).join("\n");
    }

    return summary;
  }
}

export class MultiAgentContext {
  private config: MultiAgentContextConfig;
  private forkManager: ForkManager;
  private coordinatorManager: CoordinatorManager;
  private mergeManager: MergeManager;
  private messageHistory: MessageHistory;

  constructor(config: Partial<MultiAgentContextConfig> = {}, messageHistory?: MessageHistory) {
    this.config = { ...DEFAULT_MULTI_AGENT_CONFIG, ...config };
    this.forkManager = new ForkManager(this.config);
    this.coordinatorManager = new CoordinatorManager(this.config);
    this.mergeManager = new MergeManager(this.config);
    this.messageHistory = messageHistory || new MessageHistory();
  }

  createFork(parentContext: AgentContext, agentId: string, task: string): AgentContext {
    return this.forkManager.createFork(parentContext, agentId, task, this.messageHistory);
  }

  getForkInfo(contextId: string): ForkContext | null {
    return this.forkManager.getForkInfo(contextId);
  }

  getIsolatedScope(agentId: string): string {
    return this.forkManager.getIsolatedScope(agentId);
  }

  isContextIsolated(contextId: string): boolean {
    return this.forkManager.isContextIsolated(contextId);
  }

  initializeCoordinator(coordinatorId: string, task: string, parentContext: AgentContext): CoordinatorState {
    return this.coordinatorManager.initializeCoordinator(coordinatorId, task, parentContext);
  }

  spawnWorker(coordinatorId: string, role: WorkflowPhase, task: string, parentContext: AgentContext): WorkerContext {
    return this.coordinatorManager.spawnWorker(coordinatorId, role, task, parentContext);
  }

  updateWorkerStatus(coordinatorId: string, workerId: string, status: WorkerContext["status"], result?: TaskResult): void {
    this.coordinatorManager.updateWorkerStatus(coordinatorId, workerId, status, result);
  }

  getCoordinatorState(coordinatorId: string): CoordinatorState | null {
    return this.coordinatorManager.getCoordinatorState(coordinatorId);
  }

  advancePhase(coordinatorId: string): WorkflowPhase | null {
    return this.coordinatorManager.advancePhase(coordinatorId);
  }

  cleanupCompletedWorkers(coordinatorId: string): void {
    this.coordinatorManager.cleanupCompletedWorkers(coordinatorId);
  }

  destroyCoordinator(coordinatorId: string): void {
    this.coordinatorManager.destroyCoordinator(coordinatorId);
  }

  mergeForkResult(parentContext: AgentContext, forkContext: AgentContext, result: AgentResult, options?: Partial<MergeOptions>): MergeResult {
    const defaultOptions: MergeOptions = {
      strategy: this.config.mergeStrategy,
      includeToolResults: true,
      includeThinking: false,
      maxTokens: 5000,
    };
    return this.mergeManager.mergeForkResult(parentContext, forkContext, result, { ...defaultOptions, ...options });
  }

  mergeWorkerResults(workerResults: TaskResult[], options?: Partial<MergeOptions>): string {
    const defaultOptions: MergeOptions = {
      strategy: this.config.mergeStrategy,
      includeToolResults: true,
      includeThinking: false,
      maxTokens: 5000,
    };
    return this.mergeManager.mergeWorkerResults(workerResults, { ...defaultOptions, ...options });
  }

  getConfig(): MultiAgentContextConfig {
    return { ...this.config };
  }

  getAllForks(): ForkContext[] {
    return this.forkManager.getAllForks();
  }

  getActiveCoordinators(): string[] {
    return this.coordinatorManager.getActiveCoordinators();
  }

  setMessageHistory(history: MessageHistory): void {
    this.messageHistory = history;
  }

  createDefaultContext(sessionId: string, agentId: string): AgentContext {
    return {
      agentId,
      sessionId,
      tokenBudget: {
        totalBudget: 200000,
        usedBudget: 0,
        allocation: {},
      },
      messageHistory: {
        messageCount: 0,
        tokenCount: 0,
        layerStats: {},
      },
      scope: `agent:${agentId}`,
    };
  }
}

export default MultiAgentContext;