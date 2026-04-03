/**
 * Enhanced Coordinator Mode
 * 融入 Claude Code 最佳实践的 Coordinator 实现
 */

import { 
  CoordinatorWorkflow, 
  WorkflowPhase,
  Worker,
  WorkerResult,
  WorkerType,
  buildWorkerDirective,
  decideContinueOrSpawn,
  TaskContext
} from '../../../文档/IELTS-Obsidian/Projects/claude-plugin/src/coordinator-mode/coordinator';
import { sessions_spawn, sessions_send } from '../../../../../.openclaw/skills';

// ==================== 类型定义 ====================

interface EnhancedCoordinatorConfig {
  // 上下文管理
  autoClearBetweenPhases: boolean;
  compactThreshold: number;  // token 阈值
  useBtwForQuickQuestions: boolean;
  
  // 阶段配置
  phaseConfigs: Record<EnhancedWorkflowPhase, PhaseConfig>;
  
  // 决策引擎
  enableSmartContinueVsSpawn: boolean;
  
  // 验证
  enableVerification: boolean;
  autoRetryOnFailure: boolean;
  maxRetries: number;
}

interface PhaseConfig {
  allowedTools: string[];
  permissionMode: PermissionMode;
  maxTurns: number;
  requireVerification: boolean;
  autoClearBefore: boolean;
}

type EnhancedWorkflowPhase = 
  | 'explore'      // 探索阶段（新增）
  | 'plan'
  | 'implement'
  | 'verify'
  | 'commit';     // 提交阶段（新增）

type PermissionMode = 
  | 'default' 
  | 'plan' 
  | 'bubble' 
  | 'auto' 
  | 'acceptEdits'
  | 'bypassPermissions' 
  | 'dontAsk';

interface TaskWithVerification {
  task: string;
  verificationCriteria?: string[];
  testCommand?: string;
  expectedOutput?: string;
}

interface ContinueVsSpawnDecision {
  action: 'continue' | 'spawn';
  reason: string;
  confidence: number;
}

interface ContextAnalysis {
  tokenCount: number;
  relevantFiles: string[];
  researchScope: 'broad' | 'narrow';
  implementationScope: 'broad' | 'narrow';
  isRetry: boolean;
  previousAttemptFailed: boolean;
  previousApproachWasWrong: boolean;
}

// ==================== 默认配置 ====================

const DEFAULT_ENHANCED_CONFIG: EnhancedCoordinatorConfig = {
  autoClearBetweenPhases: true,
  compactThreshold: 4000,  // 4000 tokens 触发清理
  useBtwForQuickQuestions: true,
  enableSmartContinueVsSpawn: true,
  enableVerification: true,
  autoRetryOnFailure: true,
  maxRetries: 2,
  
  phaseConfigs: {
    explore: {
      allowedTools: ['Read', 'Grep', 'Glob', 'Bash'],
      permissionMode: 'plan',
      maxTurns: 100,
      requireVerification: false,
      autoClearBefore: false
    },
    plan: {
      allowedTools: ['Read', 'Grep', 'Glob'],
      permissionMode: 'plan',
      maxTurns: 50,
      requireVerification: false,
      autoClearBefore: true
    },
    implement: {
      allowedTools: ['Read', 'Write', 'Edit', 'Bash'],
      permissionMode: 'default',
      maxTurns: 200,
      requireVerification: true,
      autoClearBefore: false
    },
    verify: {
      allowedTools: ['Read', 'Bash'],
      permissionMode: 'default',
      maxTurns: 100,
      requireVerification: true,
      autoClearBefore: true
    },
    commit: {
      allowedTools: ['Bash'],
      permissionMode: 'auto',
      maxTurns: 20,
      requireVerification: false,
      autoClearBefore: false
    }
  }
};

// ==================== 增强的 Coordinator ====================

export class EnhancedCoordinatorWorkflow {
  private phase: EnhancedWorkflowPhase = 'explore';
  private workers: Map<string, Worker> = new Map();
  private completedTasks: WorkerResult[] = [];
  private config: EnhancedCoordinatorConfig;
  private contextAnalysis: ContextAnalysis;
  private retryCount: number = 0;

  constructor(
    config: Partial<EnhancedCoordinatorConfig> = {},
    initialContext: Partial<ContextAnalysis> = {}
  ) {
    this.config = { ...DEFAULT_ENHANCED_CONFIG, ...config };
    this.contextAnalysis = {
      tokenCount: 0,
      relevantFiles: [],
      researchScope: 'broad',
      implementationScope: 'narrow',
      isRetry: false,
      previousAttemptFailed: false,
      previousApproachWasWrong: false,
      ...initialContext
    };
  }

