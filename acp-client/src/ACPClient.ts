/**
 * ACP Client - OpenClaw 调用外部 ACP Agent
 * 
 * 实现 JSON-RPC 2.0 协议，通过 stdin/stdout 与外部 agent 通信。
 * 支持：Claude Code、Codex、Copilot、Hermes 等 ACP agent。
 */

import { spawn, ChildProcess } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// Type Definitions
// ============================================================================

interface ACPConfig {
  command: string;          // ACP agent 命令，如 "claude", "codex", "copilot"
  args: string[];           // ACP 参数，默认 ["--acp", "--stdio"]
  cwd: string;              // 工作目录
  timeout: number;          // 超时秒数
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
  id?: number;  // requests have id, notifications don't
}

interface ToolCall {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments: string;
  };
}

interface ACPResult {
  text: string;
  reasoning?: string;
  toolCalls: ToolCall[];
}

// ============================================================================
// ACPClient Class
// ============================================================================

export class ACPClient {
  private process: ChildProcess | null = null;
  private requestId = 0;
  private pendingRequests: Map<number, { 
    resolve: (value: any) => void; 
    reject: (error: Error) => void;
    timeout?: NodeJS.Timeout;
  }> = new Map();
  
  private textParts: string[] = [];
  private reasoningParts: string[] = [];
  private buffer = '';
  private sessionId: string | null = null;

  constructor(private config: ACPConfig) {}

