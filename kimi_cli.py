"""
Kimi Code CLI 本地替代方案
使用 Kimi API 实现类似 CLI 的功能
"""
import os
import sys
import requests
import json
import subprocess
from pathlib import Path

# Kimi API 配置
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "sk-uavwLygbmyn30unU85N3dxH0WofJyyCUoiS9mlzdPsllqSR6")
KIMI_API_BASE = "https://api.moonshot.cn/v1"

# 可用模型
MODELS = {
    "k2.5": "kimi-k2.5",
    "k2": "kimi-k2-turbo-preview", 
    "thinking": "kimi-k2-thinking",
    "fast": "kimi-k2-thinking-turbo",
}

DEFAULT_MODEL = "k2.5"


class KimiCode:
    """Kimi Code CLI 替代"""
    
    def __init__(self, api_key=None, model=DEFAULT_MODEL):
        self.api_key = api_key or KIMI_API_KEY
        self.model = MODELS.get(model, model)
        self.conversation = []
        
    def chat(self, message, system_prompt=None):
        """发送对话"""
        url = f"{KIMI_API_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation)
        messages.append({"role": "user", "content": message})
        
        data = {
            "model": self.model,
            "messages": messages
        }
        
        resp = requests.post(url, json=data, headers=headers, timeout=120)
        result = resp.json()
        
        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
            self.conversation.append({"role": "user", "content": message})
            self.conversation.append({"role": "assistant", "content": reply})
            return reply
        else:
            return f"错误: {result}"
    
    def read_file(self, path):
        """读取文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"读取失败: {e}"
    
    def write_file(self, path, content):
        """写入文件"""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"已写入: {path}"
        except Exception as e:
            return f"写入失败: {e}"
    
    def run_shell(self, cmd):
        """执行Shell命令"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, 
                text=True, timeout=60
            )
            output = result.stdout or result.stderr
            return output[:5000]  # 限制输出长度
        except Exception as e:
            return f"命令执行失败: {e}"
    
    def help(self):
        """帮助信息"""
        return """
Kimi Code CLI (本地替代版)

可用命令:
  /read <文件>     - 读取文件
  /write <文件> <内容> - 写入文件
  /run <命令>     - 执行Shell命令
  /ls [目录]      - 列出文件
  /clear          - 清除对话历史
  /help           - 显示帮助

直接输入文字即可对话
输入 /exit 退出
"""


def main():
    """主交互循环"""
    print("=" * 50)
    print("Kimi Code CLI (本地版)")
    print("=" * 50)
    print("输入 /help 查看命令")
    print()
    
    kimi = KimiCode()
    
    while True:
        try:
            user_input = input("kimi> ").strip()
            
            if not user_input:
                continue
                
            if user_input == "/exit":
                print("再见!")
                break
            
            if user_input == "/help":
                print(kimi.help())
                continue
            
            if user_input == "/clear":
                kimi.conversation = []
                print("对话已清除")
                continue
            
            # 处理命令
            if user_input.startswith("/read "):
                path = user_input[6:].strip()
                print(kimi.read_file(path))
                continue
            
            if user_input.startswith("/write "):
                parts = user_input[7:].split(" ", 1)
                if len(parts) == 2:
                    print(kimi.write_file(parts[0], parts[1]))
                else:
                    print("用法: /write <文件> <内容>")
                continue
            
            if user_input.startswith("/run "):
                cmd = user_input[5:]
                print(kimi.run_shell(cmd))
                continue
            
            if user_input.startswith("/ls"):
                path = user_input[4:].strip() or "."
                print(kimi.run_shell(f"ls -la {path}"))
                continue
            
            # 普通对话
            print("思考中...")
            response = kimi.chat(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n退出")
            break
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    main()
