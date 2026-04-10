# ACP Client 设计文档 - OpenClaw 调用外部 Agent

## 目标

让 OpenClaw 的 agent 能通过 ACP 协议调用其他平台的 agent（Claude Code、Codex、Copilot），并将结果融入多 Agent 工作流。

## 核心 API

```typescript
// 新增 tool: acp_delegate
interface ACPDelegateParams {
  command: string;       // ACP agent 命令，如 "claude", "codex", "copilot"
  args?: string[];       // ACP 参数，默认 ["--acp", "--stdio"]
  prompt: string;        // 发送给 agent 的 prompt
  cwd?: string;          // 工作目录
  timeout?: number;      // 超时秒数，默认 300
  tools?: ToolSchema[];  // 可选：传递工具 schema
}

interface ACPDelegateResult {
  status: "completed" | "timeout" | "error";
  response: string;      // agent 的文本响应
  tool_calls?: ToolCall[]; // agent 想要执行的 tool calls
  reasoning?: string;    // agent 的 reasoning (如果支持)
  duration_ms: number;
}
```

## 实现架构

```
┌─────────────────────────────────────────────────────────────┐
│                   OpenClaw Gateway                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  sessions_spawn (runtime: "acp")                           │
│  ├─ 检测 agentId 是否为 ACP agent                          │
│  ├─ 创建 ACPClient                                         │
│  ├─ 启动 subprocess                                        │
│  ├─ JSON-RPC 通信                                          │
│  └─ 返回结果                                               │
│                                                             │
│  或者新增 tool:                                            │
│  acp_delegate                                              │
│  ├─ 直接调用外部 agent                                     │
│  ├─ 不创建新 session                                       │
│  └─ 结果返回给调用者                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 核心类: ACPClient

```typescript
// acp-client.ts (~300 行)

import { spawn, ChildProcess } from 'child_process';
import { v4 as uuidv4 } from 'uuid';

interface ACPConfig {
  command: string;
  args: string[];
  cwd: string;
  timeout: number;
}

interface JSONRPCRequest {
  jsonrpc: "2.0";
  id: number;
  method: string;
  params: Record<string, any>;
}

interface JSONRPCResponse {
  jsonrpc: "2.0";
  id: number;
  result?: any;
  error?: { code: number; message: string };
}

interface JSONRPCNotification {
  jsonrpc: "2.0";
  method: string;
  params: Record<string, any>;
}

export class ACPClient {
  private process: ChildProcess | null = null;
  private requestId = 0;
  private pendingRequests: Map<number, { resolve: Function; reject: Function }> = new Map();
  private textParts: string[] = [];
  private reasoningParts: string[] = [];
  private buffer = '';

  constructor(private config: ACPConfig) {}

  async start(): Promise<void> {
    this.process = spawn(this.config.command, this.config.args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: this.config.cwd,
    });

    if (!this.process.stdin || !this.process.stdout) {
      throw new Error('ACP process did not expose stdin/stdout');
    }

    // 处理 stdout (JSON-RPC responses)
    this.process.stdout.on('data', (data: Buffer) => {
      this.buffer += data.toString();
      this.processBuffer();
    });

    // 处理 stderr (logs)
    this.process.stderr?.on('data', (data: Buffer) => {
      console.debug('[ACP stderr]', data.toString());
    });

