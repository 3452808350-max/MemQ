# Module 01: Agent 定义格式

## 目标

建立统一的 Agent 定义格式，支持内置 Agent、自定义 Agent 和 Plugin Agent。

## 设计原则

1. **Frontmatter 优先**: 使用 YAML frontmatter + Markdown 内容
2. **向后兼容**: 支持 JSON 格式作为备选
3. **类型安全**: TypeScript 接口严格定义
4. **可扩展**: 预留自定义字段

## 文件格式

### 基础 Agent 定义 (YAML Frontmatter)

```markdown
---
# 基础信息
agent_type: "explore"           # 内置: explore/plan/custom
name: "code-explorer"           # 可寻址名称
version: "1.0.0"
description: "Fast codebase exploration agent"

# 模型配置
model: "inherit"                # inherit | haiku | sonnet | opus
effort: "high"                  # low | medium | high
max_turns: 200

# 权限配置
permission_mode: "default"      # default | plan | bubble | auto | bypass
tools:
  allow: ["Read", "Grep", "Glob", "Bash"]
  deny: ["Write", "Edit", "Agent"]

# 技能与 MCP
skills: ["git", "nodejs"]
mcp_servers:
  - name: "fetch"
    config:
      timeout: 30000

# 内存与隔离
memory_scope: "project"         # user | project | local | session
isolation: "none"               # none | worktree | remote

# 优化选项
one_shot: true                  # 跳过 continuation
omit_claude_md: true            # 节省 token
background: false               # 是否后台运行

# 元数据
source: "built-in"              # built-in | user | project | plugin
author: "anthropic"
tags: ["explore", "read-only"]
---

# System Prompt

You are a file search specialist...

## Rules

1. Do NOT create or modify files
2. Spawn multiple parallel tool calls
3. ...
```

### JSON 格式 (备选)

```json
{
  "agent_type": "explore",
  "name": "code-explorer",
  "version": "1.0.0",
  "description": "Fast codebase exploration agent",
  "model": "inherit",
  "effort": "high",
  "max_turns": 200,
  "permission_mode": "default",
  "tools": {
    "allow": ["Read", "Grep", "Glob", "Bash"],
    "deny": ["Write", "Edit", "Agent"]
  },
  "skills": ["git", "nodejs"],
  "mcp_servers": [
    { "name": "fetch", "config": { "timeout": 30000 } }
  ],
  "memory_scope": "project",
  "isolation": "none",
  "one_shot": true,
  "omit_claude_md": true,
  "background": false,
  "source": "built-in",
  "author": "anthropic",
  "tags": ["explore", "read-only"],
  "system_prompt": "You are a file search specialist..."
}
```

## TypeScript 接口

```typescript
// 基础 Agent 定义
interface AgentDefinition {
  // 基础信息
  agentType: string
  name: string
  version?: string
  description?: string
  
  // 模型配置
  model?: 'inherit' | 'haiku' | 'sonnet' | 'opus' | string
  effort?: 'low' | 'medium' | 'high'
  maxTurns?: number
  
  // 权限配置
  permissionMode?: PermissionMode
  tools?: {
    allow?: string[]
    deny?: string[]
  }
  
  // 技能与 MCP
  skills?: string[]
  mcpServers?: McpServerSpec[]
  
  // 内存与隔离
  memoryScope?: 'user' | 'project' | 'local' | 'session'
  isolation?: 'none' | 'worktree' | 'remote'
  
  // 优化选项
  oneShot?: boolean
  omitClaudeMd?: boolean
  background?: boolean
  
  // 元数据
  source: 'built-in' | 'user' | 'project' | 'plugin'
  author?: string
  tags?: string[]
  
  // 系统提示词
  systemPrompt: string
}

// MCP 服务器规格
interface McpServerSpec {
  name: string
  config?: Record<string, unknown>
}

// 权限模式
type PermissionMode = 
  | 'default' 
  | 'plan' 
  | 'bubble' 
  | 'auto' 
  | 'acceptEdits'
  | 'bypassPermissions'
  | 'dontAsk'
```

## 存储位置

```
.agents/
├── definitions/           # 全局定义
│   ├── built-in/          # 内置 Agent
│   │   ├── explore.md
│   │   ├── plan.md
│   │   └── general.md
│   ├── user/              # 用户自定义
│   │   └── my-agent.md
│   └── plugins/           # 插件提供
│       └── plugin-name/
│           └── agent.md
└── registry.json          # 注册表索引
```

## 内置 Agent 类型

| Agent Type | 用途 | 默认 Tools | 特殊配置 |
|------------|------|-----------|---------|
| `explore` | 代码库探索 | Read, Grep, Glob, Bash | oneShot: true, omitClaudeMd: true |
| `plan` | 架构规划 | Read, Grep, Glob, Bash | oneShot: true, read-only |
| `general` | 通用任务 | 继承父工具 | 默认配置 |
| `fork` | Fork Subagent | 继承父工具 | permissionMode: 'bubble' |

## 加载流程

```typescript
async function loadAgentDefinitions(): Promise<AgentDefinition[]> {
  const definitions: AgentDefinition[] = []
  
  // 1. 加载内置 Agent
  definitions.push(...await loadBuiltInAgents())
  
  // 2. 加载用户自定义
  definitions.push(...await loadUserAgents())
  
  // 3. 加载插件 Agent
  definitions.push(...await loadPluginAgents())
  
  // 4. 验证并去重
  return validateAndDeduplicate(definitions)
}
```

## 与 OpenClaw 集成

```typescript
// 包装 sessions_spawn
interface SpawnAgentOptions {
  // OpenClaw 原生
  task: string
  runtime: 'subagent' | 'acp'
  
  // Claude Plugin 扩展
  agentType?: string           # 引用预定义 Agent
  agentDefinition?: AgentDefinition  # 内联定义
}

// 使用示例
sessions_spawn({
  task: "Explore the codebase",
  runtime: "subagent",
  agentType: "explore"        # 自动应用 explore Agent 配置
})
```

## 测试计划

- [ ] 解析 YAML frontmatter
- [ ] 解析 JSON 格式
- [ ] 验证必填字段
- [ ] 工具列表展开 (`['*']` → 全部)
- [ ] 内置 Agent 加载
- [ ] 冲突检测 (同名 Agent)
