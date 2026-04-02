# Claude Code 上下文管理机制深度分析

## 概述

Claude Code 的上下文管理是其多 Agent 架构的核心，涉及 Token 预算、窗口策略、工具输出管理、多 Agent 上下文隔离等多个层面。

---

## 一、Token 管理与窗口策略

### 1.1 核心常量

```typescript
// 基于源码分析的关键常量
export const CONTEXT_WINDOW_LIMITS = {
  // Claude 3.5 Sonnet 的上下文窗口
  SONNET: 200000,  // 200K tokens
  OPUS: 200000,    // 200K tokens
  HAIKU: 200000,   // 200K tokens
};

// Token 预算分配
export const TOKEN_BUDGET = {
  SYSTEM_PROMPT: 0.15,      // 15% 给 System Prompt
  TOOL_DEFINITIONS: 0.10,   // 10% 给工具定义
  MESSAGE_HISTORY: 0.60,    // 60% 给消息历史
  RESERVE: 0.15,            // 15% 预留
};

// 关键阈值
export const TOKEN_THRESHOLDS = {
  WARNING: 0.75,    // 75% 使用率警告
  CRITICAL: 0.90,   // 90% 使用率关键
  TRUNCATION: 0.95, // 95% 触发截断
};
```

### 1.2 消息历史管理策略

```typescript
// 消息优先级分类
export enum MessagePriority {
  CRITICAL = 1,    // 系统消息、错误消息
  HIGH = 2,        // 用户指令、工具调用
  MEDIUM = 3,      // 工具输出、Agent 响应
  LOW = 4,         // 元数据、状态信息
  EPHEMERAL = 5,   // 可丢弃的临时信息
}

// 消息保留策略
export interface MessageRetentionPolicy {
  // 始终保留的消息类型
  preserveTypes: MessageType[];
  // 保留最近 N 条
  recentCount: number;
  // 摘要阈值（超过此数量的旧消息转为摘要）
  summarizationThreshold: number;
}

export const DEFAULT_RETENTION_POLICY: MessageRetentionPolicy = {
  preserveTypes: ['system', 'user_directive', 'error'],
  recentCount: 20,
  summarizationThreshold: 10,
};
```

### 1.3 上下文截断算法

```typescript
/**
 * 智能上下文截断
 * 优先保留高优先级消息，低优先级消息转为摘要或丢弃
 */
export function truncateContext(
  messages: Message[],
  maxTokens: number,
  policy: MessageRetentionPolicy
): TruncatedContext {
  const sorted = messages.sort((a, b) => 
    (a.priority || MessagePriority.EPHEMERAL) - 
    (b.priority || MessagePriority.EPHEMERAL)
  );
  
  const preserved: Message[] = [];
  const summarized: Summary[] = [];
  const dropped: Message[] = [];
  
  let currentTokens = 0;
  
  for (const msg of sorted) {
    const msgTokens = estimateTokens(msg);
    
    // 关键消息始终保留
    if (policy.preserveTypes.includes(msg.type)) {
      preserved.push(msg);
      currentTokens += msgTokens;
      continue;
    }
    
    // 检查是否还有空间
    if (currentTokens + msgTokens <= maxTokens * TOKEN_THRESHOLDS.TRUNCATION) {
      preserved.push(msg);
      currentTokens += msgTokens;
    } else if (msg.priority <= MessagePriority.MEDIUM) {
      // 中等优先级转为摘要
      summarized.push(createSummary(msg));
      currentTokens += estimateTokens(summarized[summarized.length - 1]);
    } else {
      // 低优先级丢弃
      dropped.push(msg);
    }
  }
  
  return { preserved, summarized, dropped, totalTokens: currentTokens };
}
```

---

## 二、Tool Output 与文件内容管理

### 2.1 工具输出大小限制

