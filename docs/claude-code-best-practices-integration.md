# Claude Code 最佳实践融入 OpenClaw 系统工程

## 概述

将 Claude Code 官方最佳实践融入 OpenClaw 的 Claude Plugin，提升多 Agent 系统的效率和可靠性。

---

## 1. 上下文管理最佳实践

### Claude Code 核心原则
- **上下文窗口会快速填满**，性能随之下降
- 管理上下文是最关键的资源优化

### OpenClaw 集成方案

#### 1.1 自动上下文管理

```typescript
// openclaw-bridge.ts 添加自动管理
interface ContextManagementConfig {
  autoClearBetweenPhases: boolean;  // 阶段间自动 /clear
  compactThreshold: number;         // Token 阈值，超过则 /compact
  useBtwForQuickQuestions: boolean; // 快速问答使用 /btw
}

// Coordinator Mode 集成
class CoordinatorWorkflow {
  private async transitionPhase(
    from: WorkflowPhase, 
    to: WorkflowPhase
  ): Promise<void> {
    // 阶段转换时自动清理上下文
    if (this.config.autoClearBetweenPhases) {
      await this.clearContext();
    }
    this.phase = to;
  }
}
```

#### 1.2 新增 OpenClaw 命令

| 命令 | 功能 | 使用场景 |
|------|------|----------|
| `/clear` | 重置上下文 | 无关任务之间 |
| `/compact <指令>` | 手动压缩 | 保留关键信息 |
| `/btw <问题>` | 快速问答 | 不污染上下文的查询 |
| `/rewind` | 回退状态 | 撤销错误操作 |

#### 1.3 Worker 上下文隔离

```typescript
// Worker 派生时自动清理
async function spawnWorker(
  type: WorkerType,
  directive: string
): Promise<Worker> {
  // Worker 只接收精简上下文
  const isolatedContext = buildIsolatedContext(directive);
  
  return sessions_spawn({
    task: isolatedContext,
    runtime: 'subagent',
    mode: 'run',
    // 不继承父会话历史
    inheritContext: false
  });
}
```

---

## 2. 四阶段工作流优化

### Claude Code 工作流
```
Explore → Plan → Implement → Commit
```

### OpenClaw Coordinator Mode 增强

#### 2.1 明确阶段定义

```typescript
enum WorkflowPhase {
  EXPLORE = 'explore',       // 代码库探索
  PLAN = 'plan',            // 架构规划
  IMPLEMENT = 'implement',  // 代码实现
  VERIFY = 'verify',        // 验证测试
  COMMIT = 'commit'         // 提交完成
}

interface PhaseConfig {
  allowedTools: string[];
  permissionMode: PermissionMode;
  maxTurns: number;
  requireVerification: boolean;
}

const PHASE_CONFIGS: Record<WorkflowPhase, PhaseConfig> = {
  [WorkflowPhase.EXPLORE]: {
    allowedTools: ['Read', 'Grep', 'Glob', 'Bash'],
    permissionMode: 'plan',      // 只读模式
    maxTurns: 100,
    requireVerification: false
  },
  [WorkflowPhase.PLAN]: {
    allowedTools: ['Read', 'Grep', 'Glob'],
    permissionMode: 'plan',
    maxTurns: 50,
    requireVerification: false
  },
  [WorkflowPhase.IMPLEMENT]: {
    allowedTools: ['Read', 'Write', 'Edit', 'Bash'],
    permissionMode: 'default',
    maxTurns: 200,
    requireVerification: true
  },
  [WorkflowPhase.VERIFY]: {
    allowedTools: ['Read', 'Bash'],
    permissionMode: 'default',
    maxTurns: 100,
    requireVerification: true
  },
  [WorkflowPhase.COMMIT]: {
    allowedTools: ['Bash'],
    permissionMode: 'auto',
    maxTurns: 20,
    requireVerification: false
  }
};
```

#### 2.2 Plan Mode 支持

```typescript
// 支持 Plan Mode（类似 Claude Code 的 Ctrl+G）
interface PlanModeConfig {
  enabled: boolean;
  editorCommand: string;  // 打开计划编辑器
  autoEdit: boolean;      // 是否允许自动编辑计划
}

// 用户命令
/plan          // 进入 Plan Mode
/plan edit     // 编辑当前计划
/plan approve  // 批准计划，进入 Implement
```

---

## 3. Continue vs Spawn 决策引擎

### Claude Code 决策逻辑

| 场景 | 决策 | 原因 |
|------|------|------|
| Worker 已有相关文件 | Continue | 复用上下文 |
| Research 广但 Implementation 窄 | Spawn | 避免探索噪音 |
| 修复失败尝试 | Continue | 保留错误上下文 |
| 验证刚写的代码 | Spawn | 验证者需要 fresh eyes |
| 之前方法错误 | Spawn | 错误上下文污染重试 |

### OpenClaw 实现

