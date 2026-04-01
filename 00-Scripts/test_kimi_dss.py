#!/usr/bin/env python3
"""
DSS Kimi集成测试
测试Wire模式 + Agent配置
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

print("="*60)
print("DSS Kimi集成测试")
print("="*60)

# 测试1: 简单Print模式
print("\n【测试1: Print模式 - 简单问题】")
print("-"*50)

from kimi_runner import run_kimi_task
result1 = run_kimi_task("1+1等于几？只回答数字")

if result1['success']:
    print(f"回答: {result1['output']}")
    print(f"Token: {result1['token_usage']}")
else:
    print(f"错误: {result1['error']}")

# 测试2: DSS分析任务
print("\n【测试2: DSS分析任务】")
print("-"*50)

dss_prompt = """
请用Python分析贵州茅台(sh.600519)的技术面：

1. 使用以下代码获取数据：
```python
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')
from dss_v4 import ImprovedStockPicker
picker = ImprovedStockPicker(use_denoise=True)
result = picker.analyze_stock('sh.600519')
print(result)
```

2. 简要解释技术评分的含义
"""

result2 = run_kimi_task(dss_prompt, timeout=120)

if result2['success']:
    print(result2['output'][:500])  # 只显示前500字符
    print(f"\n... (输出共{len(result2['output'])}字符)")
else:
    print(f"错误: {result2['error']}")

# 测试3: 使用Wire模式
print("\n【测试3: Wire模式测试】")
print("-"*50)

try:
    from kimi_wire import KimiWireClient
    
    with KimiWireClient() as client:
        result3 = client.prompt("用一句话解释什么是MACD指标", timeout=60)
        
        print(f"回答: {result3.text}")
        if result3.thoughts:
            print(f"思考过程: {result3.thoughts[0][:100]}...")
        print(f"状态: {result3.status}")
except Exception as e:
    print(f"Wire模式错误: {e}")
    print("回退到Print模式...")

print("\n" + "="*60)
print("测试完成!")
print("="*60)