```typescript
// 工具输出限制配置
export const TOOL_OUTPUT_LIMITS = {
  // 默认输出限制
  DEFAULT_MAX_OUTPUT: 10000,  // 10K 字符
  
  // 特定工具限制
  FILE_READ: 50000,           // 50K 字符
  BASH: 20000,                // 20K 字符
  GLOB: 5000,                 // 5K 字符
  GREP: 10000,                // 10K 字符
  
  // 截断提示
  TRUNCATION_MARKER: '\n... (truncated)',
};

// 输出截断策略
export enum TruncationStrategy {
  HEAD,      // 保留开头
  TAIL,      // 保留结尾
  SMART,     // 智能截断（保留关键部分）
  SUMMARIZE, // 生成摘要
}
```

### 2.2 大文件读取策略

```typescript
/**
 * 大文件分页读取
 * 避免一次性加载大文件到上下文
 */
export interface FileReadOptions {
  path: string;
  offset?: number;      // 起始行号
  limit?: number;       // 读取行数
  maxChars?: number;    // 最大字符数
}

export interface FileChunk {
  content: string;
  startLine: number;
  endLine: number;
  totalLines: number;
  hasMore: boolean;
}

export function readFileChunk(options: FileReadOptions): FileChunk {
  // 实现分块读取逻辑
  // 1. 检查文件大小
  // 2. 如果超过阈值，使用分页
  // 3. 返回当前块 + 元数据
}

// 文件大小阈值
export const FILE_SIZE_THRESHOLDS = {
  SMALL: 1000,      // < 1K 行：直接读取
  MEDIUM: 5000,     // 1K-5K 行：分块读取
  LARGE: 10000,     // > 5K 行：需要特殊处理
  HUGE: 50000,      // > 10K 行：仅读取结构/摘要
};
```

### 2.3 文件内容缓存机制

```typescript
/**
 * 文件内容缓存
 * 避免重复读取相同文件
 */
export class FileContentCache {
  private cache: Map<string, CachedFile> = new Map();
  private maxSize: number;
  private currentSize: number = 0;
  
  constructor(maxSizeMB: number = 50) {
    this.maxSize = maxSizeMB * 1024 * 1024;
  }
  
  get(path: string): CachedFile | undefined {
    const entry = this.cache.get(path);
    if (entry && !this.isExpired(entry)) {
      entry.lastAccessed = Date.now();
      return entry;
    }
    return undefined;
  }
  
  set(path: string, content: string, metadata: FileMetadata): void {
    const size = content.length * 2; // 粗略估计 UTF-16 大小
    
    // 如果超过缓存限制，清理旧条目
    while (this.currentSize + size > this.maxSize) {
      this.evictLRU();
    }
    
    this.cache.set(path, {
      content,
      metadata,
      size,
      lastAccessed: Date.now(),
      createdAt: Date.now(),
    });
    
    this.currentSize += size;
  }
  
  private evictLRU(): void {
    // 移除最近最少使用的条目
    let oldest: string | undefined;
    let oldestTime = Infinity;
    
    for (const [path, entry] of this.cache) {
      if (entry.lastAccessed < oldestTime) {
        oldestTime = entry.lastAccessed;
        oldest = path;
      }
    }
    
    if (oldest) {
      const entry = this.cache.get(oldest)!;
      this.currentSize -= entry.size;
      this.cache.delete(oldest);
    }
  }
}
```

### 2.4 Lazy Loading 策略

```typescript
/**
 * 延迟加载文件内容
 * 只在需要时加载文件到上下文
 */
export class LazyFileLoader {
  private fileIndex: Map<string, FileIndexEntry> = new Map();
  private loadedContent: Map<string, string> = new Map();
  
  // 索引文件但不加载内容
  indexFile(path: string): void {
    const stats = getFileStats(path);
    this.fileIndex.set(path, {
      path,
      size: stats.size,
      lines: stats.lines,
      modified: stats.mtime,
      indexed: true,
      loaded: false,
    });
  }
  
  // 按需加载文件内容
  loadFile(path: string, options?: Partial<FileReadOptions>): string {
    const cached = this.loadedContent.get(path);
    if (cached) return cached;
    
    const index = this.fileIndex.get(path);
    if (!index) throw new Error(`File not indexed: ${path}`);
    
    // 根据文件大小决定加载策略
    if (index.lines > FILE_SIZE_THRESHOLDS.LARGE) {
      return this.loadLargeFile(path, options);
    }
    
    const content = readFileSync(path, 'utf-8');
    this.loadedContent.set(path, content);
    index.loaded = true;
    
    return content;
  }
  
  private loadLargeFile(path: string, options?: Partial<FileReadOptions>): string {
    // 大文件只加载指定部分
    const { offset = 0, limit = 100 } = options || {};
    return readFileChunk({ path, offset, limit }).content;
  }
}
```

