# DSS Kimi Agent 集成

将Kimi CLI作为DSS选股系统的AI后端，使用Agent配置和Wire模式。

## 文件结构

```
kimi-dss-agent/
├── dss-agent.yaml          # 主Agent配置
├── dss-system-prompt.md    # 系统提示词
├── subagent-technical.yaml # 技术分析子Agent
├── subagent-fundamental.yaml # 基本面分析子Agent
├── subagent-sentiment.yaml # 情绪分析子Agent
└── subagent-data.yaml      # 数据获取子Agent

kimi_runner.py              # Print模式封装（简单）
kimi_wire.py                # Wire模式封装（结构化）
```

## 使用方式

### 方式1: 直接运行Kimi CLI

```bash
# 使用DSS Agent配置
kimi --agent-file kimi-dss-agent/dss-agent.yaml

# 交互模式
> 分析茅台的技术面
> 获取阿里巴巴的研报
```

### 方式2: Print模式（Python调用）

```python
from kimi_runner import run_kimi_task

# 简单任务
result = run_kimi_task("分析sh.600519的技术指标")
print(result['output'])

# DSS分析
result = run_kimi_task("""
from dss_v4 import ImprovedStockPicker
picker = ImprovedStockPicker()
print(picker.analyze_stock('sh.600519'))
""")
```

### 方式3: Wire模式（结构化通信）

```python
from kimi_wire import KimiWireClient, run_kimi_wire

# 快捷调用
result = run_kimi_wire("分析茅台的技术面")
print(result.text)
print(result.token_usage)

# 完整客户端
with KimiWireClient() as client:
    result = client.prompt("分析sh.600519")
    
    # 获取思考过程
    for thought in result.thoughts:
        print(f"思考: {thought}")
    
    # 获取最终输出
    print(f"回答: {result.text}")
```

### 方式4: 子Agent调用

在Kimi交互中：

```
# 启动技术分析子Agent
Agent(
    description="技术分析茅台",
    prompt="分析sh.600519的RSI、MACD、均线",
    subagent_type="technical"
)

# 启动基本面分析子Agent
Agent(
    description="研报分析",
    prompt="获取茅台的研报评级和目标价",
    subagent_type="fundamental"
)
```

## Agent能力

### 主Agent (dss-analyst)

- 数据获取：股票行情、新闻、研报
- 技术分析：RSI、MACD、均线、去噪
- 基本面分析：PE、ROE、资金流向
- 情绪分析：新闻情绪、国际视角

### 子Agent

| Agent | 功能 | 工具权限 |
|-------|------|----------|
| technical | 技术分析 | 读文件、Shell |
| fundamental | 基本面分析 | 读文件、Shell |
| sentiment | 情绪分析 | 读文件、Shell |
| data | 数据获取 | 读文件、Shell、网络 |

## 与OpenClaw集成

```python
# 在OpenClaw中使用Kimi额度
from kimi_runner import run_kimi_task

# 替代sessions_spawn
def kimi_subagent(task: str, timeout: int = 300):
    result = run_kimi_task(task, timeout=timeout)
    return {
        'success': result['success'],
        'output': result['output'],
        'token_usage': result['token_usage']
    }

# 使用
result = kimi_subagent("分析茅台的技术指标，给出买卖建议")
```

## 注意事项

1. **Token计费**：使用Kimi账号额度，不是百炼API
2. **超时设置**：复杂分析任务建议timeout=300秒以上
3. **浏览器自动化**：较慢，需要足够等待时间
4. **数据降级**：API失败时自动切换备用数据源

## 测试

```bash
# 运行集成测试
python test_kimi_dss.py
```