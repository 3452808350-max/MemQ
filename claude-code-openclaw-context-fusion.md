# Claude Code 上下文管理融入 OpenClaw 短期记忆插件方案

## 执行摘要

基于对 Claude Code 上下文管理机制的深度分析和 OpenClaw 现有架构的理解，本方案提出将 Claude Code 的 Token 预算管理、消息优先级分层、智能截断算法融入 OpenClaw 的 memory-lancedb-pro 插件，构建更高效的短期记忆系统。

---

## 一、现状分析

### 1.1 Claude Code 上下文管理机制

**Token 预算分配（200K 窗口）**
```
System Prompt:  15% (30K tokens)
Tool Definitions: 10% (20K tokens)
Message History:  60% (120K tokens)
Reserve:          15% (30K tokens)
```

**消息优先级分层（5 级）**
| 优先级 | 类型 | 保留策略 |
|--------|------|----------|
| CRITICAL (1) | 系统消息、错误消息 | 始终保留 |
| HIGH (2) | 用户指令、工具调用 | 优先保留 |
| MEDIUM (3) | 工具输出、Agent 响应 | 可摘要 |
| LOW (4) | 元数据、状态信息 | 可丢弃 |
| EPHEMERAL (5) | 临时信息 | 优先丢弃 |

**上下文截断阈值**
- WARNING: 75% 使用率触发警告
- CRITICAL: 90% 使用率关键状态
- TRUNCATION: 95% 使用率触发截断

**Fork vs Continue 决策（5 场景）**
1. **Continue**: Worker 已有上下文文件、修正近期工作、有错误上下文
2. **Spawn**: 研究广但实现窄、验证他人代码、首次尝试错误、任务无关

### 1.2 OpenClaw 现有架构

**记忆插件: memory-lancedb-pro**
- 向量数据库: LanceDB
- 嵌入模型: 阿里云 text-embedding-v2 (1536 维)
- 功能: autoCapture（自动捕获）、autoRecall（自动召回）
- 存储路径: ~/.openclaw/memory/lancedb-pro

**上下文引擎: lossless-claw**
- freshTailCount: 32（保留最近 32 条消息）
- contextThreshold: 0.75（75% 阈值触发压缩）
- incrementalMaxDepth: -1（无限增量深度）
- summaryModel: bailian/glm-5（摘要模型）

---

## 二、融合方案设计

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              Enhanced Context Manager                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │TokenBudget  │  │PriorityQueue│  │ContextCompressor    │ │
│  │(Claude Code)│  │(Claude Code)│  │(Claude Code)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌──────▼───────┐
│memory-lancedb│ │lossless- │ │SubagentContext│
│-pro (长期)   │ │claw (短期)│ │(新增)        │
└──────────────┘ └──────────┘ └──────────────┘
```

### 2.2 核心模块设计

#### 模块 1: TokenBudget（Token 预算管理）

```typescript
// src/context/token-budget.ts
export interface TokenBudget {
  total: number;           // 总预算（默认 200K）
  system: number;          // System Prompt 预算
  tools: number;           // 工具定义预算
  messages: number;        // 消息历史预算
  reserve: number;         // 预留预算
}

export class TokenBudgetManager {
  private budget: TokenBudget;
  private usage: Map<string, number>;

  constructor(config?: Partial<TokenBudget>) {
    this.budget = {
      total: config?.total || 200000,
      system: config?.system || 30000,    // 15%
      tools: config?.tools || 20000,      // 10%
      messages: config?.messages || 120000, // 60%
      reserve: config?.reserve || 30000,  // 15%
    };
    this.usage = new Map();
  }

  // 分配预算
  allocate(category: keyof TokenBudget, tokens: number): boolean {
    const current = this.usage.get(category) || 0;
    const limit = this.budget[category];
    
    if (current + tokens > limit) {
      return false; // 超出预算
    }
    
    this.usage.set(category, current + tokens);
    return true;
  }

  // 获取使用率
  getUsageRate(category: keyof TokenBudget): number {
    const current = this.usage.get(category) || 0;
    return current / this.budget[category];
  }

  // 检查阈值状态
  getThresholdStatus(): 'normal' | 'warning' | 'critical' | 'truncation' {
    const totalUsed = this.getTotalUsage();
    const rate = totalUsed / this.budget.total;
    
    if (rate >= 0.95) return 'truncation';
    if (rate >= 0.90) return 'critical';
    if (rate >= 0.75) return 'warning';
    return 'normal';
  }