---

## 三、Multi-Agent 上下文隔离与传递

### 3.1 Fork Subagent 的上下文继承

```typescript
/**
 * Fork Subagent 的上下文处理
 * 父 Agent 可以选择性传递上下文给 Fork Worker
 */
export interface ForkContext {
  // 继承的上下文
  inherited: {
    // 文件上下文（文件路径列表）
    files: string[];
    // 环境变量
    env: Record<string, string>;
    // 工作目录
    cwd: string;
    // Git 状态
    gitStatus?: GitStatus;
  };
  
  // 不继承的上下文（隔离）
  isolated: {
    // 消息历史
    messageHistory: Message[];
    // 工具调用历史
    toolHistory: ToolCall[];
    // 内部状态
    internalState: Map<string, any>;
  };
  
  // 指令上下文
  directive: {
    // 父 Agent 的指令
    parentDirective: string;
    // 派生的 Worker 指令
    workerDirective: string;
    // 文件范围限制
    scope: string[];
  };
}

// Fork 上下文配置
export interface ForkContextConfig {
  // 是否继承文件上下文
  inheritFiles: boolean;
  // 是否继承环境
  inheritEnv: boolean;
  // 是否继承 Git 状态
  inheritGitStatus: boolean;
  // 消息历史继承数量（0 = 不继承）
  messageHistoryCount: number;
}

export const DEFAULT_FORK_CONFIG: ForkContextConfig = {
  inheritFiles: true,
  inheritEnv: true,
  inheritGitStatus: true,
  messageHistoryCount: 0, // Fork Worker 不继承消息历史
};
```

### 3.2 Continue vs Spawn 决策逻辑

```typescript
/**
 * Continue vs Spawn 决策
 * 决定是让当前 Worker 继续工作，还是 Spawn 新的 Worker
 */
export interface ContinueVsSpawnDecision {
  action: 'continue' | 'spawn';
  reason: string;
}

// 决策场景
export enum DecisionScene {
  // 场景1: Worker 有精确文件在上下文中
  EXACT_FILES_IN_CONTEXT = 'exact_files_in_context',
  // 场景2: 修正/扩展现有工作
  CORRECT_EXTEND_WORK = 'correct_extend_work',
  // 场景3: Worker 有错误上下文
  ERROR_CONTEXT = 'error_context',
  // 场景4: 研究广泛但实现狭窄
  BROAD_RESEARCH_NARROW_IMPL = 'broad_research_narrow_impl',
  // 场景5: 验证不同 Worker 的代码
  VERIFY_DIFFERENT_WORKER = 'verify_different_worker',
}

// Continue 场景（保持当前 Worker）
const CONTINUE_SCENES = [
  DecisionScene.EXACT_FILES_IN_CONTEXT,
  DecisionScene.CORRECT_EXTEND_WORK,
  DecisionScene.ERROR_CONTEXT,
];

// Spawn 场景（创建新 Worker）
const SPAWN_SCENES = [
  DecisionScene.BROAD_RESEARCH_NARROW_IMPL,
  DecisionScene.VERIFY_DIFFERENT_WORKER,
];

export function decideContinueOrSpawn(
  scene: DecisionScene,
  context: TaskContext
): ContinueVsSpawnDecision {
  // 场景1-3: Continue
  if (CONTINUE_SCENES.includes(scene)) {
    return {
      action: 'continue',
      reason: getContinueReason(scene, context)
    };
  }
  
  // 场景4-5: Spawn
  if (SPAWN_SCENES.includes(scene)) {
    return {
      action: 'spawn',
      reason: getSpawnReason(scene, context)
    };
  }
  
  // 默认: Continue
  return {
    action: 'continue',
    reason: 'Default to continue for efficiency'
  };
}

function getContinueReason(scene: DecisionScene, context: TaskContext): string {
  switch (scene) {
    case DecisionScene.EXACT_FILES_IN_CONTEXT:
      return 'Worker has exact files in context, continuing is efficient';
    case DecisionScene.CORRECT_EXTEND_WORK:
      return 'Correcting or extending recent work, context is valuable';
    case DecisionScene.ERROR_CONTEXT:
      return 'Worker has error context, continuing allows iterative fix';
    default:
      return 'Continue for context continuity';
  }
}

function getSpawnReason(scene: DecisionScene, context: TaskContext): string {
  switch (scene) {
    case DecisionScene.BROAD_RESEARCH_NARROW_IMPL:
      return 'Research was broad but implementation is narrow, fresh context needed';
    case DecisionScene.VERIFY_DIFFERENT_WORKER:
      return 'Verifying different worker\'s code, fresh perspective needed';
    default:
      return 'Spawn for fresh context';
  }
}
```

