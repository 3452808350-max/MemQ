/**
 * Continue vs Spawn 决策引擎
 * 基于 Claude Code 最佳实践的智能决策系统
 */

// ==================== 类型定义 ====================

export interface DecisionContext {
  // 当前阶段
  currentPhase: WorkflowPhase;
  targetPhase: WorkflowPhase;
  
  // 上下文分析
  tokenCount: number;
  relevantFiles: string[];
  targetFiles: string[];
  
  // 范围分析
  researchScope: ScopeLevel;
  implementationScope: ScopeLevel;
  
  // 历史分析
  isRetry: boolean;
  previousAttemptFailed: boolean;
  previousApproachWasWrong: boolean;
  failureReason?: string;
  
  // Worker 状态
  existingWorker?: WorkerInfo;
  workerFilesInContext: string[];
  workerJustWroteCode: boolean;
  workerHasErrors: boolean;
  
  // 任务类型
  isVerification: boolean;
  isExploration: boolean;
  isImplementation: boolean;
}

export interface WorkerInfo {
  id: string;
  type: WorkerType;
  startTime: Date;
  filesAccessed: string[];
  filesModified: string[];
  errorsEncountered: string[];
  lastOutput: string;
}

export interface DecisionResult {
  action: 'continue' | 'spawn';
  reason: string;
  confidence: number;  // 0-1
  scenario: DecisionScenario;
  recommendations?: string[];
}

export interface DecisionRule {
  name: string;
  description: string;
  priority: number;  // 越高越先匹配
  condition: (ctx: DecisionContext) => boolean;
  decision: (ctx: DecisionContext) => DecisionResult;
}

export type WorkflowPhase = 
  | 'explore' 
  | 'plan' 
  | 'implement' 
  | 'verify' 
  | 'commit';

export type WorkerType = 
  | 'research' 
  | 'implementation' 
  | 'verification' 
  | 'custom';

export type ScopeLevel = 'broad' | 'narrow';

export type DecisionScenario =
  | 'worker_has_files'
  | 'research_broad_implement_narrow'
  | 'correcting_failed_attempt'
  | 'verifying_fresh_eyes'
  | 'wrong_approach_new_context'
  | 'token_threshold'
  | 'context_pollution'
  | 'default';

// ==================== 决策规则引擎 ====================

export class ContinueVsSpawnEngine {
  private rules: DecisionRule[];
  private config: EngineConfig;

  constructor(config: Partial<EngineConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.rules = this.initializeRules();
  }

  /**
   * 做出决策
   */
  decide(context: DecisionContext): DecisionResult {
    // 按优先级排序规则
    const sortedRules = [...this.rules].sort((a, b) => b.priority - a.priority);
    
    for (const rule of sortedRules) {
      if (rule.condition(context)) {
        const result = rule.decision(context);
        
        // 添加调试信息
        if (this.config.debug) {
          console.log(`[DecisionEngine] Matched rule: ${rule.name}`);
          console.log(`[DecisionEngine] Confidence: ${result.confidence}`);
        }
        
        return result;
      }
    }
    
    // 默认决策
    return this.createDefaultDecision(context);
  }

  /**
   * 批量决策（用于并行任务）
   */
  decideBatch(
    contexts: DecisionContext[]
  ): DecisionResult[] {
    return contexts.map(ctx => this.decide(ctx));
  }

  /**
   * 解释决策原因
   */
  explainDecision(result: DecisionResult): string {
    const explanations: Record<DecisionScenario, string> = {
      worker_has_files: 
        'Worker 已经拥有相关文件的上下文，复用更高效',
      research_broad_implement_narrow: 
        '探索范围广但实现范围窄，新 Worker 避免上下文噪音',
      correcting_failed_attempt: 
        '修复失败尝试，保留错误上下文有助于定位问题',
      verifying_fresh_eyes: 
        '验证需要 fresh eyes，避免实现者的偏见',
      wrong_approach_new_context: 
        '之前方法错误，需要全新上下文避免污染',
      token_threshold: 
        'Token 数量接近阈值，派生新 Worker 保持效率',
      context_pollution: 
        '检测到上下文污染，建议派生新 Worker',
      default: 
        '没有明显的上下文复用价值，默认派生新 Worker'
    };

    let explanation = `决策: ${result.action === 'continue' ? 'Continue' : 'Spawn'}\n`;
    explanation += `场景: ${result.scenario}\n`;
    explanation += `原因: ${explanations[result.scenario]}\n`;
    explanation += `置信度: ${(result.confidence * 100).toFixed(1)}%\n`;
    
    if (result.recommendations) {
      explanation += `\n建议:\n`;
      result.recommendations.forEach(r => {
        explanation += `  - ${r}\n`;
      });
    }

    return explanation;
  }

  // ==================== 决策规则定义 ====================

