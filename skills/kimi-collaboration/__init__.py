"""
Kimi 协作模块
"""
import os
import requests

# API配置
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "sk-uavwLygbmyn30unU85N3dxH0WofJyyCUoiS9mlzdPsllqSR6")
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
DEFAULT_MODEL = "kimi-latest"

def chat(prompt, model=DEFAULT_MODEL, max_tokens=2000, timeout=180):
    """调用Kimi API
    
    Args:
        prompt: 输入提示
        model: 模型名称
        max_tokens: 最大生成token数
        timeout: 超时时间(秒)
    
    Returns:
        str: AI回复内容
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

# ============ 任务封装 ============

def kimi_chat(message: str, timeout: int = 60) -> str:
    """基础对话"""
    return chat(message, max_tokens=1500, timeout=timeout)

def kimi_finance(task: str, context: str = "", timeout: int = 180) -> str:
    """金融分析 [F-分析]"""
    prompt = f"""[F-分析] 金融分析任务

## 背景
{context}

## 任务
{task}

## 要求
- 中文回复
- 专业但易懂
- 如有数据请附上"""
    return chat(prompt, max_tokens=2000, timeout=timeout)

def kimi_paper(task: str, paper_info: str = "", timeout: int = 300) -> str:
    """论文讨论 [P-精读]"""
    prompt = f"""[P-精读] 论文精读讨论

## 论文信息
{paper_info}

## 讨论任务
{task}

## 要求
- 中文回复
- 详细深入
- 可以引用相关工作"""
    return chat(prompt, max_tokens=3000, timeout=timeout)

def kimi_code(task: str, code_context: str = "", timeout: int = 300) -> str:
    """代码开发 [C-开发]"""
    prompt = f"""[C-开发] 代码开发任务

## 代码上下文
```
{code_context}
```

## 开发任务
{task}

## 要求
- Python代码
- 简洁高效
- 包含文档字符串
- 可直接运行"""
    return chat(prompt, max_tokens=3000, timeout=timeout)

def kimi_review(code: str, timeout: int = 180) -> str:
    """代码审查 [R-审查]"""
    prompt = f"""[R-审查] 代码审查任务

## 代码
```
{code}
```

## 审查要点
1. 代码质量
2. 潜在问题
3. 改进建议

## 要求
- 中文回复
- 详细具体"""
    return chat(prompt, max_tokens=2000, timeout=timeout)

def kimi_summary(points: list, timeout: int = 120) -> str:
    """总结归纳 [S-总结]"""
    prompt = f"""[S-总结] 总结以下讨论要点：

{chr(10).join(f"- {p}" for p in points)}

## 要求
- 条理清晰
- 重点突出
- 中文回复"""
    return chat(prompt, max_tokens=1500, timeout=timeout)

# ============ 对话模板 ============

TASK_TEMPLATES = {
    "finance": """[F-分析] {task}

## 背景
{context}

请分析并给出建议。""",
    
    "paper": """[P-精读] {paper}

## 讨论要点
{task}

请详细分析。""",
    
    "code": """[C-开发] {task}

## 上下文
{context}

请实现代码。""",
    
    "review": """[R-审查] 请审查以下代码：

```
{code}
```

给出改进建议。""",
}

if __name__ == "__main__":
    # 测试
    print("测试 Kimi API...")
    result = kimi_chat("你好，请用一句话介绍自己")
    print(result)