```typescript
// coordinator.ts 增强决策逻辑
interface ContinueVsSpawnContext {
  // 上下文分析
  researchFiles: string[];
  targetFiles: string[];
  
  // 范围分析
  researchScope: 'broad' | 'narrow';
  implementationScope: 'broad' | 'narrow';
  
  // 历史分析
  isRetry: boolean;
  previousAttemptFailed: boolean;
  previousApproachWasWrong: boolean;
  
  // 任务类型
  isVerification: boolean;
  targetWorkerJustWroteCode: boolean;
}

function decideContinueOrSpawn(
  context: ContinueVsSpawnContext
): Decision {
  // Scene 1: Worker already has files in context
  if (hasAllFilesInContext(context)) {
    return { action: 'continue', reason: 'Worker already has files' };
  }
  
  // Scene 2: Research broad but implementation narrow
  if (context.researchScope === 'broad' && 
      context.implementationScope === 'narrow') {
    return { action: 'spawn', reason: 'Avoid exploration noise' };
  }
  
  // Scene 3: Correcting failed attempt
  if (context.isRetry && context.previousAttemptFailed) {
    return { action: 'continue', reason: 'Worker has error context' };
  }
  
  // Scene 4: Verifying code just written
  if (context.isVerification && context.targetWorkerJustWroteCode) {
    return { action: 'spawn', reason: 'Verifier needs fresh eyes' };
  }
  
  // Scene 5: First attempt was wrong approach
  if (context.isRetry && context.previousApproachWasWrong) {
    return { action: 'spawn', reason: 'Wrong-approach context pollutes' };
  }
  
  // Default
  return { action: 'spawn', reason: 'No useful context to reuse' };
}
```

---

## 4. 权限系统增强

### Claude Code 7 种 Permission Modes

| 模式 | 说明 | OpenClaw 映射 |
|------|------|---------------|
| `default` | 每次询问 | `default` |
| `plan` | 只读规划 | `plan` |
| `auto` | 自动批准低风险 | `auto` |
| `acceptEdits` | 自动接受编辑 | `acceptEdits` |
| `bubble` | 隔离沙箱 | `bubble` |
| `bypassPermissions` | 绕过权限 | `bypassPermissions` |
| `dontAsk` | 不询问 | `dontAsk` |

### OpenClaw Permission System 增强

```typescript
// permission-system/permissions.ts
interface PermissionRule {
  tool: string;
  action: 'allow' | 'deny' | 'ask';
  condition?: (context: ExecutionContext) => boolean;
}

interface PermissionModeConfig {
  mode: PermissionMode;
  rules: PermissionRule[];
  autoApprovePatterns: RegExp[];
  requireConfirmationFor: string[];
}

// 增强的权限规则引擎
class PermissionEngine {
  evaluate(tool: string, context: ExecutionContext): PermissionDecision {
    const mode = this.getCurrentMode();
    
    // 检查显式规则
    const rule = mode.rules.find(r => r.tool === tool);
    if (rule) {
      if (rule.condition && !rule.condition(context)) {
        return { action: 'ask', reason: 'Condition not met' };
      }
      return { action: rule.action };
    }
    
    // 检查自动批准模式
    if (mode.autoApprovePatterns.some(p => p.test(tool))) {
      return { action: 'allow', auto: true };
    }
    
    // 默认行为
    return this.getDefaultDecision(mode.mode);
  }
}
```

---

## 5. 验证驱动开发

### Claude Code 核心原则
> **给 Claude 验证手段** — 这是最高杠杆的做法

### OpenClaw 集成

#### 5.1 验证优先设计

```typescript
interface TaskWithVerification {
  task: string;
  verificationCriteria: string[];
  testCommand?: string;
  expectedOutput?: string;
}

// 示例任务定义
const task: TaskWithVerification = {
  task: '实现 validateEmail 函数',
  verificationCriteria: [
    'user@example.com → true',
    'invalid → false',
    'user@.com → false'
  ],
  testCommand: 'npm test validateEmail',
  expectedOutput: '3 passing'
};
```

#### 5.2 Worker 自动验证

```typescript
// Worker 完成后自动验证
async function runWorkerWithVerification(
  worker: Worker,
  criteria: VerificationCriteria
): Promise<VerifiedResult> {
  // 1. 执行 Worker
  const result = await runWorker(worker);
  
  // 2. 自动验证
  const verification = await verifyResult(result, criteria);
  
  // 3. 验证失败则重试
  if (!verification.passed) {
    return await retryWithContext(worker, verification.issues);
  }
  
  return { result, verification };
}
```

#### 5.3 用户命令

```
/coordinator 实现 OAuth2 登录 \
  --verify "登录成功返回 token" \
  --verify "登录失败返回 401" \
  --test "npm run test:oauth"
```

---

## 6. 具体实施计划

### Phase 1: 核心增强（1-2 天）

1. **上下文管理**
   - [ ] 实现自动 `/clear` 在阶段间
   - [ ] 添加 `/btw` 命令支持
   - [ ] Worker 上下文隔离