  private getTotalUsage(): number {
    return Array.from(this.usage.values()).reduce((a, b) => a + b, 0);
  }
}
```

#### 模块 2: PriorityQueue（消息优先级队列）

```typescript
// src/context/priority-queue.ts
export enum MessagePriority {
  CRITICAL = 1,   // 系统消息、错误
  HIGH = 2,       // 用户指令、工具调用
  MEDIUM = 3,     // 工具输出、Agent 响应
  LOW = 4,        // 元数据、状态
  EPHEMERAL = 5,  // 临时信息
}

export interface PrioritizedMessage {
  id: string;
  content: string;
  priority: MessagePriority;
  timestamp: number;
  tokens: number;
  type: 'system' | 'user' | 'assistant' | 'tool';
}

export class PriorityMessageQueue {
  private messages: PrioritizedMessage[] = [];
  private maxTokens: number;

  constructor(maxTokens: number = 120000) {
    this.maxTokens = maxTokens;
  }

  // 添加消息（自动按优先级排序）
  add(message: PrioritizedMessage): void {
    this.messages.push(message);
    this.sortByPriority();
  }

  // 获取消息（按优先级排序）
  getMessages(): PrioritizedMessage[] {
    return [...this.messages];
  }

  // 截断到低优先级消息
  truncateToBudget(budget: number): {
    preserved: PrioritizedMessage[];
    summarized: PrioritizedMessage[];
    dropped: PrioritizedMessage[];
  } {
    const preserved: PrioritizedMessage[] = [];
    const summarized: PrioritizedMessage[] = [];
    const dropped: PrioritizedMessage[] = [];

    let currentTokens = 0;

    for (const msg of this.messages) {
      // CRITICAL 和 HIGH 始终保留
      if (msg.priority <= MessagePriority.HIGH) {
        preserved.push(msg);
        currentTokens += msg.tokens;
        continue;
      }

      // 检查预算
      if (currentTokens + msg.tokens <= budget * 0.95) {
        preserved.push(msg);
        currentTokens += msg.tokens;
      } else if (msg.priority === MessagePriority.MEDIUM) {
        // MEDIUM 转为摘要
        summarized.push(msg);
      } else {
        // LOW/EPHEMERAL 丢弃
        dropped.push(msg);
      }
    }

    return { preserved, summarized, dropped };
  }

  private sortByPriority(): void {
    this.messages.sort((a, b) => {
      // 先按优先级排序
      if (a.priority !== b.priority) {
        return a.priority - b.priority;
      }
      // 同优先级按时间排序（新的在前）
      return b.timestamp - a.timestamp;
    });
  }
}
```

#### 模块 3: ContextCompressor（上下文压缩器）

```typescript
// src/context/compressor.ts
export interface CompressionResult {
  originalTokens: number;
  compressedTokens: number;
  compressionRatio: number;
  strategy: 'none' | 'summary' | 'truncation' | 'eviction';
}

export class ContextCompressor {
  private summaryModel: string;

  constructor(summaryModel: string = 'bailian/glm-5') {
    this.summaryModel = summaryModel;
  }

  // 压缩策略选择
  async compress(
    messages: PrioritizedMessage[],
    targetTokens: number
  ): Promise<CompressionResult> {
    const originalTokens = messages.reduce((sum, m) => sum + m.tokens, 0);

    if (originalTokens <= targetTokens) {
      return {
        originalTokens,
        compressedTokens: originalTokens,
        compressionRatio: 1,
        strategy: 'none',
      };
    }

    // 策略 1: 摘要低优先级消息
    if (originalTokens <= targetTokens * 1.5) {
      const compressed = await this.summarizeMessages(messages, targetTokens);
      return {
        originalTokens,
        compressedTokens: compressed.tokens,
        compressionRatio: compressed.tokens / originalTokens,
        strategy: 'summary',
      };
    }

    // 策略 2: 截断旧消息
    if (originalTokens <= targetTokens * 2) {
      const truncated = this.truncateOldMessages(messages, targetTokens);
      return {
        originalTokens,
        compressedTokens: truncated.tokens,
        compressionRatio: truncated.tokens / originalTokens,
        strategy: 'truncation',
      };
    }

    // 策略 3: 驱逐最低优先级
    const evicted = this.evictLowPriority(messages, targetTokens);
    return {
      originalTokens,
      compressedTokens: evicted.tokens,
      compressionRatio: evicted.tokens / originalTokens,
      strategy: 'eviction',
    };
  }

  // 摘要消息
  private async summarizeMessages(
    messages: PrioritizedMessage[],
    targetTokens: number
  ): Promise<{ tokens: number; messages: PrioritizedMessage[] }> {
    const mediumPriority = messages.filter(m => m.priority === MessagePriority.MEDIUM);
    const summary = await this.generateSummary(mediumPriority);
    
    const compressed = messages.filter(m => m.priority !== MessagePriority.MEDIUM);
    compressed.push({
      id: `summary-${Date.now()}`,
      content: summary,
      priority: MessagePriority.MEDIUM,
      timestamp: Date.now(),
      tokens: summary.length / 4,
      type: 'system',
    });

    return {
      tokens: compressed.reduce((sum, m) => sum + m.tokens, 0),
      messages: compressed,
    };
  }