  private initializeRules(): DecisionRule[] {
    return [
      // Scene 1: Worker already has files in context
      {
        name: 'worker_has_files',
        description: 'Worker 已有相关文件',
        priority: 100,
        condition: (ctx) => {
          if (!ctx.existingWorker) return false;
          if (ctx.targetFiles.length === 0) return false;
          
          // 检查 Worker 是否已访问所有目标文件
          return ctx.targetFiles.every(file => 
            ctx.workerFilesInContext.includes(file)
          );
        },
        decision: (ctx) => ({
          action: 'continue',
          reason: `Worker ${ctx.existingWorker?.id} 已有 ${ctx.targetFiles.length} 个目标文件的上下文`,
          confidence: 0.9,
          scenario: 'worker_has_files',
          recommendations: [
            '复用现有 Worker 的上下文',
            '避免重复读取相同文件'
          ]
        })
      },

      // Scene 2: Research broad but implementation narrow
      {
        name: 'research_broad_implement_narrow',
        description: '探索广实现窄',
        priority: 95,
        condition: (ctx) => {
          return ctx.currentPhase === 'explore' && 
                 ctx.targetPhase === 'implement' &&
                 ctx.researchScope === 'broad' && 
                 ctx.implementationScope === 'narrow';
        },
        decision: (ctx) => ({
          action: 'spawn',
          reason: '探索范围广（broad）但实现范围窄（narrow），避免上下文噪音',
          confidence: 0.85,
          scenario: 'research_broad_implement_narrow',
          recommendations: [
            '派生专注的 Implementation Worker',
            '只传递必要的文件信息',
            '避免探索阶段的无关上下文'
          ]
        })
      },

      // Scene 3: Correcting failed attempt
      {
        name: 'correcting_failed_attempt',
        description: '修复失败尝试',
        priority: 90,
        condition: (ctx) => {
          return ctx.isRetry && 
                 ctx.previousAttemptFailed && 
                 !ctx.previousApproachWasWrong &&
                 ctx.targetPhase !== 'verify';
        },
        decision: (ctx) => ({
          action: 'continue',
          reason: '修复失败尝试，保留错误上下文有助于定位问题',
          confidence: 0.8,
          scenario: 'correcting_failed_attempt',
          recommendations: [
            '复用 Worker 的错误上下文',
            '基于失败原因调整实现',
            `失败原因: ${ctx.failureReason || '未知'}`
          ]
        })
      },

      // Scene 4: Verifying code just written
      {
        name: 'verifying_fresh_eyes',
        description: '验证需要 fresh eyes',
        priority: 95,
        condition: (ctx) => {
          return ctx.targetPhase === 'verify' || ctx.isVerification;
        },
        decision: (ctx) => ({
          action: 'spawn',
          reason: '验证者需要 fresh eyes，避免实现者的偏见',
          confidence: 0.9,
          scenario: 'verifying_fresh_eyes',
          recommendations: [
            '派生独立的 Verification Worker',
            '只传递验证标准和测试命令',
            '避免实现细节影响验证判断'
          ]
        })
      },

      // Scene 5: First attempt was wrong approach
      {
        name: 'wrong_approach_new_context',
        description: '方法错误需要新上下文',
        priority: 92,
        condition: (ctx) => {
          return ctx.isRetry && ctx.previousApproachWasWrong;
        },
        decision: (ctx) => ({
          action: 'spawn',
          reason: '之前的方法完全错误，错误上下文会污染重试',
          confidence: 0.85,
          scenario: 'wrong_approach_new_context',
          recommendations: [
            '派生全新 Worker',
            '只保留文件列表，不保留实现细节',
            '重新分析问题，采用不同方法'
          ]
        })
      },

      // Scene 6: Token threshold
      {
        name: 'token_threshold',
        description: 'Token 数量接近阈值',
        priority: 85,
        condition: (ctx) => {
          return ctx.tokenCount > (this.config.tokenThreshold || 4000);
        },
        decision: (ctx) => ({
          action: 'spawn',
          reason: `Token 数量 (${ctx.tokenCount}) 接近阈值，派生新 Worker 保持效率`,
          confidence: 0.75,
          scenario: 'token_threshold',
          recommendations: [
            '派生新 Worker 清理上下文',
            '只传递必要的文件和指令',
            '考虑使用 /compact 压缩上下文'
          ]
        })
      },

      // Scene 7: Context pollution
      {
        name: 'context_pollution',
        description: '上下文污染',
        priority: 80,
        condition: (ctx) => {
          // 检测上下文污染信号
          const hasManyFiles = ctx.workerFilesInContext.length > 10;
          const hasErrors = ctx.workerHasErrors;
          const hasUnrelatedWork = ctx.existingWorker?.filesModified.some(
            f => !ctx.targetFiles.includes(f)
          );
          
          return hasManyFiles || (hasErrors && hasUnrelatedWork);
        },
        decision: (ctx) => ({
          action: 'spawn',
          reason: '检测到上下文污染（文件过多或包含无关修改）',
          confidence: 0.7,
          scenario: 'context_pollution',
          recommendations: [
            '派生干净的 Worker',
            '清理无关文件引用',
            '重新开始当前任务'
          ]
        })
      }
    ];
  }

  // ==================== 辅助方法 ====================

