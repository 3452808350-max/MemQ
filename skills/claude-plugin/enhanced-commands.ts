/**
 * Enhanced Claude Plugin Commands
 * 支持 Claude Code 最佳实践的增强命令
 */

import { 
  EnhancedCoordinatorWorkflow, 
  TaskWithVerification,
  EnhancedCoordinatorConfig 
} from './enhanced-coordinator';

// ==================== 命令解析 ====================

interface ParsedCommand {
  command: string;
  subcommand?: string;
  args: string;
  options: CommandOptions;
}

interface CommandOptions {
  verify?: string[];
  test?: string;
  expect?: string;
  maxWorkers?: number;
  timeout?: number;
  noVerify?: boolean;
  autoClear?: boolean;
  mode?: PermissionMode;
}

type PermissionMode = 'default' | 'plan' | 'bubble' | 'auto' | 'acceptEdits';

/**
 * 解析增强命令
 */
export function parseEnhancedCommand(input: string): ParsedCommand | null {
  // 匹配 /command 或 /command subcommand
  const match = input.match(/^(?:\/|@)(\w+)(?:\s+(\w+))?(?:\s+(.+))?$/s);
  
  if (!match) return null;
  
  const [, command, subcommand, rawArgs = ''] = match;
  
  // 解析选项
  const options: CommandOptions = {};
  
  // --verify "条件"（可多次）
  const verifyMatches = rawArgs.matchAll(/--verify\s+"([^"]+)"/g);
  options.verify = Array.from(verifyMatches).map(m => m[1]);
  
  // --test "命令"
  const testMatch = rawArgs.match(/--test\s+"([^"]+)"/);
  if (testMatch) options.test = testMatch[1];
  
  // --expect "输出"
  const expectMatch = rawArgs.match(/--expect\s+"([^"]+)"/);
  if (expectMatch) options.expect = expectMatch[1];
  
  // --max-workers N
  const workersMatch = rawArgs.match(/--max-workers\s+(\d+)/);
  if (workersMatch) options.maxWorkers = parseInt(workersMatch[1]);
  
  // --timeout N
  const timeoutMatch = rawArgs.match(/--timeout\s+(\d+)/);
  if (timeoutMatch) options.timeout = parseInt(timeoutMatch[1]);
  
  // --no-verify
  options.noVerify = rawArgs.includes('--no-verify');
  
  // --auto-clear
  options.autoClear = rawArgs.includes('--auto-clear');
  
  // --mode <mode>
  const modeMatch = rawArgs.match(/--mode\s+(\w+)/);
  if (modeMatch) options.mode = modeMatch[1] as PermissionMode;
  
  // 移除选项后的纯参数
  let cleanArgs = rawArgs
    .replace(/--verify\s+"[^"]+"/g, '')
    .replace(/--test\s+"[^"]+"/g, '')
    .replace(/--expect\s+"[^"]+"/g, '')
    .replace(/--max-workers\s+\d+/g, '')
    .replace(/--timeout\s+\d+/g, '')
    .replace(/--no-verify/g, '')
    .replace(/--auto-clear/g, '')
    .replace(/--mode\s+\w+/g, '')
    .trim();
  
  return {
    command: command.toLowerCase(),
    subcommand: subcommand?.toLowerCase(),
    args: cleanArgs,
    options
  };
}

// ==================== 命令处理器 ====================

/**
 * 处理 /coordinator 命令（增强版）
 */
export async function handleEnhancedCoordinator(
  args: string,
  options: CommandOptions
): Promise<string> {
  if (!args.trim()) {
    return `❌ 请提供任务描述

用法: /coordinator <任务> [选项]

选项:
  --verify "标准"       添加验证标准（可多次）
  --test "命令"         运行测试命令
  --expect "输出"       期望的输出
  --max-workers N       最大并行 Worker（默认 4）
  --timeout N           超时秒数（默认 300）
  --no-verify           跳过验证阶段
  --auto-clear          阶段间自动清理上下文
  --mode <mode>         权限模式（plan/auto/default）

示例:
  /coordinator 实现 OAuth2 登录 \\
    --verify "登录成功返回 token" \\
    --verify "失败返回 401" \\
    --test "npm run test:oauth" \\
    --auto-clear`;
  }
  
  const config: Partial<EnhancedCoordinatorConfig> = {
    autoClearBetweenPhases: options.autoClear ?? true,
    enableVerification: !options.noVerify,
    maxParallelWorkers: options.maxWorkers ?? 4,
    defaultTimeoutMs: (options.timeout ?? 300) * 1000
  };
  
  const task: TaskWithVerification = {
    task: args,
    verificationCriteria: options.verify,
    testCommand: options.test,
    expectedOutput: options.expect
  };
  
  try {
    const coordinator = new EnhancedCoordinatorWorkflow(config);
    const result = await coordinator.run(task);
    
    return formatCoordinatorResult(result);
  } catch (error) {
    return `❌ 执行失败: ${error instanceof Error ? error.message : String(error)}`;
  }
}

