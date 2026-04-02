# Memory-LanceDB-Pro 插件架构分析
## Context Manager P2 集成准备报告

**分析日期**: 2026-04-02  
**插件路径**: `~/.openclaw/plugins/memory-lancedb-pro/`  
**目标**: 为 Context Manager P2 的集成确定关键集成点

---

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Memory-LanceDB-Pro Plugin                        │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Tools     │  │  Retriever  │  │    Store    │  │  ScopeManager   │ │
│  │  (tools.ts) │  │(retriever.ts│  │ (store.ts)  │  │  (scopes.ts)    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘ │
│         │                │                │                  │          │
│         ▼                ▼                ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    Plugin API (index.ts)                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  ││
│  │  │ Auto-Recall │  │ Auto-Capture│  │      Session Memory Hook    │  ││
│  │  │  (before)   │  │   (after)   │  │       (command:new)         │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                          │                                              │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                     LanceDB Storage Layer                            ││
│  │  - Vector Search (cosine similarity)                                 ││
│  │  - BM25 Full-Text Search (FTS index)                                 ││
│  │  - Hybrid Retrieval (RRF fusion)                                     ││
│  │  - Multi-scope isolation via scope column                            ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心组件分析

### 2.1 Store Layer (`src/store.ts`)

**核心职责**: 向量存储与检索的底层实现

| 组件 | 说明 |
|------|------|
| `MemoryStore` | 主存储类，封装 LanceDB 操作 |
| `MemoryEntry` | 内存条目结构：id, text, vector, category, scope, importance, timestamp, metadata |
| `vectorSearch()` | 向量相似度搜索，支持 scope 过滤 |
| `bm25Search()` | 全文检索，基于 FTS 索引 |
| `store()/importEntry()` | 存储新条目（后者保留 id/timestamp，用于迁移） |

**关键数据结构**:
```typescript
interface MemoryEntry {
  id: string;
  text: string;
  vector: number[];
  category: "preference" | "fact" | "decision" | "entity" | "other";
  scope: string;           // 作用域隔离关键字段
  importance: number;      // 0-1，用于检索排序加权
  timestamp: number;       // 用于时效性加权
  metadata?: string;       // JSON 扩展字段
}
```

**存储层扩展点**:
- `metadata` 字段可存储任意 JSON 数据，适合存储 TaskNotification 关联信息
- `importEntry()` 方法支持保留原有 ID，适合跨 Agent 数据同步

---

### 2.2 Retriever Layer (`src/retriever.ts`)

**核心职责**: 混合检索与结果重排序

**检索流程**:
```
Query → Embed → Vector Search ─┬─► RRF Fusion ──► Rerank ──► Recency Boost
                               │                    │
            BM25 Search ───────┘                    ├──► Importance Weight
                                                    ├──► Length Normalization
                                                    └──► Time Decay
```

**关键配置** (`RetrievalConfig`):
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `mode` | "hybrid" | vector / hybrid |
| `vectorWeight` | 0.7 | 向量搜索权重 |
| `bm25Weight` | 0.3 | BM25 权重 |
| `rerank` | "cross-encoder" | 重排序策略 |
| `recencyHalfLifeDays` | 14 | 时效性半衰期 |
| `recencyWeight` | 0.10 | 时效性加权系数 |
| `timeDecayHalfLifeDays` | 60 | 时间衰减半衰期 |

**检索层扩展点**:
- `retrieve()` 方法接受 `scopeFilter` 参数，可用于 Agent 隔离
- `RetrievalResult` 包含 `sources` 字段，记录检索来源（vector/BM25/reranked）
- 质量评分集成点：`qualityScore()` 已在 `index.ts` 的 recall hook 中使用

---

### 2.3 Scope Manager (`src/scopes.ts`)

**核心职责**: 多作用域访问控制与 Agent 隔离

**作用域模式**:
```typescript
const SCOPE_PATTERNS = {
  GLOBAL: "global",
  AGENT: (agentId: string) => `agent:${agentId}`,
  CUSTOM: (name: string) => `custom:${name}`,
  PROJECT: (projectId: string) => `project:${projectId}`,
  USER: (userId: string) => `user:${userId}`,
};
```

**核心方法**:
| 方法 | 说明 |
|------|------|
| `getAccessibleScopes(agentId)` | 获取 Agent 可访问的作用域列表 |
| `getDefaultScope(agentId)` | 获取 Agent 默认作用域 |
| `isAccessible(scope, agentId)` | 检查 Agent 是否有权访问某作用域 |
| `setAgentAccess(agentId, scopes)` | 设置 Agent 的作用域权限 |

**默认配置**:
- 所有 Agent 默认可访问 `global` 作用域
- 每个 Agent 自动拥有自己的 `agent:{id}` 私有作用域
- 可通过 `agentAccess` 配置自定义权限

**作用域层扩展点**:
- `addScopeDefinition()` 可动态添加新作用域类型
- `filterScopesForAgent()` 工具函数可用于检索前过滤

---

### 2.4 Tools Layer (`src/tools.ts`)

**核心职责**: 向 Agent 暴露记忆管理工具

**核心工具**:
| 工具 | 功能 |
|------|------|
| `memory_recall` | 检索记忆（支持 query/limit/scope/category） |
| `memory_store` | 存储新记忆（自动去重、噪音过滤） |
| `memory_forget` | 删除记忆（支持 ID 或搜索） |
| `memory_update` | 更新记忆（保留 timestamp） |
| `memory_stats` | 统计信息（可选） |
| `memory_list` | 列出记忆（可选） |

**工具上下文**:
```typescript
interface ToolContext {
  retriever: MemoryRetriever;
  store: MemoryStore;
  scopeManager: MemoryScopeManager;
  embedder: Embedder;
  agentId?: string;  // 运行时确定
}
```

**工具层扩展点**:
- 所有工具都通过 `scopeManager.getAccessibleScopes(agentId)` 获取权限
- `memory_store` 支持噪音过滤 (`isNoise()`)
- `memory_recall` 支持按 category 过滤

---

### 2.5 Plugin Entry Point (`index.ts`)

**生命周期 Hooks**:

| Hook | 时机 | 功能 |
|------|------|------|
| `gateway_start` | Gateway 启动 | 启动 MemQ 服务 |
| `before_agent_start` | Agent 执行前 | Auto-Recall: 注入相关记忆到上下文 |
| `agent_end` | Agent 执行后 | Auto-Capture: 自动捕获重要信息 |
| `command:new` | /new 命令 | Session Memory: 保存会话摘要 |

**Auto-Recall 流程** (`before_agent_start`):
```typescript
1. 检查 prompt 是否需要检索 (shouldSkipRetrieval)
2. 获取 Agent 可访问作用域
3. 执行混合检索 (limit: 5)
4. 应用 MemQ 质量评分 (如果服务可用)
5. 过滤低质量结果 (qualityScore < 0.4)
6. 格式化并注入上下文 (limit: 3)
```

**质量评分集成** (`quality-client.ts`):
```typescript
const qualityResult = await qualityScore(text, category);
const finalScore = retrievalScore * (0.5 + 0.5 * qualityScore);
```

---

## 3. 集成点分析

### 3.1 存储层集成：TaskNotification

**目标**: 在存储层集成任务通知系统，实现跨 Agent 任务状态同步

**集成方案**:

#### 方案 A: 扩展 MemoryEntry.metadata
```typescript
// 新增 TaskNotification 类型
interface TaskNotification {
  taskId: string;
  sourceAgent: string;
  targetAgents: string[];
  status: "pending" | "completed" | "cancelled";
  priority: "low" | "normal" | "high";
  createdAt: number;
  expiresAt?: number;
}

// 存储时使用 metadata 字段
await store.store({
  text: taskDescription,
  vector: await embedder.embedPassage(taskDescription),
  category: "decision",
  scope: `task:${taskId}`,
  importance: 0.9,
  metadata: JSON.stringify({
    type: "task_notification",
    notification: taskNotification as TaskNotification,
  }),
});
```

**优点**:
- 利用现有 `metadata` 字段，无需修改数据库结构
- 通过 `scope: "task:${taskId}"` 实现任务隔离
- 可使用 `importEntry()` 保留原始 taskId

**检索过滤**:
```typescript
// 检索特定 Agent 的待处理任务
const results = await retriever.retrieve({
  query: agentId,
  limit: 10,
  scopeFilter: [`agent:${agentId}`, `task:*`],  // 需实现通配符支持
  category: "decision",
});

// 过滤出 TaskNotification 类型
const tasks = results.filter(r => {
  const meta = JSON.parse(r.entry.metadata || "{}");
  return meta.type === "task_notification" &&
         meta.notification.targetAgents.includes(agentId) &&
         meta.notification.status === "pending";
});
```

#### 方案 B: 独立 TaskStore 类
```typescript
// 新建 src/task-store.ts
export class TaskStore {
  constructor(private memoryStore: MemoryStore) {}
  
  async createTask(task: TaskNotification): Promise<string> {
    return (await this.memoryStore.store({
      // ...同上
    })).id;
  }
  
  async getPendingTasks(agentId: string): Promise<TaskNotification[]> {
    // 封装检索逻辑
  }
  
  async updateTaskStatus(taskId: string, status: TaskNotification["status"]): Promise<void> {
    // 使用 memoryStore.update()
  }
}
```

**推荐**: 方案 A（轻量级，利用现有结构）

---

### 3.2 检索层集成：上下文注入

**目标**: 在检索层实现智能上下文注入，支持多 Agent 场景

**当前实现** (`index.ts` `before_agent_start`):
```typescript
const results = await retriever.retrieve({
  query: event.prompt,
  limit: 5,
  scopeFilter: accessibleScopes,
});

// 质量过滤
const filteredResults = scoredResults
  .filter(r => qualityScore >= 0.4)
  .slice(0, 3);

// 格式化注入
const memoryContext = filteredResults
  .map(r => `- [${r.entry.category}:${r.entry.scope}] ${text} (${score}%)`)
  .join("\n");

return {
  prependContext: `<relevant-memories>\n${memoryContext}\n</relevant-memories>`,
};
```

**Context Manager P2 扩展点**:

#### 扩展 1: 多源上下文融合
```typescript
interface ContextSource {
  type: "memory" | "session" | "task" | "file";
  results: RetrievalResult[];
  weight: number;  // 融合权重
}

async function fuseContextSources(sources: ContextSource[]): Promise<string> {
  // RRF-style fusion across sources
  // 类似 retriever.ts 的 fuseResults()，但跨数据源
}
```

#### 扩展 2: 动态上下文长度控制
```typescript
interface ContextConfig {
  maxTokens: number;
  priorityOrder: ("task" | "memory" | "session")[];
  minScorePerSource: Record<string, number>;
}

// 根据 token 预算动态调整各源检索数量
function allocateTokenBudget(config: ContextConfig, sources: ContextSource[]) {
  // 按优先级分配 token 配额
}
```

#### 扩展 3: Agent 感知上下文
```typescript
interface AgentContext {
  agentId: string;
  role: string;
  capabilities: string[];
  activeTask?: string;
}

// 根据 Agent 角色过滤/加权上下文
function filterContextForAgent(
  results: RetrievalResult[],
  agentContext: AgentContext
): RetrievalResult[] {
  // 例如：coder Agent 优先获取 technical 记忆
  // analyst Agent 优先获取 decision 记忆
}
```

---

### 3.3 作用域层集成：Agent 隔离

**目标**: 实现多 Agent 场景下的记忆隔离与共享

**当前作用域模型**:
```
┌─────────────────────────────────────────────────────────────┐
│                      Scope Hierarchy                         │
├─────────────────────────────────────────────────────────────┤
│  global (所有 Agent 可访问)                                   │
│  ├── agent:main (主 Agent 私有)                              │
│  ├── agent:researcher (研究 Agent 私有)                       │
│  ├── agent:coder (编码 Agent 私有)                           │
│  ├── project:claude-plugin (项目共享)                        │
│  └── user:kyj (用户级共享)                                   │
└─────────────────────────────────────────────────────────────┘
```

**集成方案**:

#### 方案 1: 基于角色的作用域配置
```typescript
// 在 plugin config 中定义
const scopeConfig = {
  default: "global",
  definitions: {
    global: { description: "共享知识" },
    "agent:main": { description: "主 Agent 私有" },
    "agent:researcher": { description: "研究 Agent 私有" },
    "project:*": { description: "项目共享作用域" },
  },
  agentAccess: {
    "main": ["global", "agent:main", "project:*"],
    "researcher": ["global", "agent:researcher", "project:*"],
    "coder": ["global", "agent:coder", "project:*"],
  },
};
```

#### 方案 2: 动态作用域继承
```typescript
// 扩展 ScopeManager
class ExtendedScopeManager extends MemoryScopeManager {
  // 支持作用域继承（如 project:* 自动包含 global）
  getAccessibleScopes(agentId: string, includeInherited = true): string[] {
    const scopes = super.getAccessibleScopes(agentId);
    if (!includeInherited) return scopes;
    
    // 添加继承作用域
    const inherited = scopes.flatMap(s => this.getInheritedScopes(s));
    return [...new Set([...scopes, ...inherited])];
  }
  
  private getInheritedScopes(scope: string): string[] {
    if (scope.startsWith("project:")) return ["global"];
    if (scope.startsWith("user:")) return ["global"];
    return [];
  }
}
```

#### 方案 3: 跨 Agent 消息传递
```typescript
// 新建 src/message-passing.ts
interface AgentMessage {
  from: string;
  to: string[];
  type: "notification" | "request" | "response";
  scope: string;  // 消息关联的作用域
  payload: any;
}

class AgentMessageBus {
  constructor(private store: MemoryStore, private scopeManager: MemoryScopeManager) {}
  
  async send(message: AgentMessage): Promise<string> {
    // 存储到共享作用域
    const scope = message.scope || `agent:${message.from}`;
    return (await this.store.store({
      text: JSON.stringify(message.payload),
      vector: await embedder.embedPassage(JSON.stringify(message.payload)),
      category: "fact",
      scope,
      metadata: JSON.stringify({
        type: "agent_message",
        message: message,
      }),
    })).id;
  }
  
  async receive(agentId: string): Promise<AgentMessage[]> {
    // 检索发送给该 Agent 的消息
    const scopes = this.scopeManager.getAccessibleScopes(agentId);
    // ...检索逻辑
  }
}
```

---

## 4. 实现优先级建议

### P0 (核心功能)
1. **TaskNotification 存储层集成**
   - 定义 TaskNotification 类型
   - 扩展 `memory_store` 工具支持 task 类型
   - 实现任务状态更新方法

2. **Agent 作用域隔离**
   - 配置多 Agent 作用域权限
   - 验证 `scopeFilter` 在检索中的正确应用
   - 测试跨 Agent 访问控制

### P1 (增强功能)
3. **上下文注入优化**
   - 实现多源上下文融合
   - 添加动态 token 预算控制
   - 支持 Agent 角色感知过滤

4. **跨 Agent 消息传递**
   - 实现 AgentMessageBus
   - 支持请求 - 响应模式
   - 添加消息过期机制

### P2 (可选功能)
5. **作用域继承**
   - 实现动态作用域继承
   - 支持通配符作用域配置

6. **高级检索特性**
   - 支持跨作用域联合检索
   - 添加检索结果解释性（为什么这条记忆被检索）

---

## 5. 技术风险与注意事项

### 风险 1: 作用域过滤性能
- **问题**: 多作用域 OR 条件可能导致查询变慢
- **缓解**: 在存储层添加作用域索引，或使用应用层过滤

### 风险 2: 元数据一致性
- **问题**: `metadata` 字段为 JSON 字符串，缺乏类型安全
- **缓解**: 定义严格的序列化/反序列化函数，添加 schema 验证

### 风险 3: 跨 Agent 数据竞争
- **问题**: 多 Agent 同时写入同一作用域可能导致冲突
- **缓解**: 使用 `importEntry()` 保留原始 ID，实现乐观锁

### 风险 4: 上下文注入过量
- **问题**: 多源融合可能导致上下文超出 token 限制
- **缓解**: 实现动态 token 预算，优先保留高相关性内容

---

## 6. 下一步行动

1. **阅读相关设计文档**
   - `~/workspace/claude-context-fusion-design.md` (部分截断，需重新读取)
   - Context Manager P2 需求文档

2. **创建原型实现**
   - 在 `context-manager-impl/` 目录下创建原型代码
   - 优先实现 TaskNotification 存储层

3. **测试验证**
   - 创建多 Agent 测试场景
   - 验证作用域隔离正确性
   - 测试跨 Agent 消息传递

---

**报告生成**: Subagent (analyst-p2)  
**后续任务**: 根据此报告实现 Context Manager P2 集成
