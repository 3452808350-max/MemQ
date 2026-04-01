# Module 05: Coordinator Mode

## 目标

实现复杂任务编排，支持四阶段工作流和多 Worker 并行。

## 核心设计

### 架构

```
┌─────────────────────────────────────────┐
│           Coordinator                   │
│  ┌─────────────────────────────────┐    │
│  │  System Prompt (6 章节)         │    │
│  │  1. Your Role                   │    │
│  │  2. Your Tools                  │    │
│  │  3. Workers                     │    │
│  │  4. Task Workflow               │    │
│  │  5. Writing Worker Prompts      │    │
│  │  6. Example Session             │    │
│  └─────────────────────────────────┘    │
│                    │                    │
│  ┌─────────────────┼─────────────────┐  │
│  │                 │                 │  │
│  ▼                 ▼                 ▼  │
│ Worker 1       Worker 2       Worker 3  │
│ (Research)    (Research)    (Research)  │
│     │              │              │     │
│     └──────────────┼──────────────┘     │
│                    │                    │
│                    ▼                    │
│              Coordinator                │
│           (Synthesis Phase)             │
│                    │                    │
│  ┌─────────────────┼─────────────────┐  │
│  │                 │                 │  │
│  ▼                 ▼                 ▼  │
│ Worker 4       Worker 5       Worker 6  │
│(Implementation)(Implementation)(Verify) │
└─────────────────────────────────────────┘
```

### 启用条件

```typescript
function isCoordinatorMode(): boolean {
  return feature('COORDINATOR_MODE') && 
         process.env.CLAUDE_CODE_COORDINATOR_MODE === '1'
}

// 与 Fork Subagent 互斥
function canUseFork(): boolean {
  return isForkSubagentEnabled() && !isCoordinatorMode()
}
```

### 四阶段工作流

```typescript
type WorkflowPhase = 
  | 'research'        // 调查阶段
  | 'synthesis'       // 综合阶段
  | 'implementation'  // 实现阶段
  | 'verification'    // 验证阶段

interface Workflow {
  currentPhase: WorkflowPhase
  workers: Map<string, Worker>
  completedTasks: TaskResult[]
}

class CoordinatorWorkflow {
  private phase: WorkflowPhase = 'research'
  private workers: Map<string, Worker> = new Map()
  
  async runPhase(phase: WorkflowPhase): Promise<void> {
    switch (phase) {
      case 'research':
        await this.runResearchPhase()
        break
      case 'synthesis':
        await this.runSynthesisPhase()
        break
      case 'implementation':
        await this.runImplementationPhase()
        break
      case 'verification':
        await this.runVerificationPhase()
        break
    }
  }
  
  private async runResearchPhase(): Promise<void> {
    // 1. 分析任务，确定研究方向
    const researchDirections = this.analyzeTask()
    
    // 2. 并行启动 Research Workers
    const workers = researchDirections.map(dir => 
      this.spawnWorker('research', dir)
    )
    
    // 3. 等待所有 Workers 完成
    const results = await Promise.all(workers.map(w => w.wait()))
    
    // 4. 收集结果，进入 Synthesis
    this.completedTasks.push(...results)
    this.phase = 'synthesis'
  }
  
  private async runSynthesisPhase(): Promise<void> {
    // Coordinator 自己执行，不派 Worker
    const synthesis = await this.synthesize(this.completedTasks)
    
    // 生成 Implementation Plan
    this.implementationPlan = synthesis.plan
    this.phase = 'implementation'
  }
  
  private async runImplementationPhase(): Promise<void> {
    // 1. 按文件分组任务
    const groups = this.groupByFile(this.implementationPlan)
    
    // 2. 串行执行每组（同一文件不并行）
    for (const group of groups) {
      const worker = await this.spawnWorker('implementation', group)
      await worker.wait()
    }
    
    this.phase = 'verification'
  }
  
  private async runVerificationPhase(): Promise<void> {
    // 1. 启动 Verification Workers
    const verifiers = this.spawnVerificationWorkers()
    
    // 2. 等待结果
    const results = await Promise.all(verifiers.map(v => v.wait()))
    
    // 3. 处理验证结果
    this.handleVerificationResults(results)
  }
}
```

### Worker 工具限制

