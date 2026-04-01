#!/usr/bin/env python3
"""
Kimi Remote API - 简单的 HTTP 封装
部署在远程服务器上，允许远程调用 kimi-cli
"""
from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

# 配置
KIMI_CMD = "/home/kyj/.local/bin/kimi-cli"  # kimi-cli 路径
DEFAULT_WORK_DIR = "/home/kyj/workspace"     # 默认工作目录

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "kimi-remote-api"})

@app.route('/chat', methods=['POST'])
def chat():
    """
    调用 kimi-cli
    
    JSON Body:
    {
        "prompt": "你的问题",
        "session": "会话 ID (可选，默认 default)",
        "work_dir": "工作目录 (可选)"
    }
    """
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Missing 'prompt' field"}), 400
    
    prompt = data['prompt']
    session = data.get('session', 'default')
    work_dir = data.get('work_dir', DEFAULT_WORK_DIR)
    
    try:
        # 构建命令
        cmd = [
            KIMI_CMD,
            '-S', session,
            '-w', work_dir,
            prompt
        ]
        
        # 执行命令（设置超时）
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 分钟超时
        )
        
        return jsonify({
            "success": True,
            "response": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "returncode": result.returncode
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "error": "Command timed out (5 minutes)"
        }), 504
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/execute', methods=['POST'])
def execute():
    """
    执行任意 shell 命令（需要认证）
    
    JSON Body:
    {
        "command": "shell 命令",
        "auth_token": "认证令牌"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    
    # 简单认证（实际使用请用更好的方式）
    auth_token = data.get('auth_token')
    expected_token = os.environ.get('KIMI_API_TOKEN', 'change-me')
    
    if auth_token != expected_token:
        return jsonify({"error": "Unauthorized"}), 401
    
    command = data.get('command')
    if not command:
        return jsonify({"error": "Missing 'command' field"}), 400
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return jsonify({
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # 生成默认 token
    import secrets
    default_token = secrets.token_urlsafe(16)
    print(f"\n🔑 默认 API Token: {default_token}")
    print(f"   设置方式：export KIMI_API_TOKEN='{default_token}'\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
