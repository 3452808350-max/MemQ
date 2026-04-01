"""
Kimi API 封装 v2
支持上下文管理和会话隔离
"""
import os
import requests
from typing import List, Optional

KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "sk-uavwLygbmyn30unU85N3dxH0WofJyyCUoiS9mlzdPsllqSR6")
KIMI_BASE_URL = "https://api.moonshot.cn/v1"

class KimiSession:
    """Kimi会话管理"""
    
    def __init__(self, model: str = "kimi-k2.5", system_prompt: str = None):
        self.model = model
        self.messages = []
        
        # 添加系统提示
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
    
    def chat(self, prompt: str, max_tokens: int = 2000) -> str:
        """发送对话"""
        # 添加用户消息
        self.messages.append({"role": "user", "content": prompt})
        
        url = f"{KIMI_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {KIMI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # 计算上下文大小
        total_chars = sum(len(m["content"]) for m in self.messages)
        
        # 如果上下文太大，截断历史
        max_chars = 50000  # 约10K tokens
        while total_chars > max_chars and len(self.messages) > 1:
            # 保留系统消息和最近的消息
            self.messages = [self.messages[0]] + self.messages[-2:]
            total_chars = sum(len(m["content"]) for m in self.messages)
        
        data = {
            "model": self.model,
            "messages": self.messages,
            "max_tokens": max_tokens
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=180)
            resp.raise_for_status()
            result = resp.json()
            
            # 添加助手回复
            reply = result["choices"][0]["message"]["content"]
            self.messages.append({"role": "assistant", "content": reply})
            
            return reply
            
        except requests.exceptions.HTTPError as e:
            error = e.response.json()
            error_msg = error.get("error", {}).get("message", str(e))
            
            # 如果是上下文溢出，尝试清理后重试
            if "context" in error_msg.lower():
                self.messages = self.messages[-4:]  # 只保留最近4条
                return self.chat(prompt, max_tokens)
            
            return f"错误: {error_msg}"
    
    def clear(self):
        """清理会话历史"""
        if len(self.messages) > 0 and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []
    
    def history(self) -> List[dict]:
        """获取会话历史"""
        return self.messages


def chat(prompt, model: str = "kimi-k2.5", max_tokens: int = 2000, timeout: int = 180):
    """快捷调用 - 每次新建会话"""
    session = KimiSession(model=model)
    return session.chat(prompt, max_tokens)


# ============ 测试 ============

if __name__ == "__main__":
    print("测试Kimi API...")
    
    # 简单测试
    session = KimiSession()
    result = session.chat("用50字介绍DSS选股系统")
    print(result[:200])
