/**
 * Wire Client - OpenClaw 调用 Kimi CLI
 * 
 * 实现 Wire 协议 1.7，通过 stdin/stdout JSON-RPC 2.0 通信。
 * 支持 Kimi Code CLI 的所有功能：prompt, steer, cancel, replay, plan mode。
 */

import { spawn, ChildProcess } from 'child_process';
import { randomUUID } from 'crypto';

// ============================================================================
// Type Definitions (Wire Protocol 1.7)
// ============================================================================

/** JSON-RPC 2.0 请求 */
interface JSONRPCRequest<Method extends string, Params> {
  jsonrpc: "2.0";
  method: Method;
  id: string;
  params: Params;
}

/** JSON-RPC 2.0 通知 */
interface JSONRPCNotification<Method extends string, Params> {
  jsonrpc: "2.0";
  method: Method;
  params: Params;
}

/** JSON-RPC 2.0 成功响应 */
interface JSONRPCSuccessResponse<Result> {
  jsonrpc: "2.0";
  id: string;
  result: Result;
}

/** JSON-RPC 2.0 错误响应 */
interface JSONRPCErrorResponse {
  jsonrpc: "2.0";
  id: string;
  error: {
    code: number;
    message: string;
    data?: unknown;
  };
}

type JSONRPCMessage = JSONRPCRequest<string, any> | JSONRPCNotification<string, any> | JSONRPCSuccessResponse<any> | JSONRPCErrorResponse;

// Wire Protocol Types

interface WireConfig {
  command: string;          // kimi 命令
  args: string[];           // [--wire]
  cwd: string;              // 工作目录
  timeout: number;          // 超时秒数
}

interface InitializeParams {
  protocol_version: string;
  client?: { name: string; version?: string };
  external_tools?: ExternalTool[];
  capabilities?: { supports_question?: boolean; supports_plan_mode?: boolean };
  hooks?: WireHookSubscription[];
}

interface InitializeResult {
  protocol_version: string;
  server: { name: string; version: string };
  slash_commands: SlashCommandInfo[];
  external_tools?: { accepted: string[]; rejected: Array<{ name: string; reason: string }> };
  capabilities?: { supports_question?: boolean };
}

interface ExternalTool {
  name: string;
  description: string;
  parameters: any; // JSON Schema
}

interface WireHookSubscription {
  id: string;
  event: string;
  matcher?: string;
  timeout?: number;
}

interface SlashCommandInfo {
  name: string;
  description: string;
  aliases: string[];
}

interface PromptParams {
  user_input: string | ContentPart[];
}

interface PromptResult {
  status: "finished" | "cancelled" | "max_steps_reached";
  steps?: number;
}

interface ContentPart {
  type: "text" | "image";
  text?: string;
  source?: { type: "base64"; media_type: string; data: string };
}

interface SteerParams {
  user_input: string | ContentPart[];
}

interface SteerResult {
  status: "steered";
}

interface EventParams {
  type: string;
  payload: any;
}

interface RequestParams {
  type: "ApprovalRequest" | "ToolCallRequest" | "QuestionRequest" | "HookRequest";
  payload: any;
}

interface ApprovalRequest {
  id: string;
  tool_call_id: string;
  sender: string;
  action: string;
  description: string;
  display: any[];
}

interface ApprovalResponse {
  outcome: "approve" | "reject" | "force_approve";
}

interface WireResult {
  text: string;
  reasoning?: string;
  events: EventParams[];
  status: "finished" | "cancelled" | "max_steps_reached";
}

// ============================================================================
// WireClient Class
// ============================================================================

export class WireClient {
  private process: ChildProcess | null = null;
  private pendingRequests: Map<string, {
    resolve: (value: any) => void;
    reject: (error: Error) => void;
    timeout?: NodeJS.Timeout;
  }> = new Map();

  private events: EventParams[] = [];
  private textParts: string[] = [];
  private reasoningParts: string[] = [];
  private buffer = '';
  private initialized = false;
  private serverCapabilities: InitializeResult | null = null;

  constructor(private config: WireConfig) {}

  /**
   * 启动 Kimi CLI subprocess
   */
  async start(): Promise<void> {
    this.process = spawn(this.config.command, this.config.args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: this.config.cwd,
    });

    if (!this.process.stdin || !this.process.stdout) {
      throw new Error('Wire process did not expose stdin/stdout');
    }

    this.process.stdout.on('data', (data: Buffer) => {
      this.buffer += data.toString();
      this.processBuffer();
    });

