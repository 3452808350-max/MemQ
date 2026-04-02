# Context Manager Implementation

基于 Claude Code 上下文管理 + OpenClaw 短期记忆融合方案的 P0 实现。

## 项目结构

```
context-manager-impl/
├── src/
│   ├── core/
│   │   ├── TokenBudget.ts      # Token 预算管理
│   │   ├── MessageHistory.ts   # 消息历史管理
│   │   ├── ContextManager.ts   # 核心协调器
│   │   └── index.ts            # 导出
│   ├── types/
│   │   └── index.ts            # 类型定义
│   └── utils/                  # 工具函数 (待实现)
├── tests/
│   ├── TokenBudget.test.ts
│   ├── MessageHistory.test.ts
│   └── ContextManager.test.ts
├── package.json
├── tsconfig.json
└── README.md
```

## 核心模块

### 1. TokenBudget

Token 预算管理，核心功能：
- 预算分配和跟踪
- 阈值检测（warning 80% / critical 95%）
- 紧急释放机制

```typescript
import { TokenBudget } from "./src/core/TokenBudget.js";

const budget = new TokenBudget({
  totalBudget: 200000,
  reserveBudget: 40000,
  warningThreshold: 0.8,
  criticalThreshold: 0.95,
});

budget.recordConversationHistory(50000);
const alert = budget.checkThresholds(); // null or warning/critical
```

### 2. MessageHistory

消息历史管理，核心功能：
- 消息存储和优先级分层
- FIFO 截断策略
- 自动触发压缩

```typescript
import { MessageHistory } from "./src/core/MessageHistory.js";

const history = new MessageHistory({
  maxMessages: 200,
  truncationStrategy: "fifo",
});

history.addMessage({
  id: "1",
  role: "user",
  content: "Hello",
  timestamp: Date.now(),
});
```

### 3. ContextManager

上下文管理核心协调器：
- 初始化 TokenBudget 和 MessageHistory
- 处理消息注入上下文
- 生命周期钩子（Agent Start/End/Reset）

```typescript
import { ContextManager } from "./src/core/ContextManager.js";

const manager = new ContextManager();

await manager.processMessage(
  { id: "1", role: "user", content: "Hello", timestamp: Date.now() },
  { sessionId: "session-1" }
);

const state = manager.getContextState();
```

## 配置参数

### TokenBudgetConfig

| 参数 | 默认值 | 说明 |
|------|--------|------|
| totalBudget | 200000 | 总 token 预算 |
| reserveBudget | 40000 | 保留预算 |
| warningThreshold | 0.8 | 警告阈值 |
| criticalThreshold | 0.95 | 紧急阈值 |
| compactionTarget | 0.6 | 压缩目标 |

### MessageHistoryConfig

| 参数 | 默认值 | 说明 |
|------|--------|------|
| maxMessages | 200 | 最大消息数 |
| truncationStrategy | "fifo" | 截断策略 |
| compressionTrigger.messageCount | 150 | 触发压缩的消息数 |
| compressionTrigger.tokenCount | 160000 | 触发压缩的 token 数 |

## 优先级分层

| 层级 | 优先级 | 选择器 | 最少保留 | 最多保留 |
|------|--------|--------|---------|---------|
| system_critical | 10 | role: system | 1 | 5 |
| tool_results | 8 | tool: * | 5 | 20 |
| user_decisions | 7 | pattern: 决定/decided | 3 | 10 |
| user_messages | 5 | role: user | 10 | 50 |
| assistant_responses | 3 | role: assistant | 5 | 30 |

## 运行测试

```bash
npm install
npm run test:run
```

## 与 memory-lancedb-pro 集成

P0 阶段最小集成：

```typescript
import { ContextManager } from "./src/core/ContextManager.js";
import { MemoryStore, MemoryRetriever } from "memory-lancedb-pro";

const manager = new ContextManager();

// 在 OpenClaw 插件中使用
export default {
  name: "context-manager",
  async init(ctx) {
    const { store, retriever } = ctx.memory;
    
    // 注册钩子
    ctx.hooks.on("agent:start", (event) => manager.onAgentStart(event));
    ctx.hooks.on("agent:end", (event) => manager.onAgentEnd(event));
    ctx.hooks.on("session:reset", (event) => manager.onSessionReset(event));
  },
};
```

## 实现阶段

### P0 (当前) ✅
- [x] TokenBudget 基础功能
- [x] MessageHistory FIFO 截断
- [x] ContextManager 协调器
- [x] 单元测试

### P1 (下一步)
- [ ] 优先级截断策略
- [ ] LLM 语义压缩
- [ ] MultiAgentContext 支持
- [ ] TaskNotification 存储

### P2
- [ ] 动态预算调整
- [ ] 自适应压缩
- [ ] 完整 Hook 集成

## 设计文档

参考：`~/workspace/claude-context-fusion-design.md`

## License

MIT
