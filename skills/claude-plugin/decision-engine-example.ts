/**
 * Continue vs Spawn 决策引擎使用示例
 */

import {
  ContinueVsSpawnEngine,
  DecisionContext,
  DecisionResult,
  WorkerInfo,
  quickDecide,
  DECISION_SCENARIO_DESCRIPTIONS
} from './decision-engine';

// ==================== 示例 1: 基本使用 ====================

function exampleBasicUsage() {
  console.log('=== 示例 1: 基本使用 ===\n');
  
  const engine = new ContinueVsSpawnEngine({ debug: true });
  
  // 场景：从 Explore 进入 Implement
  const context: DecisionContext = {
    currentPhase: 'explore',
    targetPhase: 'implement',
    tokenCount: 3500,
    relevantFiles: ['src/auth.ts', 'src/user.ts'],
    targetFiles: ['src/auth.ts'],
    researchScope: 'broad',
    implementationScope: 'narrow',
    isRetry: false,
    previousAttemptFailed: false,
    previousApproachWasWrong: false,
    existingWorker: {
      id: 'worker-001',
      type: 'research',
      startTime: new Date(),
      filesAccessed: ['src/auth.ts', 'src/user.ts', 'src/db.ts', 'src/config.ts'],
      filesModified: [],
      errorsEncountered: [],
      lastOutput: '探索完成'
    },
    workerFilesInContext: ['src/auth.ts', 'src/user.ts', 'src/db.ts', 'src/config.ts'],
    workerJustWroteCode: false,
    workerHasErrors: false,
    isVerification: false,
    isExploration: false,
    isImplementation: true
  };
  
  const result = engine.decide(context);
  
  console.log('决策结果:');
  console.log(`  动作: ${result.action}`);
  console.log(`  原因: ${result.reason}`);
  console.log(`  置信度: ${(result.confidence * 100).toFixed(1)}%`);
  console.log(`  场景: ${result.scenario}`);
  console.log(`  建议: ${result.recommendations?.join(', ')}`);
}

// ==================== 示例 2: 验证场景 ====================

function exampleVerification() {
  console.log('\n=== 示例 2: 验证场景（应该 Spawn） ===\n');
  
  const engine = new ContinueVsSpawnEngine();
  
  const context: DecisionContext = {
    currentPhase: 'implement',
    targetPhase: 'verify',
    tokenCount: 2000,
    relevantFiles: ['src/auth.ts'],
    targetFiles: ['src/auth.ts'],
    researchScope: 'narrow',
    implementationScope: 'narrow',
    isRetry: false,
    previousAttemptFailed: false,
    previousApproachWasWrong: false,
    existingWorker: {
      id: 'worker-002',
      type: 'implementation',
      startTime: new Date(),
      filesAccessed: ['src/auth.ts'],
      filesModified: ['src/auth.ts'],
      errorsEncountered: [],
      lastOutput: '实现完成'
    },
    workerFilesInContext: ['src/auth.ts'],
    workerJustWroteCode: true,
    workerHasErrors: false,
    isVerification: true,
    isExploration: false,
    isImplementation: false
  };
  
  const result = engine.decide(context);
  
  console.log('决策结果:');
  console.log(`  动作: ${result.action}`);
  console.log(`  原因: ${result.reason}`);
  console.log(`  场景: ${result.scenario}`);
}

// ==================== 示例 3: 修复失败 ====================

function exampleRetryFailed() {
  console.log('\n=== 示例 3: 修复失败（应该 Continue） ===\n');
  
  const engine = new ContinueVsSpawnEngine();
  
  const context: DecisionContext = {
    currentPhase: 'implement',
    targetPhase: 'implement',
    tokenCount: 3000,
    relevantFiles: ['src/auth.ts'],
    targetFiles: ['src/auth.ts'],
    researchScope: 'narrow',
    implementationScope: 'narrow',
    isRetry: true,
    previousAttemptFailed: true,
    previousApproachWasWrong: false,
    failureReason: 'TypeError: Cannot read property of undefined',
    existingWorker: {
      id: 'worker-003',
      type: 'implementation',
      startTime: new Date(),
      filesAccessed: ['src/auth.ts'],
      filesModified: ['src/auth.ts'],
      errorsEncountered: ['TypeError: Cannot read property of undefined'],
      lastOutput: '修复尝试失败'
    },
    workerFilesInContext: ['src/auth.ts'],
    workerJustWroteCode: true,
    workerHasErrors: true,
    isVerification: false,
    isExploration: false,
    isImplementation: true
  };
  
  const result = engine.decide(context);
  
  console.log('决策结果:');
  console.log(`  动作: ${result.action}`);
  console.log(`  原因: ${result.reason}`);
  console.log(`  场景: ${result.scenario}`);
}

// ==================== 示例 4: 方法错误 ====================