    this.process.stderr?.on('data', (data: Buffer) => {
      console.debug('[Wire stderr]', data.toString());
    });

    this.process.on('close', (code) => {
      console.debug('[Wire] process exited with code', code);
      this.cleanup();
    });

    this.process.on('error', (err) => {
      console.error('[Wire] process error:', err);
      this.cleanup();
    });
  }

  /**
   * 处理 stdout buffer，解析 JSON-RPC 消息
   */
  private processBuffer(): void {
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        this.handleMessage(msg);
      } catch (e) {
        console.debug('[Wire] non-JSON line:', line);
      }
    }
  }

  /**
   * 处理 JSON-RPC 消息
   */
  private handleMessage(msg: JSONRPCMessage): void {
    // 检查是否是 response（有 id 且无 method）
    if ('id' in msg && !('method' in msg)) {
      const pending = this.pendingRequests.get(msg.id);
      if (pending) {
        this.pendingRequests.delete(msg.id);
        if (pending.timeout) clearTimeout(pending.timeout);

        if ('error' in msg) {
          pending.reject(new Error(msg.error.message));
        } else {
          pending.resolve(msg.result);
        }
      }
      return;
    }

    // 检查是否是 notification（无 id）
    if ('method' in msg && !('id' in msg)) {
      this.handleNotification(msg as JSONRPCNotification<string, any>);
      return;
    }

    // 检查是否是 server request（有 id 和 method）
    if ('id' in msg && 'method' in msg) {
      this.handleServerRequest(msg as JSONRPCRequest<string, any>);
      return;
    }

    console.debug('[Wire] unknown message:', msg);
  }

  /**
   * 处理 notification（event）
   */
  private handleNotification(msg: JSONRPCNotification<string, any>): void {
    if (msg.method === 'event') {
      const params = msg.params as EventParams;
      this.events.push(params);

      // 收集文本内容
      if (params.type === 'ContentPart' && params.payload?.type === 'text') {
        this.textParts.push(params.payload.text || '');
      }

      // 收集 reasoning（如果有）
      if (params.type === 'ReasoningPart' || params.type === 'ThinkingPart') {
        this.reasoningParts.push(params.payload?.text || '');
      }

      console.debug('[Wire] event:', params.type);
      return;
    }

    console.debug('[Wire] notification:', msg.method);
  }

  /**
   * 处理 server request（需要响应）
   */
  private handleServerRequest(msg: JSONRPCRequest<string, any>): void {
    const method = msg.method;
    const params = msg.params as RequestParams;
    const id = msg.id;

    if (method === 'request') {
      const type = params.type;
      const payload = params.payload;

      // ApprovalRequest - 自动 approve
      if (type === 'ApprovalRequest') {
        console.debug('[Wire] auto-approving:', payload.action);
        this.sendResponse(id, { outcome: 'approve' });
        return;
      }

      // ToolCallRequest - 调用外部工具
      if (type === 'ToolCallRequest') {
        console.debug('[Wire] tool call request:', payload);
        // 默认拒绝（外部工具未实现）
        this.sendResponse(id, { outcome: 'reject' });
        return;
      }

      // QuestionRequest - 返回空回答
      if (type === 'QuestionRequest') {
        console.debug('[Wire] question request:', payload);
        this.sendResponse(id, { answer: '' });
        return;
      }

      // HookRequest - 返回 continue
      if (type === 'HookRequest') {
        console.debug('[Wire] hook request:', payload);
        this.sendResponse(id, { decision: 'continue' });
        return;
      }
    }

    // 其他方法不支持
    this.sendError(id, -32601, `Method '${method}' not supported`);
  }

  /**
   * 发送成功响应
   */
  private sendResponse(id: string, result: any): void {
    const response: JSONRPCSuccessResponse<any> = {
      jsonrpc: '2.0',
      id,
      result,
    };
    this.send(JSON.stringify(response));
  }

  /**
   * 发送错误响应
   */
  private sendError(id: string, code: number, message: string): void {
    const response: JSONRPCErrorResponse = {
      jsonrpc: '2.0',
      id,
      error: { code, message },
    };
    this.send(JSON.stringify(response));
  }

  /**
   * 发送原始数据到 stdin
   */
  private send(data: string): void {
    if (!this.process?.stdin) {
      throw new Error('Wire process not running');
    }
    this.process.stdin.write(data + '\n');
  }

  /**
   * 发送 request 并等待 response
   */
  private async request<P, R>(method: string, params: P): Promise<R> {
    const id = randomUUID();
    const request = {
      jsonrpc: '2.0',
      method,
      id,
      params,
    };

    return new Promise<R>((resolve, reject) => {
      const timeout = setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error(`Timeout waiting for response to ${method}`));
        }
      }, this.config.timeout * 1000);

      this.pendingRequests.set(id, { resolve, reject, timeout });
      this.send(JSON.stringify(request));
    });
  }

  /**
   * initialize - Wire handshake (可选)
   */
  async initialize(options?: {
    clientName?: string;
    externalTools?: ExternalTool[];
    supportsQuestion?: boolean;
    supportsPlanMode?: boolean;
  }): Promise<InitializeResult> {
    const params: InitializeParams = {
      protocol_version: '1.7',
      client: {
        name: options?.clientName || 'openclaw',
        version: '1.0.0',
      },
      capabilities: {
        supports_question: options?.supportsQuestion ?? true,
        supports_plan_mode: options?.supportsPlanMode ?? false,
      },
      external_tools: options?.externalTools,
    };

    try {
      const result = await this.request<InitializeParams, InitializeResult>('initialize', params);
      this.initialized = true;
      this.serverCapabilities = result;
      return result;
    } catch (e: any) {
      // 如果 method not found，降级到无握手模式
      if (e.message.includes('method not found') || e.message.includes('-32601')) {
        console.debug('[Wire] initialize not supported, skipping handshake');
        this.initialized = true;
        return {
          protocol_version: '1.0',
          server: { name: 'Kimi CLI', version: 'unknown' },
          slash_commands: [],
        };
      }
      throw e;
    }
  }

  /**
   * 发送 prompt 并运行 Agent 轮次
   */
  async prompt(userInput: string): Promise<WireResult> {
    // 清空收集的数据
    this.events = [];
    this.textParts = [];
    this.reasoningParts = [];

    const result = await this.request<PromptParams, PromptResult>('prompt', {
      user_input: userInput,
    });

    return {
      text: this.textParts.join(''),
      reasoning: this.reasoningParts.join(''),
      events: this.events,
      status: result.status,
    };
  }

  /**
   * steer - 在轮次进行中注入消息
   */
  async steer(userInput: string): Promise<SteerResult> {
    return await this.request<SteerParams, SteerResult>('steer', {
      user_input: userInput,
    });
  }

  /**
   * cancel - 取消当前轮次
   */
  async cancel(): Promise<void> {
    try {
      await this.request<{}, {}>('cancel', {});
    } catch (e: any) {
      // No turn in progress - ignore
      if (!e.message.includes('No agent turn')) {
        throw e;
      }
    }
  }

  /**
   * set_plan_mode - 设置 Plan 模式
   */
  async setPlanMode(enabled: boolean): Promise<{ status: 'ok'; plan_mode: boolean }> {
    return await this.request<{ enabled: boolean }, { status: 'ok'; plan_mode: boolean }>('set_plan_mode', { enabled });
  }

  /**
   * replay - 回放历史
   */
  async replay(): Promise<{ status: 'finished' | 'cancelled'; events: number; requests: number }> {
    return await this.request<{}, { status: 'finished' | 'cancelled'; events: number; requests: number }>('replay', {});
  }

  /**
   * 关闭 Kimi CLI
   */
  close(): void {
    if (this.process) {
      try {
        this.process.kill();
      } catch (e) {
        // ignore
      }
      this.process = null;
    }
    this.cleanup();
  }

  /**
   * 清理 pending requests
   */
  private cleanup(): void {
    for (const [id, pending] of this.pendingRequests) {
      if (pending.timeout) clearTimeout(pending.timeout);
      pending.reject(new Error('Wire process closed'));
    }
    this.pendingRequests.clear();
    this.initialized = false;
  }

  /**
   * 获取 server capabilities
   */
  getCapabilities(): InitializeResult | null {
    return this.serverCapabilities;
  }
}

// ============================================================================
// Convenience Function
// ============================================================================

/**
 * 快速调用 Kimi CLI
 */
export async function wire_call(
  prompt: string,
  options: {
    cwd?: string;
    timeout?: number;
    command?: string;
  } = {}
): Promise<WireResult> {
  const client = new WireClient({
    command: options.command || 'kimi',
    args: ['--wire'],
    cwd: options.cwd || process.cwd(),
    timeout: options.timeout || 300,
  });

  try {
    await client.start();
    await client.initialize();
    const result = await client.prompt(prompt);
    client.close();
    return result;
  } catch (e) {
    client.close();
    throw e;
  }
}