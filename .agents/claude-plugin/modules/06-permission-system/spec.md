# Module 06: Permission System

## 目标

实现灵活的权限控制，支持多种模式和规则引擎。

## 核心设计

### 权限模式

```typescript
type PermissionMode =
  | 'default'        // 默认：所有敏感操作需确认
  | 'plan'           // 计划模式：只读，不执行
  | 'acceptEdits'    // 自动接受文件编辑
  | 'bypassPermissions'  // 绕过所有权限（危险）
  | 'dontAsk'        // 不询问，但保留安全检查
  | 'auto'           // 自动分类器模式（实验性）
  | 'bubble'         // 权限提示冒泡到父 Agent（Fork 专用）

// 外部可见模式（用户可配置）
type ExternalPermissionMode = 
  | 'default' 
  | 'plan' 
  | 'acceptEdits' 
  | 'bypassPermissions' 
  | 'dontAsk'

// 内部模式
// auto: ant-only，对外显示为 default
// bubble: Fork Subagent 专用
```

### 模式配置

```typescript
interface PermissionModeConfig {
  title: string
  shortTitle: string
  symbol: string
  color: 'text' | 'planMode' | 'autoAccept' | 'error' | 'warning'
  external: ExternalPermissionMode
}

const PERMISSION_MODE_CONFIG: Record<PermissionMode, PermissionModeConfig> = {
  default: {
    title: 'Default',
    shortTitle: 'Default',
    symbol: '',
    color: 'text',
    external: 'default'
  },
  plan: {
    title: 'Plan Mode',
    shortTitle: 'Plan',
    symbol: '⏸',
    color: 'planMode',
    external: 'plan'
  },
  acceptEdits: {
    title: 'Accept edits',
    shortTitle: 'Accept',
    symbol: '⏵⏵',
    color: 'autoAccept',
    external: 'acceptEdits'
  },
  bypassPermissions: {
    title: 'Bypass Permissions',
    shortTitle: 'Bypass',
    symbol: '⏵⏵',
    color: 'error',
    external: 'bypassPermissions'
  },
  dontAsk: {
    title: "Don't Ask",
    shortTitle: 'DontAsk',
    symbol: '⏵⏵',
    color: 'error',
    external: 'dontAsk'
  },
  auto: {
    title: 'Auto mode',
    shortTitle: 'Auto',
    symbol: '⏵⏵',
    color: 'warning',
    external: 'default'  // 对外显示为 default
  },
  bubble: {
    title: 'Bubble',
    shortTitle: 'Bubble',
    symbol: '',
    color: 'text',
    external: 'default'
  }
}
```

### 权限决策

```typescript
type PermissionDecision =
  | AllowDecision
  | AskDecision
  | DenyDecision

interface AllowDecision {
  behavior: 'allow'
  updatedInput?: unknown      // 可能修改的输入
  userModified?: boolean      // 用户是否修改
  decisionReason: DecisionReason
}

interface AskDecision {
  behavior: 'ask'
  message: string             // 提示用户的消息
  suggestions?: PermissionUpdate[]  // 建议的权限更新
  blockedPath?: string        // 被阻止的路径
  pendingClassifierCheck?: PendingClassifierCheck
}

interface DenyDecision {
  behavior: 'deny'
  message: string
  decisionReason: DecisionReason
}
```

### 决策原因

```typescript
type DecisionReason =
  | { type: 'rule'; rule: PermissionRule }
  | { type: 'mode'; mode: PermissionMode }
  | { type: 'classifier'; classifier: string; reason: string }
  | { type: 'safetyCheck'; reason: string; classifierApprovable: boolean }
  | { type: 'hook'; hookName: string; reason?: string }
  | { type: 'other'; reason: string }
```

### 权限规则

```typescript
interface PermissionRule {
  source: PermissionRuleSource
  behavior: 'allow' | 'deny' | 'ask'
  toolName: string
  pattern?: string            // 可选匹配模式
}

type PermissionRuleSource =
  | 'userSettings'      // ~/.claude/settings.json
  | 'projectSettings'   // .claude/settings.json
  | 'localSettings'     // .claude/local.json
  | 'flagSettings'      // 特性标志
  | 'policySettings'    // 企业策略
  | 'cliArg'            // 命令行参数
  | 'command'           // 运行时命令
  | 'session'           // 会话级

// 规则存储
interface PermissionRules {
  allow: PermissionRule[]
  deny: PermissionRule[]
  ask: PermissionRule[]
}
```

### 规则引擎