    this.process.on('close', (code) => {
      console.debug('[ACP] process exited with code', code);
    });
  }

  private processBuffer(): void {
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || ''; // 保留不完整的行

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        this.handleMessage(msg);
      } catch (e) {
        console.debug('[ACP] non-JSON line:', line);
      }
    }
  }

  private handleMessage(msg: JSONRPCResponse | JSONRPCNotification): void {
    // 处理 notification
    if (msg.method && !('id' in msg && msg.id !== undefined)) {
      this.handleNotification(msg as JSONRPCNotification);
      return;
    }

    // 处理 response
    const pending = this.pendingRequests.get(msg.id);
    if (!pending) {
      console.debug('[ACP] unknown response id:', msg.id);
      return;
    }

    this.pendingRequests.delete(msg.id);

    if (msg.error) {
      pending.reject(new Error(msg.error.message));
    } else {
      pending.resolve(msg.result);
    }
  }

  private handleNotification(msg: JSONRPCNotification): void {
    const method = msg.method;
    const params = msg.params || {};

    // session/update - 收集响应文本
    if (method === 'session/update') {
      const update = params.update || {};
      const kind = update.sessionUpdate;
      const content = update.content || {};

      if (kind === 'agent_message_chunk') {
        this.textParts.push(content.text || '');
      } else if (kind === 'agent_thought_chunk') {
        this.reasoningParts.push(content.text || '');
      }
      return;
    }

    // session/request_permission - 自动 approve
    if (method === 'session/request_permission') {
      this.sendResponse(msg.id!, { outcome: { outcome: 'allow_once' } });
      return;
    }

    // fs/read_text_file - 处理文件读取请求
    if (method === 'fs/read_text_file') {
      this.handleFileRead(msg.id!, params);
      return;
    }

    // fs/write_text_file - 处理文件写入请求
    if (method === 'fs/write_text_file') {
      this.handleFileWrite(msg.id!, params);
      return;
    }

    // 其他方法 - 暂不支持
    this.sendError(msg.id!, -32601, `Method '${method}' not supported`);
  }

  private handleFileRead(id: number, params: Record<string, any>): void {
    const path = params.path;
    if (!path) {
      this.sendError(id, -32602, 'Missing path parameter');
      return;
    }

    // 安全检查：确保路径在 cwd 内
    const resolvedPath = this.resolvePath(path);
    if (!resolvedPath) {
      this.sendError(id, -32602, `Path '${path}' is outside cwd`);
      return;
    }

    try {
      const fs = require('fs');
      let content = fs.readFileSync(resolvedPath, 'utf-8');

      // 处理 line/limit 参数
      const line = params.line;
      const limit = params.limit;
      if (line && limit) {
        const lines = content.split('\n');
        content = lines.slice(line - 1, line - 1 + limit).join('\n');
      }

      this.sendResponse(id, { content });
    } catch (e: any) {
      this.sendError(id, -32602, e.message);
    }
  }

  private handleFileWrite(id: number, params: Record<string, any>): void {
    const path = params.path;
    const content = params.content || '';

    if (!path) {
      this.sendError(id, -32602, 'Missing path parameter');
      return;
    }

    const resolvedPath = this.resolvePath(path);
    if (!resolvedPath) {
      this.sendError(id, -32602, `Path '${path}' is outside cwd`);
      return;
    }

    try {
      const fs = require('fs');
      const dir = require('path').dirname(resolvedPath);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(resolvedPath, content);
      this.sendResponse(id, null);
    } catch (e: any) {
      this.sendError(id, -32602, e.message);
    }
  }

  private resolvePath(path: string): string | null {
    const fs = require('fs');
    const pathLib = require('path');

    if (!pathLib.isAbsolute(path)) {
      return null; // ACP 要求绝对路径
    }

    const resolved = pathLib.resolve(path);
    const cwdResolved = pathLib.resolve(this.config.cwd);

    // 确保路径在 cwd 内
    if (!resolved.startsWith(cwdResolved)) {
      return null;
    }

    return resolved;
  }

  private sendResponse(id: number, result: any): void {
    const response = {
      jsonrpc: '2.0',
      id,
      result,
    };
    this.send(JSON.stringify(response));
  }

  private sendError(id: number, code: number, message: string): void {
    const response = {
      jsonrpc: '2.0',
      id,
      error: { code, message },
    };
    this.send(JSON.stringify(response));
  }

  private send(data: string): void {
    if (!this.process?.stdin) {
      throw new Error('ACP process not running');
    }
    this.process.stdin.write(data + '\n');
  }

  private async request(method: string, params: Record<string, any>): Promise<any> {
    const id = ++this.requestId;
    const request: JSONRPCRequest = {
      jsonrpc: '2.0',
      id,
      method,
      params,
    };

    return new Promise((resolve, reject) => {
      this.pendingRequests.set(id, { resolve, reject });
      this.send(JSON.stringify(request));

      // 超时处理
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error(`Timeout waiting for response to ${method}`));
        }
      }, this.config.timeout * 1000);
    });
  }

  async initialize(): Promise<void> {
    await this.request('initialize', {
      protocolVersion: 1,
      clientCapabilities: {
        fs: {
          readTextFile: true,
          writeTextFile: true,
        },
      },
      clientInfo: {
        name: 'openclaw',
        title: 'OpenClaw',
        version: '1.0.0',
      },
    });
  }

  async createSession(): Promise<string> {
    const result = await this.request('session/new', {
      cwd: this.config.cwd,
      mcpServers: [], // 可选：传递 MCP servers
    });

    const sessionId = result?.sessionId;
    if (!sessionId) {
      throw new Error('ACP agent did not return sessionId');
    }

    return sessionId;
  }

  async sendPrompt(sessionId: string, prompt: string, tools?: ToolSchema[]): Promise<{ text: string; reasoning?: string }> {
    this.textParts = [];
    this.reasoningParts = [];

    // 构建 prompt
    let fullPrompt = prompt;
    if (tools && tools.length > 0) {
      fullPrompt += '\n\nAvailable tools:\n' + JSON.stringify(tools, null, 2);
      fullPrompt += '\n\nUse tools by emitting <tool_call>{...}.getTag() blocks with JSON.';
    }

    await this.request('session/prompt', {
      sessionId,
      prompt: [
        {
          type: 'text',
          text: fullPrompt,
        },
      ],
    });

    return {
      text: this.textParts.join(''),
      reasoning: this.reasoningParts.join(''),
    };
  }

  extractToolCalls(text: string): ToolCall[] {
    // 匹配 <tool_call>{...}.getTag() 格式的 tool calls
    const regex = /<tool_call>\s*(\{.*?\})\s*
/gs;
    const toolCalls: ToolCall[] = [];

    for (const match of text.matchAll(regex)) {
      try {
        const json = JSON.parse(match[1]);
        if (json.function?.name) {
          toolCalls.push({
            id: json.id || `acp_${toolCalls.length + 1}`,
            type: 'function',
            function: {
              name: json.function.name,
              arguments: json.function.arguments || '{}',
            },
          });
        }
      } catch (e) {
        // ignore invalid JSON
      }
    }

    return toolCalls;
  }

  close(): void {
    if (this.process) {
      this.process.kill();
      this.process = null;
    }
    this.pendingRequests.clear();
  }
}
```

## Tool 实现: acp_delegate

```typescript
// tools/acp_delegate.ts