```typescript
// Coordinator 可用工具
const COORDINATOR_TOOLS = [
  'Agent',              // 派生 Worker
  'SendMessage',        // 与 Worker 通信
  'TaskStop',           // 停止 Worker
  'SubscribePrActivity', // PR 订阅
  'UnsubscribePrActivity'
]

// Worker 工具 (Simple 模式)
const WORKER_TOOLS_SIMPLE = [
  'Bash',
  'FileRead',
  'FileEdit'
]

// Worker 工具 (Full 模式)
const WORKER_TOOLS_FULL = [
  ...ASYNC_AGENT_ALLOWED_TOOLS
].filter(t => !INTERNAL_WORKER_TOOLS.includes(t))

// Worker 禁止工具 (内部工具)
const INTERNAL_WORKER_TOOLS = [
  'TeamCreate',
  'TeamDelete',
  'SendMessage',
  'SyntheticOutput'
]
```

### Continue vs Spawn 决策

```typescript
interface ContinueVsSpawnDecision {
  action: 'continue' | 'spawn'
  reason: string
}

function decideContinueOrSpawn(
  context: TaskContext,
  workerHistory: Worker[]
): ContinueVsSpawnDecision {
  // 决策矩阵
  
  // 场景 1: 研究文件正好是需编辑的文件
  if (context.researchFiles === context.targetFiles) {
    return { 
      action: 'continue', 
      reason: 'Worker already has files in context' 
    }
  }
  
  // 场景 2: 研究广泛但实现狭窄
  if (context.researchScope === 'broad' && context.implementationScope === 'narrow') {
    return { 
      action: 'spawn', 
      reason: 'Avoid exploration noise, focused context is cleaner' 
    }
  }
  
  // 场景 3: 纠正失败
  if (context.isRetry && context.previousAttemptFailed) {
    return { 
      action: 'continue', 
      reason: 'Worker has error context' 
    }
  }
  
  // 场景 4: 验证刚写的代码
  if (context.isVerification && context.targetWorkerJustWroteCode) {
    return { 
      action: 'spawn', 
      reason: 'Verifier should have fresh eyes' 
    }
  }
  
  // 场景 5: 第一次实现完全错误
  if (context.isRetry && context.previousApproachWasWrong) {
    return { 
      action: 'spawn', 
      reason: 'Wrong-approach context pollutes retry' 
    }
  }
  
  // 默认: 无关任务 → Spawn fresh
  return { 
    action: 'spawn', 
    reason: 'No useful context to reuse' 
  }
}
```

### 系统提示词结构

```markdown
# Coordinator System Prompt

## 1. Your Role

You are the Coordinator. Your job is to orchestrate workers to accomplish complex tasks.

- Every message you send is to the user
- Workers report to you via <task-notification>
- You synthesize worker results and make decisions

## 2. Your Tools

- **Agent**: Spawn workers with specific directives
- **SendMessage**: Send messages to workers
- **TaskStop**: Stop a running worker
- **SubscribePrActivity** / **UnsubscribePrActivity**: PR notifications

## 3. Workers

Workers are autonomous agents that execute tasks in parallel.

- Workers do NOT see the conversation between you and the user
- Workers only see their assigned task
- Workers report results via <task-notification>

### Worker Tools

- Simple mode: Bash, FileRead, FileEdit
- Full mode: All async tools except internal ones

### Internal Tools (Workers cannot use)

- TeamCreate, TeamDelete, SendMessage, SyntheticOutput

## 4. Task Workflow

### Phase 1: Research

Spawn parallel workers to investigate the codebase.

- Each worker: focused research task
- You: wait for all, synthesize findings

### Phase 2: Synthesis

You analyze worker findings and create implementation plan.

### Phase 3: Implementation

Spawn workers to make changes.

- Same file set → one worker at a time
- Different file sets → parallel OK

### Phase 4: Verification

Spawn workers to verify the changes work.

- Can run parallel with implementation (different areas)
- Must prove code works, not just confirm existence

## 5. Writing Worker Prompts

### DO

- Be specific about what to investigate
- Include file paths when known
- Define clear success criteria

### DON'T

- Ask workers to suggest next steps
- Include conversational filler
- Be vague about scope

## 6. Example Session

[完整示例...]
```

### 与