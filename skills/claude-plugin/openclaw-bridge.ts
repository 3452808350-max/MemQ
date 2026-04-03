/**
 * Claude Plugin - OpenClaw Bridge
 * 
 * 将 Claude Plugin 模块桥接到 OpenClaw 的 sessions_spawn 工具
 */

import { sessions_spawn, sessions_send, sessions_list } from '../../../../../.openclaw/skills';
import { 
  CoordinatorWorkflow, 
  WorkflowPhase,
  buildCoordinatorSystemPrompt,
  buildWorkerDirective 
} from '../../../文档/IELTS-Obsidian/Projects/claude-plugin/src/coordinator-mode/coordinator';
import { 
  spawnFork, 
  spawnParallelForks,
  ForkResult,
  isInForkChild 
} from '../../../文档/IELTS-Obsidian/Projects/claude-plugin/src/fork-subagent/fork';
import {
  loadAgentDefinition,
  loadAgentsFromDir,
  AgentDefinition,
  BUILT_IN_AGENTS
} from '../../../文档/IELTS-Obsidian/Projects/claude-plugin/src/agent-definitions/parser';

// OpenClaw 会话上下文接口
interface OpenClawContext {
  sessionKey: string;
  messages: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
  }>;
}

// Coordinator 配置
interface CoordinatorConfig {
  maxParallelWorkers: number;
  defaultTimeoutMs: number;
  enableVerification: boolean;
}

const DEFAULT_CONFIG: CoordinatorConfig = {
  maxParallelWorkers: 4,
  defaultTimeoutMs: 300000,
  enableVerification: true
};

/**
 * 运行 Coordinator Mode 工作流
 */
export async function runCoordinatorMode(
  task: string,
  context: OpenClawContext,
  config: Partial<CoordinatorConfig> = {}
): Promise<string> {
  const fullConfig = { ...DEFAULT_CONFIG, ...config };
  
  // Phase 1: Research
  console.log('🔍 Phase 1: Research');
  const researchResults = await runResearchPhase(task, context, fullConfig);
  
  // Phase 2: Synthesis
  console.log('🧠 Phase 2: Synthesis');
  const synthesis = await runSynthesisPhase(researchResults);
  
  // Phase 3: Implementation
  console.log('⚙️ Phase 3: Implementation');
  const implementationResults = await runImplementationPhase(
    synthesis, 
    context, 
    fullConfig
  );
  
  // Phase 4: Verification (if enabled)
  let verificationResults: string | null = null;
  if (fullConfig.enableVerification) {
    console.log('✅ Phase 4: Verification');
    verificationResults = await runVerificationPhase(
      implementationResults,
      context,
      fullConfig
    );
  }
  
  // 汇总结果
  return formatCoordinatorResults({
    task,
    research: researchResults,
    synthesis,
    implementation: implementationResults,
    verification: verificationResults
  });
}

/**
 * Research Phase: 并行调查
 */
async function runResearchPhase(
  task: string,
  context: OpenClawContext,
  config: CoordinatorConfig
): Promise<Array<{ topic: string; result: string }>> {
  
  // 分析任务，确定研究方向
  const researchTopics = analyzeResearchTopics(task);
  
  // 并行派生 Research Worker
  const workerPromises = researchTopics.map(topic => 
    spawnResearchWorker(topic, context, config)
  );
  
  const results = await Promise.all(workerPromises);
  
  return researchTopics.map((topic, i) => ({
    topic,
    result: results[i]
  }));
}

/**
 * 分析任务确定研究方向
 */
function analyzeResearchTopics(task: string): string[] {
  // 简单启发式分析，实际可用 LLM 分析
  const topics: string[] = [];
  
  if (task.includes('代码') || task.includes('实现')) {
    topics.push('调查相关代码文件和模块结构');
  }
  if (task.includes('认证') || task.includes('auth')) {
    topics.push('分析现有认证机制和流程');
  }
  if (task.includes('API') || task.includes('接口')) {
    topics.push('调查 API 设计和现有端点');
  }
  if (topics.length === 0) {
    topics.push('调查项目结构和相关文件');
  }
  
  return topics.slice(0, 3); // 最多 3 个研究方向
}

/**
 * 派生 Research Worker
 */
async function spawnResearchWorker(
  topic: string,
  context: OpenClawContext,
  config: CoordinatorConfig
): Promise<string> {
  
  const directive = buildWorkerDirective('research', topic, {
    tools: ['Read', 'Grep', 'Glob', 'Bash']
  });
  
  // 使用 OpenClaw 的 sessions_spawn
  const result = await sessions_spawn({
    task: directive,
    runtime: 'subagent',
    mode: 'run',
    label: `research-${Date.now()}`,
    runTimeoutSeconds: Math.floor(config.defaultTimeoutMs / 1000)
  });
  
  // 获取子代理结果
  // 注意：实际实现需要轮询或使用 streamTo: 'parent'
  return `Research completed: ${topic}`;
}

