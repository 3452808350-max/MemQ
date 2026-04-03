/**
 * Claude Plugin - Command Handlers
 * 
 * 处理 /coordinator、/fork 等命令
 */

import { runCoordinatorMode, runForkMode, runWithAgent, OpenClawContext } from './openclaw-bridge';

// 命令解析结果
interface ParsedCommand {
  command: string;
  args: string;
  options: Record<string, string | boolean>;
}

/**
 * 解析用户输入的命令
 */
export function parseCommand(input: string): ParsedCommand | null {
  // 匹配 /command 或 @command 格式
  const match = input.match(/^(?:\/|@)(\w+)(?:\s+(.+))?$/s);
  
  if (!match) return null;
  
  const [, command, args = ''] = match;
  
  // 解析选项 (--key value 或 --flag)
  const options: Record<string, string | boolean> = {};
  const optionRegex = /--(\w+)(?:\s+(\S+))?/g;
  let optionMatch;
  
  while ((optionMatch = optionRegex.exec(args)) !== null) {
    const [, key, value] = optionMatch;
    options[key] = value || true;
  }
  
  // 移除选项后的纯参数
  const cleanArgs = args.replace(optionRegex, '').trim();
  
  return {
    command: command.toLowerCase(),
    args: cleanArgs,
    options
  };
}

/**
 * 处理 /coordinator 命令
 */
export async function handleCoordinatorCommand(
  args: string,
  options: Record<string, string | boolean>,
  context: OpenClawContext
): Promise<string> {
  if (!args.trim()) {
    return `❌ 请提供任务描述

用法: /coordinator <任务描述> [--max-workers 4] [--timeout 300] [--no-verify]`;
  }
  
  const config = {
    maxParallelWorkers: parseInt(options['max-workers'] as string) || 4,
    defaultTimeoutMs: (parseInt(options['timeout'] as string) || 300) * 1000,
    enableVerification: options['no-verify'] !== true
  };
  
  try {
    const result = await runCoordinatorMode(args, context, config);
    return result;
  } catch (error) {
    return `❌ Coordinator Mode 执行失败: ${error instanceof Error ? error.message : String(error)}`;
  }
}

/**
 * 处理 /fork 命令
 */
export async function handleForkCommand(
  args: string,
  context: OpenClawContext
): Promise<string> {
  if (!args.trim()) {
    return `❌ 请提供任务列表

用法: /fork <任务1>; <任务2>; <任务3>

示例:
/fork 调查认证流程; 分析会话管理; 检查权限控制`;
  }
  
  // 按分号或换行分割任务
  const tasks = args
    .split(/[;\n]/)
    .map(t => t.trim())
    .filter(t => t.length > 0);
  
  if (tasks.length === 0) {
    return '❌ 未找到有效任务';
  }
  
  if (tasks.length === 1) {
    return '⚠️ 只有一个任务，建议直接使用 /coordinator 或普通对话';
  }
  
  try {
    const results = await runForkMode(tasks, context);
    
    return formatForkResults(results);
  } catch (error) {
    return `❌ Fork 执行失败: ${error instanceof Error ? error.message : String(error)}`;
  }
}

/**
 * 处理 /agent 命令（使用特定 Agent）
 */
export async function handleAgentCommand(
  args: string,
  context: OpenClawContext
): Promise<string> {
  const match = args.match(/^(\w+)\s+(.+)$/s);
  
  if (!match) {
    return `❌ 请指定 Agent 名称和任务

用法: /agent <agent-name> <任务>

可用 Agents:
- code-explorer: 代码库探索
- code-planner: 架构规划
- implementer: 代码实现
- verifier: 验证测试

示例:
/agent code-explorer 调查 src/auth 目录`;
  }
  
  const [, agentName, task] = match;
  
  try {
    const result = await runWithAgent(agentName, task, context);
    return result;
  } catch (error) {
    return `❌ Agent 执行失败: ${error instanceof Error ? error.message : String(error)}`;
  }
}

/**
 * 处理 /claude 命令（通用入口）
 */
export async function handleClaudeCommand(
  args: string,
  context: OpenClawContext
): Promise<string> {
  if (!args.trim()) {
    return `Claude Plugin - 多 Agent 协调器

可用命令:
• /coordinator <任务> - 四阶段工作流（Research → Synthesis → Implementation → Verification）
• /fork <任务1>; <任务2> - 并行执行多个子任务
• /agent <name> <任务> - 使用特定 Agent 类型

示例:
/coordinator 实现 OAuth2 认证系统
/fork 调查 API 设计; 分析数据库模型; 检查安全需求
/agent code-explorer 探索项目结构`;
  }
  
  // 智能判断使用哪种模式
  if (args.includes(';') || args.includes('并行')) {
    return handleForkCommand(args, context);
  }
  
  // 默认使用 Coordinator
  return handleCoordinatorCommand(args, {}, context);
}

/**
 * 格式化 Fork 结果
 */
function formatForkResults(results: Array<{
  scope: string;
  result: string;
  keyFiles: string[];
  filesChanged: Array<{ path: string; commitHash?: string }>;
  issues: string[];
}>): string {
  const sections = results.map((r, i) => `
### 任务 ${i + 1}: ${r.scope}
**结果**: ${r.result}

**关键文件**: ${r.keyFiles.join(', ') || '无'}

**修改文件**: ${r.filesChanged.map(f => f.path).join(', ') || '无'}

**问题**: ${r.issues.join(', ') || '无'}
`).join('\n---\n');

  return `
# Fork 并行执行结果

${sections}

---
✅ 所有 ${results.length} 个任务执行完成
`;
}

/**
 * 主命令处理器
 */
export async function handleCommand(
  input: string,
  context: OpenClawContext
): Promise<string | null> {
  const parsed = parseCommand(input);
  
  if (!parsed) return null;
  
  switch (parsed.command) {
    case 'coordinator':
    case 'coord':
      return handleCoordinatorCommand(parsed.args, parsed.options, context);
    
    case 'fork':
      return handleForkCommand(parsed.args, context);
    
    case 'agent':
      return handleAgentCommand(parsed.args, context);
    
    case 'claude':
    case 'claude-plugin':
      return handleClaudeCommand(parsed.args, context);
    
    default:
      return null; // 不处理的命令
  }
}

/**
 * 检查输入是否是 Claude Plugin 命令
 */
export function isClaudePluginCommand(input: string): boolean {
  const parsed = parseCommand(input);
  if (!parsed) return false;
  
  return ['coordinator', 'coord', 'fork', 'agent', 'claude', 'claude-plugin'].includes(parsed.command);
}

// 导出
export { ParsedCommand };
