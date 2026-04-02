# Claude Code 上下文管理融入 OpenClaw 短期记忆插件 - 最终方案

## 📋 执行摘要

基于 Subagent 并行研究成果，本方案整合 Claude Code 的上下文管理机制与 OpenClaw 的 memory-lancedb-pro 插件。

---

## 🔍 研究成果（来自 Subagent）

### Subagent 1: Researcher - Claude Code 上下文机制

**Token 预算分配：**
| 分配项 | 比例 | 用途 |
|--------|------|------|
| System Prompt | 15% | 身份定义、能力描述 |
| Tool Definitions | 10% | 工具定义 |
| Message History | 60% | 消息历史（主体） |
| Reserve | 15% | 预留空间 |

**消息优先级分层：**
| 优先级 | 级别 | 消息类型 | 处理策略 |
|--------|------|----------|----------|
| CRITICAL | 1 | 系统消息、错误消息 | 始终保留 |
| HIGH | 2 | 用户指令、工具调用 | 高优先保留 |
| MEDIUM | 3 | 工具输出、Agent 响应 | 可转摘要 |
| LOW | 4 | 元数据、状态信息 | 可丢弃 |
| EPHEMERAL | 5 | 临时信息 | 优先丢弃 |

**上下文截断触发条件：**
- WARNING: 75% 使用率 → 开始监控
- CRITICAL: 90% 使用率 → 强制执行摘要
- TRUNCATION: 95% 使用率 → 触发强制截断

**Fork vs Continue 决策（5场景）：**
- Continue: Worker 有精确文件、修正近期工作、有错误上下文
- Spawn: 研究广但实现窄、验证他人代码、首次尝试错误

### Subagent 2: Analyst - OpenClaw 记忆系统架构

**memory-lancedb-pro 配置：**
- 向量数据库: LanceDB
- 嵌入模型: 阿里云 text-embedding-v2 (1536维)
- 功能: autoCapture（自动捕获）、autoRecall（自动召回）
- 存储路径: ~/.openclaw/memory/lancedb-pro

**autoCapture 工作流程：**
1. 在 `agent_end` 事件触发
2. 通过 MEMORY_TRIGGERS 正则匹配判断是否值得记忆
3. 自动分类: preference、fact、decision、entity、other
4. 生成向量嵌入
5. 去重检查（相似度 > 0.95 则跳过）
6. 存入 LanceDB

**autoRecall 工作流程：**
1. 在 `before_agent_start` 触发
2. 混合检索（vector 70% + BM25 30%）
3. RRF融合 → Rerank重排 → MemQ质量评分
4. 过滤低质量结果（qualityScore < 0.4）
5. 注入 `<relevant-memories>` 上下文

**与 lossless-claw 的关系：**
- memory-lancedb-pro: 跨会话长期记忆（持久化）
- lossless-claw: 会话内上下文管理（DAG摘要层级）

---

## 🏗️ 融合架构设计

```
┌─────────────────────────────────────────────────────────────┐
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
│-pro (长期)   │ │claw (短期)│ │(Fork/Continue)│
└──────────────┘ └──────────┘ └──────────────┘
```

---

## 🔧 核心模块实现

### 模块 1: TokenBudget

```typescript
export interface TokenBudget {
  total: number;      // 200K for Claude models
  system: number;     // 15% = 30K
  tools: number;      // 10% = 20K
  messages: number;   // 60% = 120K
  reserve: number;    // 15% = 30K
}

export class ContextBudget {
  private budget: TokenBudget;
  private used: Map<string, number> = new Map();

  constructor(totalTokens: number = 200000) {
    this.budget = {
      total: totalTokens,
      system: Math.floor(totalTokens * 0.15),
      tools: Math.floor(totalTokens * 0.10),
      messages: Math.floor(totalTokens * 0.60),
      reserve: Math.floor(totalTokens * 0.15),
    };
  }

  allocate(category: keyof TokenBudget, tokens: number): boolean {
    const current = this.used.get(category) || 0;
    const limit = this.budget[category];
    
    if (current + tokens > limit) {
      // 尝试使用 reserve
      if (category !== 'reserve') {
        const reserveAvailable = this.budget.reserve - (this.used.get('reserve') || 0);
        const overflow = current + tokens - limit;
        if (overflow <= reserveAvailable) {
          this.used.set('reserve', (this.used.get('reserve') || 0) + overflow);
          this.used.set(category, limit);
          return true;
        }
      }
      return false;
    }
    
    this.used.set(category, current + tokens);
    return true;
  }

  getUsageRate(): number {
    const totalUsed = Array.from(this.used.values()).reduce((a, b) => a + b, 0);
    return totalUsed / this.budget.total;
  }

  getThresholdStatus(): 'normal' | 'warning' | 'critical' | 'truncation' {
    const rate = this.getUsageRate();
    if (rate >= 0.95) return 'truncation';
    if (rate >= 0.90) return 'critical';
    if (rate >= 0.75) return 'warning';
    return 'normal';
  }
}
```

### 模块 2: PriorityQueue

```typescript
export enum MessagePriority {
  CRITICAL = 1,    // 系统消息、错误
  HIGH = 2,        // 用户指令、工具调用
  MEDIUM = 3,      // 工具输出、Agent 响应
  LOW = 4,         // 元数据、状态
  EPHEMERAL = 5,   // 临时信息
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

  add(message: PrioritizedMessage): void {
    this.messages.push(message);
    this.sortByPriority();
  }

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

      if (currentTokens + msg.tokens <= budget * 0.95) {
        preserved.push(msg);
        currentTokens += msg.tokens;
      } else if (msg.priority === MessagePriority.MEDIUM) {
        summarized.push(msg);
      } else {
        dropped.push(msg);
      }
    }

    return { preserved, summarized, dropped };
  }

  private sortByPriority(): void {
    this.messages.sort((a, b) => {
      if (a.priority !== b.priority) {
        return a.priority - b.priority;
      }
      return b.timestamp - a.timestamp;
    });
  }
}
```

### 模块 3: ContextCompressor

```typescript
export class ContextCompressor {
  async compress(
    messages: PrioritizedMessage[],
    targetTokens: number
  ): Promise<CompressionResult> {
    const originalTokens = messages.reduce((sum, m) => sum + m.tokens, 0);

    // 策略 1: 摘要 MEDIUM 优先级消息
    if (originalTokens <= targetTokens * 1.5) {
      return await this.summarizeMessages(messages, targetTokens);
    }

    // 策略 2: 截断旧消息
    if (originalTokens <= targetTokens * 2) {
      return this.truncateOldMessages(messages, targetTokens);
    }

    // 策略 3: 驱逐低优先级
    return this.evictLowPriority(messages, targetTokens);
  }

  private async summarizeMessages(
    messages: PrioritizedMessage[],
    targetTokens: number
  ): Promise<CompressionResult> {
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
      originalTokens,
      compressedTokens: compressed.reduce((sum, m) => sum + m.tokens, 0),
      strategy: 'summary',
    };
  }

  private async generateSummary(messages: PrioritizedMessage[]): Promise<string> {
    // 使用配置的 summaryModel 生成摘要
    const content = messages.map(m => m.content).join('\n');
    return `[摘要] ${content.slice(0, 500)}...`;
  }
}
```

### 模块 4: SubagentContext

```typescript
export interface SubagentContextConfig {
  inheritFiles: boolean;
  inheritEnv: boolean;
  inheritGitStatus: boolean;
  messageHistoryCount: number; // Fork=0, Continue=10
}

export class SubagentContextManager {
  createForkContext(parentSessionId: string, task: string): SubagentContext {
    return {
      id: `fork