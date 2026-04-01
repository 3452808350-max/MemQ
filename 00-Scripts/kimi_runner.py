#!/usr/bin/env python3
"""
Kimi CLI Runner - 让OpenClaw子任务使用Kimi额度

使用方式:
    python kimi_runner.py "你的任务描述"
    
或作为模块:
    from kimi_runner import run_kimi_task
    result = run_kimi_task("分析这段代码")
"""
import subprocess
import sys
import json
import re
from typing import Optional, Dict, Any


def run_kimi_task(
    prompt: str,
    work_dir: str = None,
    timeout: int = 300,
    thinking: bool = True,
    yolo: bool = True
) -> Dict[str, Any]:
    """
    运行Kimi CLI任务
    
    Args:
        prompt: 任务描述
        work_dir: 工作目录
        timeout: 超时时间(秒)
        thinking: 是否启用思考模式
        yolo: 是否自动确认所有操作
        
    Returns:
        {
            'success': bool,
            'output': str,
            'error': str,
            'token_usage': dict
        }
    """
    cmd = ['kimi', '-p', prompt, '--print']
    
    if thinking:
        cmd.append('--thinking')
    
    if yolo:
        cmd.append('--yolo')
    
    if work_dir:
        cmd.extend(['-w', work_dir])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=work_dir
        )
        
        output = result.stdout
        error = result.stderr
        
        # 解析token使用情况
        token_usage = {}
        usage_match = re.search(r'token_usage=TokenUsage\(([^)]+)\)', output)
        if usage_match:
            usage_str = usage_match.group(1)
            for match in re.finditer(r'(\w+)=(\d+)', usage_str):
                token_usage[match.group(1)] = int(match.group(2))
        
        # 提取实际回复内容
        text_parts = re.findall(r"text='([^']*)'", output)
        clean_output = '\n'.join(text_parts) if text_parts else output
        
        return {
            'success': result.returncode == 0,
            'output': clean_output,
            'raw_output': output,
            'error': error,
            'token_usage': token_usage
        }
        
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': '',
            'error': f'Timeout after {timeout} seconds',
            'token_usage': {}
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'token_usage': {}
        }


def run_kimi_code_review(file_path: str) -> Dict[str, Any]:
    """用Kimi进行代码审查"""
    prompt = f"""请审查这个代码文件: {file_path}

重点关注:
1. 代码质量和可读性
2. 潜在的bug或问题
3. 性能优化建议
4. 安全性问题

请给出具体的改进建议。"""
    
    return run_kimi_task(prompt, work_dir='/home/kyj/.openclaw/workspace')


def run_kimi_analysis(task: str, context: str = None) -> Dict[str, Any]:
    """用Kimi进行分析任务"""
    full_prompt = task
    if context:
        full_prompt = f"{task}\n\n上下文:\n{context}"
    
    return run_kimi_task(full_prompt)


# 命令行入口
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python kimi_runner.py \"你的任务\"")
        sys.exit(1)
    
    prompt = sys.argv[1]
    result = run_kimi_task(prompt)
    
    if result['success']:
        print(result['output'])
        if result['token_usage']:
            print(f"\n--- Token使用: {result['token_usage']} ---", file=sys.stderr)
    else:
        print(f"错误: {result['error']}", file=sys.stderr)
        sys.exit(1)