### 3.3 Coordinator Mode 的上下文管理

```typescript
/**
 * Coordinator 管理多个 Worker 的上下文
 */
export interface CoordinatorContext {
  // 全局上下文（所有 Worker 共享）
  global: {
    // 项目结构
    projectStructure: ProjectStructure;
    // 共享知识库
    sharedKnowledge: Map<string, any>;
    // 任务依赖图
    dependencyGraph: DependencyGraph;
  };
  
  // Worker 特定上下文
  workers: Map<string, WorkerContext>;
  
  // 阶段上下文
  phases: Map<WorkflowPhase, PhaseContext>;
}

export interface WorkerContext {
  workerId: string;
  type: WorkerType;
  // Worker 的私有上下文
  privateContext: {
    files: string[];
    messages: Message[];
    toolCalls: ToolCall[];
  };
  // 与其他 Worker 共享的上下文
  sharedContext: {
    inputFrom: string[];
    outputTo: string[];
  };
}

/**
 * 任务分片时的上下文分配
 */
export function allocateContextForWorker(
  coordinatorContext: CoordinatorContext,
  workerType: WorkerType,
  task: Task
): WorkerContext {
  const workerId = generateWorkerId();
  
  // 根据 Worker 类型分配不同的上下文
  switch (workerType) {
    case 'research':
      return allocateResearchContext(coordinatorContext, workerId, task);
    case 'implementation':
      return allocateImplementationContext(coordinatorContext, workerId, task);
    case 'verification':
      return allocateVerificationContext(coordinatorContext, workerId, task);
    default:
      return allocateDefaultContext(coordinatorContext, workerId, task);
  }
}

function allocateResearchContext(
  coordinatorContext: CoordinatorContext,
  workerId: string,
  task: Task
): WorkerContext {
  return {
    workerId,
    type: 'research',
    privateContext: {
      // Research Worker 获得广泛的文件访问权限
      files: coordinatorContext.global.projectStructure.allFiles,
      messages: [],
      toolCalls: [],
    },
    sharedContext: {
      inputFrom: [],
      outputTo: ['synthesis'],
    },
  };
}

function allocateImplementationContext(
  coordinatorContext: CoordinatorContext,
  workerId: string,
  task: Task
): WorkerContext {
  return {
    workerId,
    type: 'implementation',
    privateContext: {
      // Implementation Worker 只获得目标文件
      files: task.targetFiles || [],
      messages: [],
      toolCalls: [],
    },
    sharedContext: {
      inputFrom: ['synthesis'],
      outputTo: ['verification'],
    },
  };
}
```

### 3.4 Task Notification 中的上下文传递

