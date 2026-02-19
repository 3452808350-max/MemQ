"""
Kimi API 封装
"""
import os
import requests

KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "sk-uavwLygbmyn30unU85N3dxH0WofJyyCUoiS9mlzdPsllqSR6")
KIMI_BASE_URL = "https://api.moonshot.cn/v1"

def chat(prompt, model="kimi-latest", max_tokens=2000, timeout=180):
    """调用Kimi API
    
    Args:
        prompt: 输入提示
        model: 模型名称 (默认kimi-latest)
        max_tokens: 最大生成token数
        timeout: 超时时间(秒)，默认180秒
    """
    url = f"{KIMI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }
    
    resp = requests.post(url, headers=headers, json=data, timeout=timeout)
    resp.raise_for_status()
    result = resp.json()
    return result["choices"][0]["message"]["content"]

if __name__ == "__main__":
    # 测试
    print("测试Kimi API...")
    result = chat("用50字介绍FinRL框架")
    print(result)