  private createDefaultDecision(context: DecisionContext): DecisionResult {
    // 默认情况下，如果有 Worker 且没有明显问题，Continue
    if (context.existingWorker && !context.workerHasErrors) {
      return {
        action: 'continue',
        reason: '默认复用现有 Worker',
        confidence: 0.6,
        scenario: 'default',
        recommendations: ['监控 Worker 性能']
      };
    }

    // 否则 Spawn
    return {
      action: 'spawn',
      reason: '没有可复用的 Worker 或 Worker 有错误',
      confidence: 0.6,
      scenario: 'default',
      recommendations: ['派生新 Worker']
    };
  }

  /**
   * 分析上下文质量
   */
  analyzeContextQuality(ctx: DecisionContext): ContextQualityReport {
    const report: ContextQualityReport = {
      score: 1.0,
      issues: [],
      suggestions: []
    };

    // Token 数量评分
    if (ctx.tokenCount > 6000) {
      report.score -= 0.3;
      report.issues.push('Token 数量过高');
      report.suggestions.push('考虑清理上下文');
    } else if (ctx.tokenCount > 4000) {
      report.score -= 0.1;
      report.issues.push('Token 数量接近阈值');
    }

    // 文件相关性
    const relevantRatio = ctx.targetFiles.length > 0
      ? ctx.targetFiles.filter(f => ctx.workerFilesInContext.includes(f)).length / ctx.targetFiles.length
      : 0;
    
    if (relevantRatio < 0.5) {
      report.score -= 0.2;
      report.issues.push('Worker 上下文相关性低');
      report.suggestions.push('派生新 Worker');
    }

    // 错误历史
    if (ctx.workerHasErrors) {
      report.score -= 0.15;
      report.issues.push('Worker 有错误历史');
    }

    return report;
  }

  /**
   * 添加自定义规则
   */
  addRule(rule: DecisionRule): void {
    this.rules.push(rule);
  }

  /**
   * 移除规则
   */
  removeRule(name: string): void {
    this.rules = this.rules.filter(r => r.name !== name);
  }
}

// ==================== 配置 ====================

interface EngineConfig {
  tokenThreshold: number;
  debug: boolean;
  enableLogging: boolean;
}

const DEFAULT_CONFIG: EngineConfig = {
  tokenThreshold: 4000,
  debug: false,
  enableLogging: true
};

// ==================== 上下文质量报告 ====================

interface ContextQualityReport {
  score: number;  // 0-1
  issues: string[];
  suggestions: string[];
}

// ==================== 便捷函数 ====================

/**
 * 快速决策
 */
export function quickDecide(
  currentPhase: WorkflowPhase,
  targetPhase: WorkflowPhase,
  existingWorker: WorkerInfo | undefined,
  options: Partial<EngineConfig> = {}
): DecisionResult {
  const engine = new ContinueVsSpawnEngine(options);
  
  const context: DecisionContext = {
    currentPhase,
    targetPhase,
    tokenCount: 0,
    relevantFiles: [],
    targetFiles: existingWorker?.filesAccessed || [],
    researchScope: 'broad',
    implementationScope: 'narrow',
    isRetry: false,
    previousAttemptFailed: false,
    previousApproachWasWrong: false,
    existingWorker,
    workerFilesInContext: existingWorker?.filesAccessed || [],
    workerJustWroteCode: (existingWorker?.filesModified.length || 0) > 0,
    workerHasErrors: (existingWorker?.errorsEncountered.length || 0) > 0,
    isVerification: targetPhase === 'verify',
    isExploration: targetPhase === 'explore',
    isImplementation: targetPhase === 'implement'
  };

  return engine.decide(context);
}

/**
 * 决策场景说明
 */
export const DECISION_SCENARIO_DESCRIPTIONS: Record<DecisionScenario, {
  title: string;
  description: string;
  whenToUse: string;
}> = {
  worker_has_files: {
    title: 'Worker 已有文件',
    description: '现有 Worker 已经访问过所有目标文件',
    whenToUse: '继续在同一代码区域工作'
  },
  research_broad_implement_narrow: {
    title: '探索广实现窄',
    description: '探索阶段涉及面广，但实现只涉及特定文件',
    whenToUse: '从探索进入具体实现'
  },
  correcting_failed_attempt: {
    title: '修复失败',
    description: '之前的尝试失败了，但方法正确',
    whenToUse: '修复小错误，保留错误上下文'
  },
  verifying_fresh_eyes: {
    title: '验证 Fresh Eyes',
    description: '验证需要独立的视角',
    whenToUse: '验证刚写的代码'
  },
  wrong_approach_new_context: {
    title: '方法错误',
    description: '之前的方法完全错误',
    whenToUse: '重新开始，采用不同方法'
  },
  token_threshold: {
    title: 'Token 阈值',
    description: '上下文接近 token 限制',
    whenToUse: '保持性能，避免上下文膨胀'
  },
  context_pollution: {
    title: '上下文污染',
    description: '上下文包含无关信息',
    whenToUse: '清理上下文，重新开始'
  },
  default: {
    title: '默认',
    description: '没有明显匹配的场景',
    whenToUse: '一般情况'
  }
};

// ==================== 导出 ====================

export {
  ContinueVsSpawnEngine,
  EngineConfig,
  DEFAULT_CONFIG,
  ContextQualityReport
};