  // ==================== 主工作流 ====================

  async run(task: TaskWithVerification): Promise<{
    success: boolean;
    results: WorkerResult[];
    summary: string;
  }> {
    try {
      console.log('🚀 启动增强 Coordinator Mode');
      
      // Phase 1: Explore
      await this.runExplorePhase(task);
      await this.maybeClearContext('explore');
      
      // Phase 2: Plan
      await this.runPlanPhase();
      await this.maybeClearContext('plan');
      
      // Phase 3: Implement
      const implementResult = await this.runImplementPhase(task);
      
      // Phase 4: Verify
      if (this.config.enableVerification) {
        const verifyResult = await this.runVerifyPhase(task, implementResult);
        
        // 自动重试逻辑
        if (!verifyResult.success && this.config.autoRetryOnFailure) {
          if (this.retryCount < this.config.maxRetries) {
            this.retryCount++;
            console.log(`🔄 验证失败，开始第 ${this.retryCount} 次重试...`);
            this.contextAnalysis.isRetry = true;
            this.contextAnalysis.previousAttemptFailed = true;
            return this.run(task);  // 递归重试
          }
        }
      }
      
      // Phase 5: Commit
      await this.runCommitPhase();
      
      this.phase = 'commit';
      
      return {
        success: true,
        results: this.completedTasks,
        summary: this.generateSummary()
      };
      
    } catch (error) {
      console.error('❌ Coordinator Mode 执行失败:', error);
      return {
        success: false,
        results: this.completedTasks,
        summary: `执行失败: ${error instanceof Error ? error.message : String(error)}`
      };
    }
  }

  // ==================== 各阶段实现 ====================

  private async runExplorePhase(task: TaskWithVerification): Promise<void> {
    console.log('🔍 Phase 1: Explore - 探索代码库');
    this.phase = 'explore';
    
    const phaseConfig = this.config.phaseConfigs.explore;
    
    // 分析研究方向
    const researchDirections = this.analyzeResearchDirections(task.task);
    
    // 并行派生 Explore Worker
    const explorePromises = researchDirections.map(dir => 
      this.spawnWorkerWithDecision('explore', dir, phaseConfig, null)
    );
    
    const workers = await Promise.all(explorePromises);
    const results = await this.waitForWorkers(workers.map(w => w.id));
    
    this.completedTasks.push(...results);
    
    // 更新上下文分析
    this.contextAnalysis.relevantFiles = this.extractRelevantFiles(results);
    this.contextAnalysis.researchScope = researchDirections.length > 2 ? 'broad' : 'narrow';
  }

  private async runPlanPhase(): Promise<void> {
    console.log('📝 Phase 2: Plan - 制定实施计划');
    this.phase = 'plan';
    
    const phaseConfig = this.config.phaseConfigs.plan;
    const synthesis = this.synthesizeFindings(this.completedTasks);
    
    // 派生 Plan Worker
    const planWorker = await this.spawnWorkerWithDecision(
      'plan',
      `基于以下发现制定实施计划：\n${synthesis}`,
      phaseConfig,
      this.getLastWorker()  // 可能 Continue
    );
    
    await this.waitForWorker(planWorker.id);
  }

  private async runImplementPhase(task: TaskWithVerification): Promise<WorkerResult> {
    console.log('⚙️ Phase 3: Implement - 实现功能');
    this.phase = 'implement';
    
    const phaseConfig = this.config.phaseConfigs.implement;
    const plan = this.getLastCompletedTask()?.output || '';
    
    // 按文件分组任务
    const fileGroups = this.groupTasksByFile(plan);
    this.contextAnalysis.implementationScope = fileGroups.length > 3 ? 'broad' : 'narrow';
    
    const results: WorkerResult[] = [];
    
    for (const group of fileGroups) {
      // 智能决策：Continue vs Spawn
      const decision = this.decideContinueOrSpawn('implement', group.files);
      
      const worker = await this.spawnWorkerWithDecision(
        'implement',
        group.directive,
        phaseConfig,
        decision.action === 'continue' ? this.getLastWorker() : null
      );
      
      const result = await this.waitForWorker(worker.id);
      results.push(result);
    }
    
    return results[results.length - 1];
  }