function exampleWrongApproach() {
  console.log('\n=== 示例 4: 方法错误（应该 Spawn） ===\n');
  
  const engine = new ContinueVsSpawnEngine();
  
  const context: DecisionContext = {
    currentPhase: 'implement',
    targetPhase: 'implement',
    tokenCount: 2500,
    relevantFiles: ['src/auth.ts'],
    targetFiles: ['src/auth.ts'],
    researchScope: 'narrow',
    implementationScope: 'narrow',
    isRetry: true,
    previousAttemptFailed: true,
    previousApproachWasWrong: true,
    failureReason: '架构设计错误，需要重新设计',
    existingWorker: {
      id: 'worker-004',
      type: 'implementation',
      startTime: new Date(),
      filesAccessed: ['src/auth.ts'],
      filesModified: ['src/auth.ts'],
      errorsEncountered: ['架构设计错误'],
      lastOutput: '方法错误'
    },
    workerFilesInContext: ['src/auth.ts'],
    workerJustWroteCode: true,
    workerHasErrors: true,
    isVerification: false,
    isExploration: false,
    isImplementation: true
  };
  
  const result = engine.decide(context);
  
  console.log('决策结果:');
  console.log(`  动作: ${result.action}`);
  console.log(`  原因: ${result.reason}`);
  console.log(`  场景: ${result.scenario}`);
}

// ==================== 示例 5: 快速决策 ====================

function exampleQuickDecide() {
  console.log('\n=== 示例 5: 快速决策 ===\n');
  
  const worker: WorkerInfo = {
    id: 'worker-005',
    type: 'research',
    startTime: new Date(),
    filesAccessed: ['src/auth.ts', 'src/user.ts'],
    filesModified: [],
    errorsEncountered: [],
    lastOutput: '探索完成'
  };
  
  const result = quickDecide('explore', 'implement', worker);
  
  console.log('快速决策结果:');
  console.log(`  动作: ${result.action}`);
  console.log(`  原因: ${result.reason}`);
}

// ==================== 示例 6: 上下文质量分析 ====================

function exampleContextQuality() {
  console.log('\n=== 示例 6: 上下文质量分析 ===\n');
  
  const engine = new ContinueVsSpawnEngine();
  
  const context: DecisionContext = {
    currentPhase: 'explore',
    targetPhase: 'implement',
    tokenCount: 6500,  // 高 token
    relevantFiles: ['src/auth.ts'],
    targetFiles: ['src/auth.ts'],
    researchScope: 'broad',
    implementationScope: 'narrow',
    isRetry: false,
    previousAttemptFailed: false,
    previousApproachWasWrong: false,
    existingWorker: {
      id: 'worker-006',
      type: 'research',
      startTime: new Date(),
      filesAccessed: ['src/auth.ts', 'src/user.ts', 'src/db.ts', 'src/config.ts', 
                       'src/utils.ts', 'src/middleware.ts', 'src/routes.ts'],
      filesModified: [],
      errorsEncountered: [],
      lastOutput: '探索完成'
    },
    workerFilesInContext: ['src/auth.ts', 'src/user.ts', 'src/db.ts', 'src/config.ts',
                           'src/utils.ts', 'src/middleware.ts', 'src/routes.ts'],
    workerJustWroteCode: false,
    workerHasErrors: false,
    isVerification: false,
    isExploration: false,
    isImplementation: true
  };
  
  const quality = engine.analyzeContextQuality(context);
  
  console.log('上下文质量报告:');
  console.log(`  评分: ${(quality.score * 100).toFixed(1)}%`);
  console.log(`  问题: ${quality.issues.join(', ') || '无'}`);
  console.log(`  建议: ${quality.suggestions.join(', ') || '无'}`);
}

// ==================== 示例 7: 场景说明 ====================

function exampleScenarioDescriptions() {
  console.log('\n=== 示例 7: 决策场景说明 ===\n');
  
  Object.entries(DECISION_SCENARIO_DESCRIPTIONS).forEach(([key, desc]) => {
    console.log(`${desc.title} (${key})`);
    console.log(`  ${desc.description}`);
    console.log(`  使用时机: ${desc.whenToUse}\n`);
  });
}

// ==================== 运行所有示例 ====================

function runAllExamples() {
  exampleBasicUsage();
  exampleVerification();
  exampleRetryFailed();
  exampleWrongApproach();
  exampleQuickDecide();
  exampleContextQuality();
  exampleScenarioDescriptions();
}

// ==================== 如果在 Node.js 环境运行 ====================

if (typeof window === 'undefined' && typeof process !== 'undefined') {
  runAllExamples();
}

// ==================== 导出 ====================

export {
  exampleBasicUsage,
  exampleVerification,
  exampleRetryFailed,
  exampleWrongApproach,
  exampleQuickDecide,
  exampleContextQuality,
  exampleScenarioDescriptions,
  runAllExamples
};