  /**
   * 启动 ACP agent subprocess
   */
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
      this.cleanup();
    });

    this.process.on('error', (err) => {
      console.error('[ACP] process error:', err);
      this.cleanup();
    });
  }

  /**
   * 处理 stdout buffer，解析 JSON-RPC 消息
   */
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

  /**
   * 处理 JSON-RPC 消息
   */
  private handleMessage(msg: JSONRPCResponse | JSONRPCNotification): void {
    // 判断是 request 还是 notification
    const hasId = 'id' in msg && msg.id !== undefined && msg.id !== null;
    
    // 如果有 method 但没有 id，是 notification
    if ('method' in msg && !hasId) {
      this.handleNotification(msg as JSONRPCNotification);
      return;
    }

    // 如果有 id，是 response 或 request from server
    if (hasId) {
      const id = msg.id as number;
      
      // 检查是否是我们发送的 request 的 response
      const pending = this.pendingRequests.get(id);
      if (pending) {
        // 这是我们发送的 request 的 response
        this.pendingRequests.delete(id);
        if (pending.timeout) clearTimeout(pending.timeout);
        
        const resp = msg as JSONRPCResponse;
        if (resp.error) {
          pending.reject(new Error(resp.error.message));
        } else {
          pending.resolve(resp.result);
        }
        return;
      }

      // 这是 server 发来的 request（如 fs/read_text_file）
      if ('method' in msg) {
        this.handleServerRequest(msg as JSONRPCNotification & { id: number });
        return;
      }
    }

    console.debug('[ACP] unknown message:', msg);
  }

  /**
   * 处理 notification（server 发来的事件通知）
   */
  private handleNotification(msg: JSONRPCNotification): void {
    const method = msg.method;
    const params = msg.params || {};

    // session/update - 收集响应文本
    if (method === 'session/update') {
      const update = params.update || params;
      const kind = update.sessionUpdate || update.kind;
      const content = update.content || {};

      if (kind === 'agent_message_chunk') {
        const text = content.text || '';
        this.textParts.push(text);
      } else if (kind === 'agent_thought_chunk' || kind === 'reasoning_chunk') {
        const text = content.text || '';
        this.reasoningParts.push(text);
      }
      return;
    }

    // 其他 notification
    console.debug('[ACP] notification:', method, params);
  }

  /**
   * 处理 server request（需要响应）
   */
  private handleServerRequest(msg: JSONRPCNotification & { id: number }): void {
    const method = msg.method;
    const params = msg.params || {};
    const id = msg.id;

    // session/request_permission - 自动 approve
    if (method === 'session/request_permission') {
      this.sendResponse(id, { outcome: { outcome: 'allow_once' } });
      return;
    }

    // fs/read_text_file - 处理文件读取请求
    if (method === 'fs/read_text_file') {
      this.handleFileRead(id, params);
      return;
    }

    // fs/write_text_file - 处理文件写入请求
    if (method === 'fs/write_text_file') {
      this.handleFileWrite(id, params);
      return;
    }

    // 其他方法 - 暂不支持
    this.sendError(id, -32601, `Method '${method}' not supported`);
  }

  /**
   * 处理文件读取请求
   */
  private handleFileRead(id: number, params: Record<string, any>): void {
    const filePath = params.path;
    if (!filePath) {
      this.sendError(id, -32602, 'Missing path parameter');
      return;
    }

    // 安全检查：确保路径在 cwd 内
    const resolvedPath = this.resolvePath(filePath);
    if (!resolvedPath) {
      this.sendError(id, -32602, `Path '${filePath}' is outside cwd or not absolute`);
      return;
    }

    try {
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

  /**
   * 处理文件写入请求
   */
  private handleFileWrite(id: number, params: Record<string, any>): void {
    const filePath = params.path;
    const content = params.content || '';

    if (!filePath) {
      this.sendError(id, -32602, 'Missing path parameter');
      return;
    }

    const resolvedPath = this.resolvePath(filePath);
    if (!resolvedPath) {
      this.sendError(id, -32602, `Path '${filePath}' is outside cwd or not absolute`);
      return;
    }

    try {
      const dir = path.dirname(resolvedPath);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(resolvedPath, content);
      this.sendResponse(id, null);
    } catch (e: any) {
      this.sendError(id, -32602, e.message);
    }
  }

  /**
   * 安全检查：确保路径在 cwd 内且为绝对路径
   */
  private resolvePath(filePath: string): string | null {
    // ACP 要求绝对路径
    if (!path.isAbsolute(filePath)) {
      return null;
    }

    const resolved = path.resolve(filePath);
    const cwdResolved = path.resolve(this.config.cwd);

    // 确保路径在 cwd 内
    if (!resolved.startsWith(cwdResolved)) {
      return null;
    }

    return resolved;
  }

  /**
   * 发送成功响应
   */
  private sendResponse(id: number, result: any): void {
    const response = {
      jsonrpc: '2.0',
      id,
      result,
    };
    this.send(JSON.stringify(response));
  }

  /**
   * 发送错误响应
   */
  private sendError(id: number, code: number, message: string): void {
    const response = {
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
      throw new Error('ACP process not running');
    }
    this.process.stdin.write(data + '\n');
  }

  /**
   * 发送 request 并等待 response
   */
  private async request(method: string, params: Record<string, any>): Promise<any> {
    const id = ++this.requestId;
    const request: JSONRPCRequest = {
      jsonrpc: '2.0',
      id,
      method,
      params,
    };

    return new Promise((resolve, reject) => {
      // 设置超时
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
   * initialize - ACP handshake
   */
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

  /**
   * 创建新的 session
   */
  async createSession(): Promise<string> {
    const result = await this.request('session/new', {
      cwd: this.config.cwd,
      mcpServers: [], // 可选：传递 MCP servers
    });

    const sessionId = result?.sessionId;
    if (!sessionId) {
      throw new Error('ACP agent did not return sessionId');
    }

    this.sessionId = sessionId;
    return sessionId;
  }

  /**
   * 发送 prompt 并收集响应
   */
  async sendPrompt(prompt: string): Promise<ACPResult> {
    if (!this.sessionId) {
      throw new Error('Session not created. Call createSession() first.');
    }

    // 清空收集的 parts
    this.textParts = [];
    this.reasoningParts = [];

    // 发送 prompt
    await this.request('session/prompt', {
      sessionId: this.sessionId,
      prompt: [
        {
          type: 'text',
          text: prompt,
        },
      ],
    });

    // 提取 tool calls
    const text = this.textParts.join('');
    const reasoning = this.reasoningParts.join('');
    const toolCalls = this.extractToolCalls(text);

    return {
      text,
      reasoning,
      toolCalls,
    };
  }

  /**
   * 从响应文本中提取 tool calls
   * ACP agent 可能使用 <tool_call>{...}.getTag() 格式输出 tool calls
   */
  extractToolCalls(text: string): ToolCall[] {
    // 匹配 ACP agent 输出的 tool call 格式（如 <tool_call>{...}.getTag()）
    // 注意：不同 agent 的格式可能不同，这里使用通用匹配
    const regex = /\{\s*"type"\s*:\s*"function"[^}]+\}/gs;
    const toolCalls: ToolCall[] = [];

    for (const match of text.matchAll(regex)) {
      try {
        const jsonStr = match[1];
        const obj = JSON.parse(jsonStr);

        if (obj.type === 'function' && obj.function?.name) {
          toolCalls.push({
            id: obj.id || `acp_${toolCalls.length + 1}`,
            type: 'function',
            function: {
              name: obj.function.name,
              arguments: obj.function.arguments || '{}',
            },
          });
        }
      } catch (e) {
        // invalid JSON, skip
      }
    }

    return toolCalls;
  }

  /**
   * 取消当前 session
   */
  async cancel(): Promise<void> {
    if (!this.sessionId) return;

    try {
      await this.request('session/cancel', {
        sessionId: this.sessionId,
      });
    } catch (e) {
      // ignore errors on cancel
    }
  }

  /**
   * 关闭 ACP agent
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
      pending.reject(new Error('ACP process closed'));
    }
    this.pendingRequests.clear();
    this.sessionId = null;
  }
}

// ============================================================================
// Convenience Function
// ============================================================================

/**
 * 快速调用外部 ACP agent
 */
export async function acp_call(
  command: string,
  prompt: string,
  options: {
    args?: string[];
    cwd?: string;
    timeout?: number;
  } = {}
): Promise<ACPResult> {
  const client = new ACPClient({
    command,
    args: options.args || ['--acp', '--stdio'],
    cwd: options.cwd || process.cwd(),
    timeout: options.timeout || 300,
  });

  try {
    await client.start();
    await client.initialize();
    await client.createSession();
    const result = await client.sendPrompt(prompt);
    client.close();
    return result;
  } catch (e) {
    client.close();
    throw e;
  }
}