  private async runVerifyPhase(
    task: TaskWithVerification,
    implementResult: WorkerResult
  ): Promise<WorkerResult> {
    console.log('✅ Phase 4: Verify - 验证实现');
    this.phase = 'verify';
    
    const phaseConfig = this.config.phaseConfigs.verify;
    
    let verifyDirective = `验证以下实现：\n${implementResult.output}`;
    
    if (task.verificationCriteria) {
      verifyDirective += `\n\n验证标准：\n${task.verificationCriteria.map(c => `- ${c}`).join('\n')}`;
    }
    
    if (task.testCommand) {
      verifyDirective += `\n\n运行：${task.testCommand}`;
    }
    
    const verifyWorker = await this.spawnWorkerWithDecision(
      'verify',
      verifyDirective,
      phaseConfig,
      null
    );
    
    return await this.waitForWorker(verifyWorker.id);
  }

  private async runCommitPhase(): Promise<void> {
    console.log('💾 Phase 5: Commit - 提交代码');
    this.phase = 'commit';
    
    const changedFiles = this.collectChangedFiles();
    if (changedFiles.length === 0) return;
    
    const commitWorker = await this.spawnWorkerWithDecision(
      'commit',
      `提交修改：\n${changedFiles.join('\n')}`,
      this.config.phaseConfigs.commit,
      null
    );
    
    await this.waitForWorker(commitWorker.id);
  }

  // ==================== 智能决策引擎 ====================

  private decideContinueOrSpawn(
    phase: EnhancedWorkflowPhase,
    targetFiles: string[]
  ): { action: 'continue' | 'spawn'; reason: string } {
    if (!this.config.enableSmartContinueVsSpawn) {
      return { action: 'spawn', reason: '智能决策已禁用' };
    }
    
    const ctx = this.contextAnalysis;
    
    // Scene 1: Worker has files
    if (targetFiles.every(f => ctx.relevantFiles.includes(f))) {
      return { action: 'continue', reason: 'Worker 已有相关文件' };
    }
    
    // Scene 2: Research broad, implement narrow
    if (phase === 'implement' && ctx.researchScope === 'broad' && ctx.implementationScope === 'narrow') {
      return { action: 'spawn', reason: '避免上下文噪音' };
    }
    
    // Scene 3: Retry failed
    if (ctx.isRetry && ctx.previousAttemptFailed) {
      return { action: 'continue', reason: '保留错误上下文' };
    }
    
    // Scene 4: Verify
    if (phase === 'verify') {
      return { action: 'spawn', reason: '验证者需要 fresh eyes' };
    }
    
    return { action: 'spawn', reason: '默认派生新 Worker' };
  }

  // ==================== 辅助方法 ====================

  private async maybeClearContext(phase: EnhancedWorkflowPhase): Promise<void> {
    if (!this.config.autoClearBetweenPhases) return;
    if (!this.config.phaseConfigs[phase].autoClearBefore) return;
    
    console.log(`🧹 清理 ${phase} 阶段上下文`);
  }

  private analyzeResearchDirections(task: string): string[] {
    const directions: string[] = [];
    if (task.includes('代码') || task.includes('实现')) {
      directions.push('调查代码文件和模块');
      directions.push('分析实现模式');
    }
    if (task.includes('认证') || task.includes('auth')) {
      directions.push('分析认证机制');
    }
    return directions.length > 0 ? directions : ['调查项目结构'];
  }

  private synthesizeFindings(results: WorkerResult[]): string {
    return results.filter(r => r.success).map(r => r.output).join('\n\n');
  }

  private groupTasksByFile(plan: string): Array<{ files: string[]; directive: string }> {
    // 简化实现
    return [{ files: ['src/main.ts'], directive: plan }];
  }

  private extractRelevantFiles(results: WorkerResult[]): string[] {
    const files: string[] = [];
    for (const r of results) {
      // 从输出中提取文件路径
      const matches = r.output.match(/[\w\/]+\.(ts|js|py|java)/g);
      if (matches) files.push(...matches);
    }
    return [...new Set(files)];
  }

  private collectChangedFiles(): string[] {
    const files: string[] = [];
    for (const task of this.completedTasks) {
      // 从结果中提取修改的文件
    }
    return [...new Set(files)];
  }

  private getLastWorker(): Worker | null {
    const workers = Array.from(this.workers.values());
    return workers[workers.length - 1] || null;
  }

  private getLastCompletedTask(): WorkerResult | null {
    return this.completedTasks[this.completedTasks.length - 1] || null;
  }

  private generateSummary(): string {
    return `完成 ${this.completedTasks.length} 个任务，成功: ${this.completedTasks.filter(t => t.success).length}`;
  }
}

// ==================== 导出 ====================

export {
  EnhancedCoordinatorWorkflow,
  EnhancedCoordinatorConfig,
  TaskWithVerification,
  EnhancedWorkflowPhase
};