```typescript
/**
 * Task Notification XML 中的上下文信息
 */
export interface TaskNotificationContext {
  // 任务元数据
  taskId: string;
  parentTaskId?: string;
  workerId: string;
  
  // 上下文摘要
  contextSummary: {
    // 相关文件列表
    relevantFiles: string[];
    // 关键决策点
    keyDecisions: string[];
    // 进度状态
    progressStatus: string;
  };
  
  // 继承的上下文标记
  inheritedContext: {
    files: boolean;
    env: boolean;
    gitStatus: boolean;
  };
}

/**
 * 构建 Task Notification XML
 */
export function buildTaskNotification(
  context: TaskNotificationContext
): string {
  return `<task-notification>
  <task-id>${context.taskId}</task-id>
  ${context.parentTaskId ? `<parent-task-id>${context.parentTaskId}</parent-task-id>` : ''}
  <worker-id>${context.workerId}</worker-id>
  <context-summary>
    <relevant-files>
      ${context.contextSummary.relevantFiles.map(f => `<file>${f}</file>`).join('\n      ')}
    </relevant-files>
    <key-decisions>
      ${context.contextSummary.keyDecisions.map(d => `<decision>${d}</decision>`).join('\n      ')}
    </key-decisions>
    <progress-status>${context.contextSummary.progressStatus}</progress-status>
  </context-summary>
  <inherited-context files="${context.inheritedContext.files}" env="${context.inheritedContext.env}" git-status="${context.inheritedContext.gitStatus}"/>
</task-notification>`;
}
```

---

## 四、System Prompt 与动态上下文

### 4.1 System Prompt 结构

```typescript
/**
 * System Prompt 的组成部分
 */
export interface SystemPrompt {
  // 核心身份定义
  identity: string;
  // 能力描述
  capabilities: string;
  // 工具定义
  tools: ToolDefinition[];
  // 工作流规则
  workflowRules: string;
  // 环境上下文
  environmentContext: EnvironmentContext;
  // 动态注入的上下文
  dynamicContext: DynamicContext;
}

// System Prompt 构建器
export function buildSystemPrompt(config: SystemPromptConfig): string {
  const sections: string[] = [];
  
  // 1. 身份定义
  sections.push(buildIdentitySection(config.agentType));
  
  // 2. 能力描述
  sections.push(buildCapabilitiesSection(config.capabilities));
  
  // 3. 工具定义
  sections.push(buildToolsSection(config.tools));
  
  // 4. 工作流规则
  sections.push(buildWorkflowRulesSection(config.workflow));
  
  // 5. 环境上下文
  sections.push(buildEnvironmentSection(config.environment));
  
  // 6. 动态上下文
  sections.push(buildDynamicContextSection(config.dynamicContext));
  
  return sections.join('\n\n');
}
```

### 4.2 动态上下文注入

```typescript
/**
 * 动态注入的环境信息
 */
export interface DynamicContext {
  // 当前工作目录
  cwd: string;
  // Git 状态
  gitStatus: GitStatus;
  // 最近修改的文件
  recentlyModifiedFiles: string[];
  // 项目结构摘要
  projectSummary: ProjectSummary;
  // 相关历史上下文
  relevantHistory: Message[];
}

// 环境上下文收集器
export class EnvironmentContextCollector {
  async collect(): Promise<DynamicContext> {
    return {
      cwd: process.cwd(),
      gitStatus: await this.collectGitStatus(),
      recentlyModifiedFiles: await this.collectRecentFiles(),
      projectSummary: await this.collectProjectSummary(),
      relevantHistory: await this.collectRelevantHistory(),
    };
  }
  
  private async collectGitStatus(): Promise<GitStatus> {
    // 收集 Git 分支、未提交更改等信息
    return {
      branch: await exec('git branch --show-current'),
      modified: await exec('git diff --name-only'),
      staged: await exec('git diff --staged --name-only'),
    };
  }
  
  private async collectRecentFiles(): Promise<string[]> {
    // 收集最近修改的文件
    const output = await exec('git diff --name-only HEAD~5..HEAD');
    return output.split('\n').filter(f => f.trim());
  }
  
  private async collectProjectSummary(): Promise<ProjectSummary> {
    // 收集项目结构摘要
    return {
      totalFiles: await this.countFiles(),
      mainLanguages: await this.detectLanguages(),
      entryPoints: await this.findEntryPoints(),
    };
  }
  
  private async collectRelevantHistory(): Promise<Message[]> {
    // 收集与当前任务相关的历史消息
    // 基于相似度或关键词匹配
    return [];
  }
}
```