/**
 * Synthesis Phase: 综合研究结果
 */
async function runSynthesisPhase(
  researchResults: Array<{ topic: string; result: string }>
): Promise<string> {
  // 在当前会话中综合结果
  const synthesis = researchResults
    .map(r => `## ${r.topic}\n${r.result}`)
    .join('\n\n');
  
  return `## 综合分析\n\n${synthesis}\n\n## 实施计划\n\n1. 基于调查结果设计实现方案\n2. 分步骤执行代码修改\n3. 验证实现正确性`;
}

/**
 * Implementation Phase: 执行实现
 */
async function runImplementationPhase(
  synthesis: string,
  context: OpenClawContext,
  config: CoordinatorConfig
): Promise<string> {
  
  const directive = buildWorkerDirective('implementation', synthesis, {
    tools: ['Read', 'Write', 'Edit', 'Bash'],
    maxTurns: 200
  });
  
  // 派生 Implementation Worker
  const result = await sessions_spawn({
    task: directive,
    runtime: 'subagent',
    mode: 'run',
    label: `implement-${Date.now()}`,
    runTimeoutSeconds: Math.floor(config.defaultTimeoutMs / 1000)
  });
  
  return `Implementation completed`;
}

/**
 * Verification Phase: 验证结果
 */
async function runVerificationPhase(
  implementation: string,
  context: OpenClawContext,
  config: CoordinatorConfig
): Promise<string> {
  
  const directive = buildWorkerDirective('verification', 
    `验证以下实现是否正确工作：\n${implementation}`,
    { tools: ['Read', 'Bash'] }
  );
  
  const result = await sessions_spawn({
    task: directive,
    runtime: 'subagent',
    mode: 'run',
    label: `verify-${Date.now()}`,
    runTimeoutSeconds: Math.floor(config.defaultTimeoutMs / 1000)
  });
  
  return `Verification completed`;
}

/**
 * 运行 Fork 模式（轻量级并行）
 */
export async function runForkMode(
  tasks: string[],
  context: OpenClawContext
): Promise<ForkResult[]> {
  
  // 检查递归
  if (isInForkChild(context.messages as any)) {
    throw new Error('Recursive fork detected');
  }
  
  // 并行执行所有任务
  const results: ForkResult[] = [];
  
  for (const task of tasks) {
    const result = await sessions_spawn({
      task: buildWorkerDirective('custom', task, {
        tools: ['Read', 'Grep', 'Bash']
      }),
      runtime: 'subagent',
      mode: 'run',
      label: `fork-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      runTimeoutSeconds: 300
    });
    
    results.push({
      scope: task,
      result: 'Fork execution completed',
      keyFiles: [],
      filesChanged: [],
      issues: []
    });
  }
  
  return results;
}

/**
 * 加载并使用特定 Agent
 */
export async function runWithAgent(
  agentName: string,
  task: string,
  context: OpenClawContext
): Promise<string> {
  
  // 查找 Agent 定义
  let agentDef = BUILT_IN_AGENTS.find(a => a.name === agentName);
  
  if (!agentDef) {
    // 尝试从用户目录加载
    try {
      const userAgents = loadAgentsFromDir(
        `${process.env.HOME}/.openclaw/agents`,
        'user'
      );
      agentDef = userAgents.find(a => a.name === agentName);
    } catch (e) {
      // 忽略加载错误
    }
  }
  
  if (!agentDef) {
    throw new Error(`Agent "${agentName}" not found`);
  }
  
  // 使用 Agent 定义派生子代理
  const directive = `${agentDef.systemPrompt}\n\n任务：${task}`;
  
  const result = await sessions_spawn({
    task: directive,
    runtime: 'subagent',
    mode: 'run',
    label: `${agentName}-${Date.now()}`,
    runTimeoutSeconds: agentDef.maxTurns || 300
  });
  
  return `Agent ${agentName} completed task`;
}

/**
 * 格式化 Coordinator 结果
 */
function formatCoordinatorResults(results: {
  task: string;
  research: Array<{ topic: string; result: string }>;
  synthesis: string;
  implementation: string;
  verification: string | null;
}): string {
  const researchSection = results.research
    .map(r => `### ${r.topic}\n${r.result}`)
    .join('\n\n');
  
  return `
# Coordinator Mode 执行结果

## 原始任务
${results.task}

## Phase 1: Research
${researchSection}

## Phase 2: Synthesis
${results.synthesis}

## Phase 3: Implementation
${results.implementation}

## Phase 4: Verification
${results.verification || '未启用'}

---
✅ Coordinator Mode 执行完成
`;
}

/**
 * 导出主要功能
 */
export {
  runCoordinatorMode,
  runForkMode,
  runWithAgent,
  CoordinatorConfig,
  OpenClawContext
};