```typescript
class PermissionEngine {
  private rules: PermissionRules
  private mode: PermissionMode
  
  checkPermission(
    toolName: string,
    input: unknown,
    context: PermissionContext
  ): PermissionDecision {
    // 1. 检查模式覆盖
    if (this.mode === 'bypassPermissions') {
      return { behavior: 'allow', decisionReason: { type: 'mode', mode: 'bypassPermissions' } }
    }
    
    if (this.mode === 'plan') {
      // Plan 模式下只允许读操作
      if (!isReadOnlyTool(toolName)) {
        return { 
          behavior: 'deny', 
          message: 'Plan mode: write operations not allowed',
          decisionReason: { type: 'mode', mode: 'plan' }
        }
      }
    }
    
    // 2. 检查 deny 规则
    const denyRule = this.findMatchingRule(this.rules.deny, toolName, input)
    if (denyRule) {
      return {
        behavior: 'deny',
        message: `Denied by rule: ${denyRule.pattern}`,
        decisionReason: { type: 'rule', rule: denyRule }
      }
    }
    
    // 3. 检查 allow 规则
    const allowRule = this.findMatchingRule(this.rules.allow, toolName, input)
    if (allowRule) {
      return {
        behavior: 'allow',
        decisionReason: { type: 'rule', rule: allowRule }
      }
    }
    
    // 4. 检查 ask 规则
    const askRule = this.findMatchingRule(this.rules.ask, toolName, input)
    if (askRule) {
      return {
        behavior: 'ask',
        message: `Confirm: ${toolName}`,
        decisionReason: { type: 'rule', rule: askRule }
      }
    }
    
    // 5. 默认行为
    return this.getDefaultDecision(toolName, input)
  }
  
  private findMatchingRule(
    rules: PermissionRule[],
    toolName: string,
    input: unknown
  ): PermissionRule | undefined {
    return rules.find(rule => {
      if (rule.toolName !== toolName && rule.toolName !== '*') {
        return false
      }
      if (rule.pattern && !matchesPattern(input, rule.pattern)) {
        return false
      }
      return true
    })
  }
}
```

### Agent 权限上下文

```typescript
interface ToolPermissionContext {
  mode: PermissionMode
  additionalWorkingDirectories: Map<string, AdditionalWorkingDirectory>
  alwaysAllowRules: ToolPermissionRulesBySource
  alwaysDenyRules: ToolPermissionRulesBySource
  alwaysAskRules: ToolPermissionRulesBySource
  isBypassPermissionsModeAvailable: boolean
  shouldAvoidPermissionPrompts?: boolean
  awaitAutomatedChecksBeforeDialog?: boolean
}

interface AdditionalWorkingDirectory {
  path: string
  source: WorkingDirectorySource
}
```

### Agent 工具过滤

```typescript
function filterToolsForAgent(
  tools: Tool[],
  agentDefinition: AgentDefinition,
  isAsync: boolean
): Tool[] {
  return tools.filter(tool => {
    // MCP 工具对所有 Agent 开放
    if (tool.name.startsWith('mcp__')) return true
    
    // Plan 模式特殊处理
    if (tool.name === 'ExitPlanMode' && agentDefinition.permissionMode === 'plan') {
      return true
    }
    
    // 所有 Agent 禁止的工具
    if (ALL_AGENT_DISALLOWED_TOOLS.has(tool.name)) return false
    
    // 自定义 Agent 额外禁止
    if (agentDefinition.source !== 'built-in' && 
        CUSTOM_AGENT_DISALLOWED_TOOLS.has(tool.name)) {
      return false
    }
    
    // 异步 Agent 限制
    if (isAsync && !ASYNC_AGENT_ALLOWED_TOOLS.has(tool.name)) {
      return false
    }
    
    return true
  })
}

// 禁止列表
const ALL_AGENT_DISALLOWED_TOOLS = new Set([
  'InternalTool1',
  'InternalTool2'
])

const CUSTOM_AGENT_DISALLOWED_TOOLS = new Set([
  'DangerousTool1'
])

const ASYNC_AGENT_ALLOWED_TOOLS = new Set([
  'Bash', 'Read', 'Write', 'Edit', 'Grep', 'Glob'
  // ... 但不包括 Agent 工具本身（防止嵌套）
])
```

### 权限更新

```typescript
type PermissionUpdate =
  | { type: 'addRules'; destination: UpdateDestination; rules: PermissionRule[] }
  | { type: 'removeRules'; destination: UpdateDestination; rules: PermissionRule[] }
  | { type: 'setMode'; destination: UpdateDestination; mode: PermissionMode }
  | { type: 'addDirectories'; destination: UpdateDestination; directories: string[] }
  | { type: 'removeDirectories'; destination: UpdateDestination; directories: string[] }

type UpdateDestination =
  | 'userSettings'
  | 'projectSettings'
  | 'localSettings'
  | 'session'

async function updatePermission(
  update: PermissionUpdate
): Promise<void> {
  switch (update.type