### 4.3 Statusline 上下文

```typescript
/**
 * Statusline 提供的环境上下文
 * 类似于 Vim 的 statusline，显示当前环境状态
 */
export interface StatuslineContext {
  // 当前模式
  mode: 'default' | 'coordinator' | 'worker';
  // 当前阶段
  phase?: WorkflowPhase;
  // 活跃 Worker 数量
  activeWorkers: number;
  // 上下文使用率
  contextUsage: {
    tokens: number;
    maxTokens: number;
    percentage: number;
  };
  // 当前工具
  currentTool?: string;
  // 待处理任务
  pendingTasks: number;
}

// Statusline 构建器
export function buildStatusline(context: StatuslineContext): string {
  const parts: string[] = [];
  
  // 模式指示器
  parts.push(`[${context.mode.toUpperCase()}]`);
  
  // 阶段指示器
  if (context.phase) {
    parts.push(`{${context.phase}}`);
  }
  
  // Worker 数量
  if (context.activeWorkers > 0) {
    parts.push(`Workers: ${context.activeWorkers}`);
  }
  
  // 上下文使用率
  const usageColor = context.contextUsage.percentage > 90 ? '🔴' : 
                     context.contextUsage.percentage > 75 ? '🟡' : '🟢';
  parts.push(`${usageColor} ${context.contextUsage.percentage}%`);
  
  // 当前工具
  if (context.currentTool) {
    parts.push(`→ ${context.currentTool}`);
  }
  
  // 待处理任务
  if (context.pendingTasks > 0) {
    parts.push(`(${context.pendingTasks} pending)`);
  }
  
  return parts.join(' ');
}
```

### 4.4 Contextual Memory 整合

```typescript
/**
 * 上下文记忆管理
 * 整合短期上下文和长期记忆
 */
export interface ContextualMemory {
  // 短期上下文（当前会话）
  shortTerm: {
    messages: Message[];
    toolCalls: ToolCall[];
    files: Map<string, FileContent>;
  };
  
  // 长期记忆（跨会话）
  longTerm: {
    // 用户偏好
    userPreferences: UserPreferences;
    // 项目知识
    projectKnowledge: ProjectKnowledge;
    // 历史决策
    historicalDecisions: Decision[];
  };
  
  // 工作记忆（当前任务相关）
  workingMemory: {
    // 当前目标
    currentGoal: string;
    // 关键信息
    keyFacts: string[];
    // 待解决问题
    openQuestions: string[];
  };
}

/**
 * 记忆整合器
 * 将长期记忆注入当前上下文
 */
export class MemoryIntegrator {
  integrate(
    contextualMemory: ContextualMemory,
    currentContext: DynamicContext
  ): IntegratedContext {
    // 1. 提取与当前任务相关的长期记忆
    const relevantMemory = this.extractRelevantMemory(
      contextualMemory.longTerm,
      currentContext
    );
    
    // 2. 将记忆注入上下文
    return {
      ...currentContext,
      userPreferences: relevantMemory.userPreferences,
      relevantHistory: this.mergeHistory(
        contextualMemory.shortTerm.messages,
        relevantMemory.historicalDecisions
      ),
      projectKnowledge: relevantMemory.projectKnowledge,
    };
  }
  
  private extractRelevantMemory(
    longTerm: ContextualMemory['longTerm'],
    currentContext: DynamicContext
  ): Partial<ContextualMemory['longTerm']> {
    // 基于当前上下文的相关性提取记忆
    // 使用相似度计算或关键词匹配
    return {
      userPreferences: longTerm.userPreferences,
      projectKnowledge: this.filterProjectKnowledge(
        longTerm.projectKnowledge,
        currentContext
      ),
      historicalDecisions: this.filterDecisions(
        longTerm.historicalDecisions,
        currentContext
      ),
    };
  }
}
```