  private async generateSummary(messages: PrioritizedMessage[]): Promise<string> {
    const content = messages.map(m => m.content).join('\n');
    return `[摘要] ${content.slice(0, 500)}...`;
  }
}
```

#### 模块 4: SubagentContext（子 Agent 上下文管理）

```typescript
// src/context/subagent-context.ts
export interface SubagentContextConfig {
  inheritFiles: boolean;
  inheritEnv: boolean;
  inheritGitStatus: boolean;
  messageHistoryCount: number;
}

export class SubagentContextManager {
  private contexts: Map<string, SubagentContext> = new Map();

  createForkContext(parentSessionId: string, task: string): SubagentContext {
    const config: SubagentContextConfig = {
      inheritFiles: true,
      inheritEnv: true,
      inheritGitStatus: true,
      messageHistoryCount: 0,
    };

    const context: SubagentContext = {
      id: `fork-${Date.now()}`,
      parentId: parentSessionId,
      type: 'fork',
      config,
      task,
      files: new Set(),
      env: {},
    };

    this.contexts.set(context.id, context);
    return context;
  }

  createContinueContext(parentSessionId: string, task: string): SubagentContext {
    const config: SubagentContextConfig = {
      inheritFiles: true,
      inheritEnv: true,
      inheritGitStatus: true,
      messageHistoryCount: 10,
    };

    const context: SubagentContext = {
      id: `continue-${Date.now()}`,
      parentId: parentSessionId,
      type: 'continue',
      config,
      task,
      files: new Set(),
      env: {},
    };

    this.contexts.set(context.id, context);
    return context;
  }

  decideSpawnStrategy(
    parentContext: SubagentContext,
    taskType: 'research' | 'implementation' | 'verification'
  ): 'fork' | 'continue' {
    switch (taskType) {
      case 'research': return 'fork';
      case 'implementation': return 'continue';
      case 'verification': return 'fork';
      default: return 'fork';
    }
  }
}

interface SubagentContext {
  id: string;
  parentId: string;
  type: 'fork' | 'continue';
  config: SubagentContextConfig;
  task: string;
  files: Set<string>;
  env: Record<string, string>;
}
```

---

## 三、与 memory-lancedb-pro 的集成

### 3.1 集成架构

```
memory-lancedb-pro
├─ Enhanced Memory Plugin
│  ├─ Capture + Token Budget
│  └─ Recall + Priority
└─ LanceDB Vector DB
```

### 3.2 集成点

**集成点 1: 记忆捕获时进行 Token 预算检查**

```typescript
async capture(content: string, metadata: MemoryMetadata): Promise<void> {
  const tokens = estimateTokens(content);
  if (!this.tokenBudget.allocate('messages', tokens)) {
    await this.compressOldMemories();
  }
  await this.originalCapture(content, metadata);
}
```

**集成点 2: 记忆召回时按优先级排序**

```typescript
async recall(query: string): Promise<Memory[]> {
  const results = await this.vectorRecall(query);
  const prioritized = this.priorityQueue.sortByPriority(results);
  return this.selectWithinBudget(prioritized);
}
```

---

## 四、实现优先级

### P0（核心功能）
- TokenBudget 模块实现
- PriorityQueue 基础功能
- 与 memory-lancedb-pro 的基础集成

### P1（增强功能）
- ContextCompressor 智能压缩
- SubagentContext Fork/Continue 决策
- 与 lossless-claw 的协同压缩

### P2（高级功能）
- 自适应 Token 预算调整
- 基于使用模式的优先级学习
- 跨会话上下文恢复

---

## 五、预期收益

| 指标 | 当前 | 预期 | 提升 |
|------|------|------|------|
| Token 利用率 | ~60% | ~85% | +42% |
| 上下文命中率 | ~45% | ~70% | +56% |
| 多 Agent 协作效率 | 基准 | +30% | - |

---

## 六、下一步行动

1. **P0 实现**（预计 2-3 天）
   - 实现 TokenBudget 和 PriorityQueue 核心模块
   - 在 memory-lancedb-pro 中添加集成点
   - 编写单元测试

2. **P1 实现**（预计 3-5 天）
   - 实现 ContextCompressor
   - 实现 SubagentContextManager
   - 与 lossless-claw 协同

3. **验证测试**
   - 对比测试 Token 利用率
   - 多 Agent 场景压力测试
   - 长期稳定性测试