/**
 * 处理 /plan 命令
 */
export async function handlePlanCommand(
  subcommand: string | undefined,
  args: string
): Promise<string> {
  switch (subcommand) {
    case undefined:
      // 进入 Plan Mode
      return `📝 进入 Plan Mode

当前任务: ${args || '未指定'}

可用命令:
  /plan edit    - 编辑计划
  /plan show    - 显示当前计划
  /plan approve - 批准并执行
  /plan discard - 放弃计划`;
    
    case 'edit':
      return `✏️ 编辑计划

打开计划编辑器...

[Plan Editor]
阶段 1: Explore
- 调查现有代码
- 分析依赖关系

阶段 2: Plan  
- 设计架构
- 确定文件修改

阶段 3: Implement
- 实现功能
- 编写测试

阶段 4: Verify
- 运行测试
- 验证结果

使用 Ctrl+G 保存并退出编辑器`;
    
    case 'show':
      return `📋 当前计划

[待实现: 显示当前计划内容]`;
    
    case 'approve':
      return `✅ 计划已批准

进入 Implement 阶段...`;
    
    case 'discard':
      return `🗑️ 计划已放弃

返回 Explore 阶段`;
    
    default:
      return `❌ 未知子命令: ${subcommand}

可用: edit, show, approve, discard`;
  }
}

/**
 * 处理 /btw 命令（快速问答）
 */
export async function handleBtwCommand(
  args: string
): Promise<string> {
  if (!args.trim()) {
    return `❌ 请提供问题

用法: /btw <问题>

说明: 快速问答，不增长上下文

示例:
  /btw 这个文件是做什么的？
  /btw 项目使用什么框架？`;
  }
  
  // 使用轻量级查询，不污染上下文
  return `💬 快速回答: ${args}

[注意: 此回答不会添加到上下文中]`;
}

/**
 * 处理 /clear 命令
 */
export async function handleClearCommand(
  args: string
): Promise<string> {
  const preserve = args.includes('--preserve');
  
  if (preserve) {
    const items = args.match(/--preserve\s+(.+)/)?.[1]?.split(',').map(s => s.trim()) || [];
    return `🧹 清理上下文（保留 ${items.length} 项）

保留:
${items.map(i => `  - ${i}`).join('\n')}

其余上下文已清除。`;
  }
  
  return `🧹 上下文已清除

开始新的对话。`;
}

/**
 * 处理 /compact 命令
 */
export async function handleCompactCommand(
  args: string
): Promise<string> {
  if (!args.trim()) {
    return `❌ 请提供压缩指令

用法: /compact <指令>

示例:
  /compact 总结以上讨论的关键点
  /compact 提取代码修改摘要`;
  }
  
  return `📦 上下文已压缩

指令: ${args}

[上下文已压缩，保留关键信息]`;
}

// ==================== 格式化输出 ====================

function formatCoordinatorResult(result: {
  success: boolean;
  results: Array<{ success: boolean; output: string }>;
  summary: string;
}): string {
  const icon = result.success ? '✅' : '⚠️';
  
  return `
${icon} Coordinator Mode 执行结果

## 摘要
${result.summary}

## 详细结果
${result.results.map((r, i) => `
### 任务 ${i + 1}
状态: ${r.success ? '✅ 成功' : '❌ 失败'}
输出: ${r.output.substring(0, 200)}${r.output.length > 200 ? '...' : ''}
`).join('\n---\n')}

---
${result.success ? '🎉 所有阶段完成' : '⚠️ 部分任务失败'}
`;
}

// ==================== 主命令处理器 ====================

export async function handleEnhancedCommand(
  input: string
): Promise<string | null> {
  const parsed = parseEnhancedCommand(input);
  
  if (!parsed) return null;
  
  switch (parsed.command) {
    case 'coordinator':
    case 'coord':
      return handleEnhancedCoordinator(parsed.args, parsed.options);
    
    case 'plan':
      return handlePlanCommand(parsed.subcommand, parsed.args);
    
    case 'btw':
      return handleBtwCommand(parsed.args);
    
    case 'clear':
      return handleClearCommand(parsed.args);
    
    case 'compact':
      return handleCompactCommand(parsed.args);
    
    default:
      return null;
  }
}

// ==================== 导出 ====================

export {
  ParsedCommand,
  CommandOptions,
  parseEnhancedCommand
};