---

## 五、关键洞察与最佳实践

### 5.1 Token 优化策略

1. **优先级分层**: 关键消息始终保留，低优先级消息摘要或丢弃
2. **智能截断**: 保留消息头部和尾部，中间部分摘要
3. **工具输出限制**: 大输出自动截断，保留关键信息
4. **文件分页**: 大文件分块读取，按需加载

### 5.2 多 Agent 上下文隔离原则

1. **最小权限**: Worker 只获得完成任务所需的最小上下文
2. **显式传递**: 上下文传递必须显式声明，避免隐式泄漏
3. **不可变性**: 继承的上下文只读，Worker 修改不影响父 Agent
4. **结果聚合**: 通过 Task Notification 聚合结果，而非共享状态

### 5.3 动态上下文收集

1. **延迟收集**: 只在需要时收集环境信息
2. **增量更新**: 环境变化时增量更新，避免全量重建
3. **相关性过滤**: 只保留与当前任务相关的历史上下文
4. **缓存策略**: 频繁访问的上下文缓存，减少重复计算

---

## 六、实现建议

### 6.1 上下文管理器架构

```typescript
export class ContextManager {
  private tokenBudget: TokenBudget;
  private messageHistory: MessageHistory;
  private fileCache: FileContentCache;
  private memoryIntegrator: MemoryIntegrator;
  
  constructor(config: ContextManagerConfig) {
    this.tokenBudget = new TokenBudget(config.maxTokens);
    this.messageHistory = new MessageHistory(config.retentionPolicy);
    this.fileCache = new FileContentCache(config.cacheSizeMB);
    this.memoryIntegrator = new MemoryIntegrator();
  }
  
  // 添加上下文
  addMessage(message: Message): void {
    this.messageHistory.add(message);
    this.enforceTokenBudget();
  }
  
  // 获取当前上下文
  getContext(): Context {
    return {
      messages: this.messageHistory.getMessages(),
      files: this.fileCache.getAll(),
      usage: this.tokenBudget.getUsage(),
    };
  }
  
  // 强制执行 Token 预算
  private enforceTokenBudget(): void {
    while (this.tokenBudget.isOverBudget()) {
      const lowestPriority = this.messageHistory.findLowestPriority();
      if (lowestPriority) {
        this.messageHistory.summarize(lowestPriority);
      } else {
        break;
      }
    }
  }
}
```

### 6.2 监控与调试

```typescript
export interface ContextMetrics {
  totalTokens: number;
  messageCount: number;
  fileCount: number;
  cacheHitRate: number;
  truncationEvents: number;
}

export class ContextMonitor {
  private metrics: ContextMetrics = {
    totalTokens: 0,
    messageCount: 0,
    fileCount: 0,
    cacheHitRate: 0,
    truncationEvents: 0,
  };
  
  recordTruncation(): void {
    this.metrics.truncationEvents++;
    console.warn(`Context truncated! Total events: ${this.metrics.truncationEvents}`);
  }
  
  getMetrics(): ContextMetrics {
    return { ...this.metrics };
  }
}
```

---

## 七、总结

Claude Code 的上下文管理机制是一个多层次的复杂系统：

1. **Token 层**: 严格的预算控制和智能截断
2. **消息层**: 优先级分层的消息保留策略
3. **文件层**: 分页读取和缓存机制
4. **Agent 层**: 显式的上下文隔离和传递
5. **系统层**: 动态注入的环境信息

这种设计确保了在有限的上下文窗口内，Agent 能够高效地获取所需信息，同时避免信息过载和上下文污染。