import { ACPClient } from '../acp-client';

export async function acp_delegate(params: ACPDelegateParams): Promise<ACPDelegateResult> {
  const startTime = Date.now();
  
  const client = new ACPClient({
    command: params.command,
    args: params.args || ['--acp', '--stdio'],
    cwd: params.cwd || process.cwd(),
    timeout: params.timeout || 300,
  });

  try {
    await client.start();
    await client.initialize();
    const sessionId = await client.createSession();
    
    const result = await client.sendPrompt(sessionId, params.prompt, params.tools);
    const toolCalls = client.extractToolCalls(result.text);
    
    client.close();

    return {
      status: 'completed',
      response: result.text,
      tool_calls: toolCalls,
      reasoning: result.reasoning,
      duration_ms: Date.now() - startTime,
    };
  } catch (e: any) {
    client.close();
    
    if (e.message.includes('Timeout')) {
      return {
        status: 'timeout',
        response: '',
        duration_ms: Date.now() - startTime,
      };
    }

    return {
      status: 'error',
      response: '',
      error: e.message,
      duration_ms: Date.now() - startTime,
    };
  }
}
```

## 使用示例

### 1. 从 Telegram 调用 Claude Code

```typescript
// 用户: "帮我用 Claude 分析这个 PR"

await acp_delegate({
  command: 'claude',
  args: ['--acp', '--stdio'],
  prompt: 'Review this PR: https://github.com/xxx/pull/123\nFocus on code quality and potential bugs.',
  cwd: '/home/user/project',
  timeout: 300,
});
```

### 2. Coordinator Mode 中使用 ACP Agent

```typescript
// 在 Coordinator 四阶段工作流中，Task Agent 可以是 ACP agent

const coordinator = new Coordinator();
coordinator.addAgent({
  id: 'claude-coder',
  type: 'acp',
  config: {
    command: 'claude',
    args: ['--acp', '--stdio'],
  },
});

// Task Agent 执行编码任务
await coordinator.runPhase('task', {
  task: 'Implement feature X',
  agentId: 'claude-coder',
});
```

### 3. 多 Agent 并行（Research + Code）

```typescript
// 使用现有的 sessions_spawn，但 runtime 改为 "acp"

const [research, code] = await Promise.all([
  sessions_spawn({
    runtime: 'acp',
    agentId: 'claude',  // ACP agent
    task: 'Research best practices for Y',
  }),
  sessions_spawn({
    runtime: 'subagent',  // 本地 subagent
    task: 'Draft implementation plan',
  }),
]);
```

## 工作量估算

| 模块 | 工作量 | 依赖 |
|------|--------|------|
| ACPClient | 1-2天 | 无 |
| acp_delegate tool | 0.5天 | ACPClient |
| sessions_spawn 改造 | 1天 | ACPClient |
| 测试 + 文档 | 1天 | 全部 |
| **总计** | **3-4天** | |

## 关键差异 vs Hermes

1. **不实现 ACP Server** - 我们不需要被 IDE 调用
2. **只实现 ACP Client** - 调用外部 agent
3. **融入现有架构** - 使用 sessions_spawn 或新增 tool
4. **利用 Coordinator Mode** - 外部 agent 作为 Task Agent

## 下一步

1. 实现 ACPClient 类
2. 添加 acp_delegate tool
3. 改造 sessions_spawn 支持 runtime="acp"
4. 测试 Claude Code / Codex 集成
5. 写使用文档
