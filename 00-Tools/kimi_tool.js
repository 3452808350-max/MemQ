#!/usr/bin/env node
/**
 * OpenClaw + Kimi CLI 集成工具
 * 
 * 使用方法:
 * openclaw kimi "任务描述"
 * openclaw kimi --project /path/to/project "任务描述"
 */

import { execSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 配置
const DEFAULT_WORKDIR = '/home/kyj/.openclaw/workspace';
const KIMI_CMD = 'kimi';
const TIMEOUT = 300; // 秒

/**
 * 检查 Kimi CLI 是否已安装
 */
function checkKimiInstalled() {
  try {
    execSync('which kimi', { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

/**
 * 获取 Kimi CLI 版本
 */
function getKimiVersion() {
  try {
    const version = execSync('kimi --version', { encoding: 'utf8' }).trim();
    return version;
  } catch {
    return 'unknown';
  }
}

/**
 * 执行 Kimi CLI 任务
 */
function executeKimiTask(task, options = {}) {
  const {
    workdir = DEFAULT_WORKDIR,
    timeout = TIMEOUT,
    interactive = false
  } = options;
  
  console.log('🚀 开始执行 Kimi 任务...\n');
  console.log(`📂 工作目录：${workdir}`);
  console.log(`📝 任务：${task}\n`);
  console.log('='.repeat(60));
  
  // 记录任务日志
  const logFile = join(workdir, 'kimi_tasks.log');
  const logEntry = {
    timestamp: new Date().toISOString(),
    task: task,
    status: 'running',
    workdir: workdir
  };
  
  fs.appendFileSync(logFile, JSON.stringify(logEntry, null, 2) + '\n');
  
  try {
    // 构建命令
    const cmd = interactive ? KIMI_CMD : `${KIMI_CMD} "${task.replace(/"/g, '\\"')}"`;
    
    // 执行
    const result = execSync(cmd, {
      cwd: workdir,
      encoding: 'utf8',
      timeout: timeout * 1000,
      stdio: 'inherit' // 直接输出到终端
    });
    
    // 记录完成
    logEntry.status = 'completed';
    fs.appendFileSync(logFile, JSON.stringify(logEntry, null, 2) + '\n');
    
    console.log('\n✅ 任务完成！');
    return { success: true, task };
    
  } catch (error) {
    if (error.killed) {
      logEntry.status = 'timeout';
      console.log(`\n⏰ 任务超时（${timeout}秒）`);
    } else {
      logEntry.status = 'failed';
      console.log(`\n❌ 任务失败：${error.message}`);
    }
    
    fs.appendFileSync(logFile, JSON.stringify(logEntry, null, 2) + '\n');
    return { success: false, error: error.message, task };
  }
}

/**
 * 初始化项目（生成 AGENTS.md）
 */
function initProject(workdir = DEFAULT_WORKDIR) {
  console.log('📋 初始化项目，生成 AGENTS.md...\n');
  return executeKimiTask('/init', { workdir, interactive: true });
}

/**
 * 主函数
 */
function main() {
  const args = process.argv.slice(2);
  
  // 解析参数
  const options = {
    workdir: DEFAULT_WORKDIR,
    timeout: TIMEOUT,
    interactive: false,
    init: false,
    status: false,
    task: null
  };
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === '--project' || arg === '-p') {
      options.workdir = args[++i];
    } else if (arg === '--timeout' || arg === '-t') {
      options.timeout = parseInt(args[++i]);
    } else if (arg === '--interactive' || arg === '-i') {
      options.interactive = true;
    } else if (arg === '--init') {
      options.init = true;
    } else if (arg === '--status') {
      options.status = true;
    } else if (!arg.startsWith('-')) {
      options.task = arg;
    }
  }
  
  // 检查 Kimi CLI
  if (!checkKimiInstalled()) {
    console.error('❌ Kimi CLI 未安装');
    console.error('请先运行：curl -LsSf https://code.kimi.com/install.sh | bash');
    process.exit(1);
  }
  
  // 执行命令
  if (options.status) {
    const version = getKimiVersion();
    console.log(`✅ Kimi CLI 版本：${version}`);
    process.exit(0);
  }
  
  if (options.init) {
    initProject(options.workdir);
    process.exit(0);
  }
  
  if (options.task) {
    const result = executeKimiTask(options.task, {
      workdir: options.workdir,
      timeout: options.timeout,
      interactive: options.interactive
    });
    process.exit(result.success ? 0 : 1);
  }
  
  // 显示帮助
  console.log(`
🔧 OpenClaw + Kimi CLI 集成工具

用法:
  openclaw kimi [选项] <任务描述>

选项:
  --project, -p <目录>   项目目录（默认：${DEFAULT_WORKDIR}）
  --timeout, -t <秒数>   超时时间（默认：${TIMEOUT}秒）
  --interactive, -i      交互式运行
  --init                 初始化项目（生成 AGENTS.md）
  --status               检查 Kimi CLI 状态

示例:
  openclaw kimi "帮我写一个 Python 函数"
  openclaw kimi -p /path/to/project "修复这个 bug"
  openclaw kimi --init
  openclaw kimi --status
`);
}

main();