2. **权限系统**
   - [ ] 完善 7 种 permission modes
   - [ ] 阶段级权限控制
   - [ ] 工具过滤规则

### Phase 2: 工作流优化（2-3 天）

1. **四阶段工作流**
   - [ ] 明确 Explore/Plan/Implement/Verify/Commit
   - [ ] Plan Mode 支持（/plan, /plan edit, /plan approve）
   - [ ] 阶段级工具限制

2. **决策引擎**
   - [ ] Continue vs Spawn 自动决策
   - [ ] 上下文分析（文件、范围、历史）
   - [ ] 决策理由记录

### Phase 3: 验证系统（1-2 天）

1. **验证驱动**
   - [ ] 任务定义添加 verificationCriteria
   - [ ] 自动验证执行
   - [ ] 失败重试机制

2. **测试集成**
   - [ ] 测试命令自动运行
   - [ ] 结果解析和报告

---

## 7. 关键代码实现

### 7.1 增强的 CoordinatorWorkflow

```typescript
class EnhancedCoordinatorWorkflow {
  // 阶段配置
  private phaseConfigs: Record<WorkflowPhase, PhaseConfig>;
  
  // 决策引擎
  private decisionEngine: ContinueVsSpawnEngine;
  
  // 验证器
  private verifier: VerificationEngine;
  
  async run(task: TaskWithVerification): Promise<Result> {
    // Phase 1: Explore
    const exploreResult = await this.runExplorePhase(task);
    await this.maybeClearContext();
    
    // Phase 2: Plan
    const planResult = await this.runPlanPhase(exploreResult);
    await this.maybeClearContext();
    
    // Phase 3: Implement
    const implementResult = await this.runImplementPhase(planResult);
    
    // Phase 4: Verify
    const verifyResult = await this.runVerifyPhase(
      implementResult, 
      task.verificationCriteria
    );
    
    // Phase 5: Commit
    await this.runCommitPhase(verifyResult);
    
    return this.synthesizeResults();
  }
  
  private async spawnPhaseWorker(
    phase: WorkflowPhase,
    directive: string,
    previousWorker?: Worker
  ): Promise<Worker> {
    // 决策：Continue vs Spawn
    const decision = this.decisionEngine.decide({
      phase,
      previousWorker,
      directive
    });
    
    if (decision.action === 'continue' && previousWorker) {
      // 复用现有 Worker，发送新指令
      return await this.continueWorker(previousWorker, directive);
    } else {
      // 派生新 Worker
      return await this.spawnNewWorker(phase, directive);
    }
  }
}
```

### 7.2 上下文管理器

```typescript
class ContextManager {
  private tokenCount: number;
  private lastClearTime: Date;
  
  shouldClear(): boolean {
    // 自动清理阈值
    if (this.tokenCount > this.config.compactThreshold) {
      return true;
    }
    
    // 阶段转换时
    if (this.config.autoClearBetweenPhases && this.isPhaseTransition()) {
      return true;
    }
    
    return false;
  }
  
  async clearContext(preserve?: string[]): Promise<void> {
    // 保留指定内容，清理其余
    await sessions_send({
      sessionKey: this.sessionKey,
      message: '/clear'
    });
    
    // 重新注入保留内容
    if (preserve) {
      for (const item of preserve) {
        await this.injectContext(item);
      }
    }
  }
}
```

---

## 8. 使用示例

### 示例 1：完整工作流

```bash
# 启动 Coordinator Mode
/coordinator 实现用户认证系统

# 自动执行：
# 1. Explore: code-explorer agent 调查现有代码
# 2. Plan: code-planner agent 设计架构
# 3. Implement: implementer agent 编写代码
# 4. Verify: verifier agent 运行测试
# 5. Commit: 自动提交代码
```

### 示例 2：带验证标准

```bash
/coordinator 实现密码重置功能 \
  --verify "发送重置邮件成功" \
  --verify "链接 24 小时过期" \
  --verify "只能使用一次" \
  --test "npm run test:password-reset"
```

### 示例 3：Plan Mode

```bash
# 进入规划模式
/plan 设计新的 API 架构

# 编辑计划
/plan edit

# 批准并执行
/plan approve
```

---

## 9. 总结

### 融入的 Claude Code 最佳实践

| 实践 | OpenClaw 实现 | 效果 |
|------|--------------|------|
| 上下文管理 | 自动 /clear, /compact, /btw | 减少 token 浪费 |
| 四阶段工作流 | Explore→Plan→Implement→Verify→Commit | 系统化开发 |
| Continue vs Spawn | 智能决策引擎 | 优化上下文复用 |
| 权限模式 | 7 种 modes + 阶段级控制 | 安全灵活 |
| 验证驱动 | verificationCriteria + 自动验证 | 提高质量 |

### 下一步行动

1. 实现上下文管理增强
2. 完善权限系统
3. 添加 Continue vs Spawn 决策引擎
4. 集成验证系统
5. 测试和优化

---

*基于 Claude Code 最佳实践 | 46 测试覆盖 | Commit 3156f72*