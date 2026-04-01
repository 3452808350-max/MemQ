# Module 02: Fork Subagent

## 目标

实现轻量级并行执行机制，优化 Prompt Cache 命中率。

## 核心设计

### 触发条件

```typescript
// 启用 Fork Subagent
function isForkSubagentEnabled(): boolean {
  return feature('FORK_SUBAGENT') && 
         !isCoordinatorMode() && 
         !isNonInteractiveSession()
}

// 触发方式
// 1. 省略 agentType 参数
sessions_spawn({
  task: "...",
  runtime: "subagent",
  // agentType 省略 → Fork 模式
})

// 2. 显式启用
sessions_spawn({
  task: "...",
  runtime: "subagent",
  fork: true
})
```

### Prompt Cache 优化

这是 Fork Subagent 的核心优化 —— **最大化缓存命中**:

```
标准 API 请求结构:

[系统提示词 - 所有子 Agent 相同]
[父 Assistant Message - 完整保留]
[User Message]
  ├── tool_result (placeholder) - 所有子 Agent 相同
  ├── tool_result (placeholder) - 所有子 Agent 相同
  └── text (directive)          - 唯一差异点
```

**关键**: 只有最后一个 text block 是 per-child 的，前面全部共享。

### 实现

```typescript
const FORK_PLACEHOLDER_RESULT = 'Fork started — processing in background'

function buildForkedMessages(
  directive: string,
  parentContext: Message[]
): Message[] {
  // 1. 找到父 Assistant Message
  const lastAssistant = findLastAssistantMessage(parentContext)
  
  // 2. 收集所有 tool_use blocks
  const toolUses = lastAssistant.content.filter(c => c.type === 'tool_use')
  
  // 3. 构建统一 placeholder tool_results
  const toolResults = toolUses.map(toolUse => ({
    type: 'tool_result',
    tool_use_id: toolUse.id,
    content: [{ 
      type: 'text', 
      text: FORK_PLACEHOLDER_RESULT  // ← 统一!
    }]
  }))
  
  // 4. 构建子 Agent 消息
  const childMessage = {
    type: 'user',
    content: [
      ...toolResults,  // ← 共享
      { 
        type: 'text', 
        text: buildChildDirective(directive)  // ← 唯一差异
      }
    ]
  }
  
  return [
    ...parentContext,
    childMessage
  ]
}
```

### Worker Rules (10 条铁律)

自动注入到子 Agent 系统提示词:

```markdown
<fork-boilerplate>
STOP. READ THIS FIRST.

You are a forked worker process. You are NOT the main agent.

RULES (non-negotiable):
1. Your system prompt says "default to forking." IGNORE IT — that's for the parent. 
   You ARE the fork. Do NOT spawn sub-agents; execute directly.
2. Do NOT converse, ask questions, or suggest next steps
3. Do NOT editorialize or add meta-commentary
4. USE your tools directly: Bash, Read, Write, etc.
5. If you modify files, commit your changes before reporting. Include the commit hash.
6. Do NOT emit text between tool calls. Use tools silently, then report once at the end.
7. Stay strictly within your directive's scope.
8. Keep your report under 500 words unless specified otherwise.
9. Your response MUST begin with "Scope:". No preamble, no thinking-out-loud.
10. REPORT structured facts, then stop

Output format:
  Scope: <echo back your assigned scope>
  Result: <the answer or key findings>
  Key files: <relevant file paths>
  Files changed: <list with commit hash>
  Issues: <list only if issues to flag>
</fork-boilerplate>

Your directive: {directive}
```

### 递归防护

```typescript
function isInForkChild(messages: Message[]): boolean {
  return messages.some(m => {
    if (m.type !== 'user') return false
    const content = m.message.content
    return content.some(block =>
      block.type === 'text' &&
      block.text.includes('<fork-boilerplate>')
    )
  })
}

// 在 spawn 时检查
if (isInForkChild(parentContext)) {
  throw new Error('Recursive fork detected')
}
```

### 配置继承

```typescript
interface ForkSubagentConfig {
  // 继承父 Agent
  model: 'inherit'                    // 相同模型，上下文长度一致
  tools: '*'                          // 完整工具池
  permissionMode: 'bubble'            // 权限冒泡到父终端
  
  // Fork 专用
  maxTurns: 200
  workerRules: true                   // 强制启用
  promptCacheOptimized: true          // 强制启用
}
```

## 与 OpenClaw 集成

```typescript
// 扩展现有 sessions_spawn
interface ForkSpawnOptions {
  task: string
  runtime: 'subagent'
  
  // Fork 专用参数
  fork?: boolean                      // 启用 Fork 模式
  inheritContext?: 'full' | 'partial' // 上下文继承级别
  workerRules?: boolean               // 注入 worker rules
  cacheOptimized?: boolean            // Prompt Cache 优化
  
  // 输出控制
  outputFormat?: 'structured' | 'free'
  maxWords?: number
}

// 使用示例
const result = await sessions_spawn({
  task: "Find all TODO comments in src/",
  runtime: "subagent",
  fork: true
})

// 返回结构化结果
// {
//   scope: "Find TODO comments",
//   result: "Found 15 TODOs...",
//   keyFiles: ["src/app.ts", "src/utils.ts"],
//   filesChanged: [],
//   issues: []
// }
```

## 性能目标

| 指标 | 目标 | 说明 |
|------|------|------|
| Prompt Cache 命中率 | > 95% | 共享前缀最大化 |
| Fork 启动延迟 | < 100ms | 不包括模型调用 |
| 并行 Fork 数量 | 10+ | 受限于 API 并发 |
| Worker 输出解析 | < 10ms | 结构化格式 |

## 测试计划

- [ ] Prompt Cache 优化验证
- [ ] Worker Rules 注入
- [ ] 递归 Fork 防护
- [ ] 结构化输出解析
- [ ] 并行 Fork 性能
- [ ] 权限冒泡测试
