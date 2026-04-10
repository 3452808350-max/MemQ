# OpenClaw Wire Client

Wire Client for OpenClaw - 通过 Wire 协议 1.7 调用 Kimi CLI。

## 安装

```bash
npm install
npm run build
```

## 使用

### 快速调用

```typescript
import { wire_call } from 'openclaw-wire-client';

// 调用 Kimi CLI
const result = await wire_call('分析当前项目的架构', {
  cwd: '/path/to/project',
});

console.log(result.text);
```

### 完整控制

```typescript
import { WireClient } from 'openclaw-wire-client';

const client = new WireClient({
  command: 'kimi',
  args: ['--wire'],
  cwd: '/path/to/project',
  timeout: 300,
});

await client.start();
await client.initialize({
  clientName: 'openclaw',
  supportsQuestion: true,
});

const result = await client.prompt('帮我重构这个函数');
console.log(result.text);

// Plan 模式
await client.setPlanMode(true);

// 注入消息
await client.steer('用 Python 实现');

// 取消
await client.cancel();

client.close();
```

## Wire 协议

基于 JSON-RPC 2.0，通过 stdin/stdout 双向通信。协议版本 1.7。

### Client → Server Methods

| Method | 功能 |
|--------|------|
| `initialize` | 协议握手（可选） |
| `prompt` | 发送用户输入 |
| `steer` | 注入消息到当前轮次 |
| `cancel` | 取消当前轮次 |
| `set_plan_mode` | 设置 Plan 模式 |
| `replay` | 回放历史 |

### Server → Client Notifications

| Method | 功能 |
|--------|------|
| `event` | 事件通知（TurnBegin, ContentPart, StatusUpdate, TurnEnd 等） |

### Server → Client Requests

| Type | 功能 |
|------|------|
| `ApprovalRequest` | 审批确认 |
| `ToolCallRequest` | 外部工具调用 |
| `QuestionRequest` | 问题回答 |
| `HookRequest` | Hook 事件处理 |

## 测试

```bash
npm run test
```

需要安装 Kimi CLI：
```bash
pip install kimi-code-cli
# 或
npm install -g kimi-code-cli
```

## 与 OpenClaw 融合

### 方式 1: 新增 Tool

在 OpenClaw 工具目录新增 `wire_delegate` tool：

```typescript
// tools/wire_delegate.ts
import { WireClient } from 'openclaw-wire-client';

export async function wire_delegate(params) {
  const client = new WireClient({
    command: 'kimi',
    args: ['--wire'],
    cwd: params.cwd || process.cwd(),
    timeout: params.timeout || 300,
  });

  await client.start();
  await client.initialize();
  const result = await client.prompt(params.prompt);
  client.close();

  return {
    text: result.text,
    events: result.events,
    status: result.status,
  };
}
```

### 方式 2: sessions_spawn 改造

支持 `runtime: "wire"`：

```typescript
sessions_spawn({
  runtime: 'wire',
  task: '分析代码',
  cwd: '/path/to/project',
});
```

## 协议对比

| 协议 | Agent | 文档 | 文件系统 | Hooks | Plan Mode | Steer |
|------|-------|------|----------|-------|-----------|-------|
| **Wire** | Kimi CLI | 完整 v1.7 | ❌ | ✅ | ✅ | ✅ |
| **ACP** | Hermes/Codex | 源码分析 | ✅ | ❌ | ❌ | ❌ |

Wire 更适合 UI/自动化场景，ACP 更适合文件操作场景。

## License

MIT