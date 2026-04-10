# OpenClaw ACP Client

ACP Client for OpenClaw - 调用外部 ACP Agent（Claude Code、Codex、Copilot 等）。

## 安装

```bash
npm install
npm run build
```

## 使用

### 快速调用

```typescript
import { acp_call } from 'openclaw-acp-client';

// 调用 Claude Code
const result = await acp_call('claude', '分析当前项目的架构', {
  cwd: '/path/to/project',
});

console.log(result.text);
```

### 完整控制

```typescript
import { ACPClient } from 'openclaw-acp-client';

const client = new ACPClient({
  command: 'claude',
  args: ['--acp', '--stdio'],
  cwd: '/path/to/project',
  timeout: 300,
});

await client.start();
await client.initialize();
const sessionId = await client.createSession();

const result = await client.sendPrompt('帮我重构这个函数');
console.log(result.text);

client.close();
```

## 支持的 ACP Agent

| Agent | Command | 状态 |
|-------|---------|------|
| Claude Code | `claude --acp --stdio` | ✅ |
| Codex | `codex --acp --stdio` | ⏳ 待测试 |
| Copilot | `copilot --acp --stdio` | ⏳ 待测试 |
| Hermes | `hermes --acp` | ⏳ 待测试 |

## 测试

```bash
# 测试 Claude Code（需要安装 Claude Code CLI）
npm run test:claude
```

## 架构

```
ACPClient
├── start()          启动 subprocess
├── initialize()     JSON-RPC handshake
├── createSession()  创建 session
├── sendPrompt()     发送 prompt，收集响应
├── cancel()         取消当前操作
└── close()          关闭 agent

内部处理：
├── handleMessage()      处理 JSON-RPC 消息
├── handleNotification() 处理 notifications (session/update)
├── handleServerRequest()处理 requests (fs/read, fs/write, request_permission)
└── extractToolCalls()   从响应中提取 tool calls
```

## 协议

基于 JSON-RPC 2.0，通过 stdin/stdout 通信。

### Client → Server Requests

- `initialize` - 协商协议版本和能力
- `session/new` - 创建新 session
- `session/prompt` - 发送用户输入
- `session/cancel` - 取消当前操作

### Server → Client Notifications

- `session/update` - 响应文本片段

### Server → Client Requests

- `session/request_permission` - 审批请求（自动 approve）
- `fs/read_text_file` - 文件读取请求
- `fs/write_text_file` - 文件写入请求

## 与 OpenClaw 融合

### 方式 1: 新增 Tool

```typescript
// tools/acp_delegate.ts
import { acp_call } from 'openclaw-acp-client';

export async function acp_delegate(params) {
  return await acp_call(params.command, params.prompt, {
    cwd: params.cwd,
    timeout: params.timeout,
  });
}
```

### 方式 2: sessions_spawn 改造

```typescript
// 支持 runtime: "acp"
sessions_spawn({
  runtime: 'acp',
  agentId: 'claude', // ACP agent
  task: '分析代码',
});
```

## License

MIT