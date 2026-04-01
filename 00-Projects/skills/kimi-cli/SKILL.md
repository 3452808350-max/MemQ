# Kimi CLI Integration Skill

## 概述

这个Skill用于将Kimi CLI (Kimi Code) 集成到OpenClaw，作为Coding Agent使用。

## 前置要求

1. 已安装Kimi CLI: `uv tool install kimi-cli`
2. 已完成登录: `kimi` → `/login`

## 使用方法

### 启动Kimi CLI (需要先在终端完成登录)

```bash
# 方式1: ACP Server模式 (推荐)
kimi acp --port 8080

# 方式2: MCP Server模式
kimi mcp start
```

### 调用Kimi CLI

通过Python调用:

```python
import subprocess
import json

def call_kimi_cli(prompt: str) -> str:
    """调用Kimi CLI执行任务"""
    result = subprocess.run(
        ['kimi', '-c', prompt],  # 需要先配置
        capture_output=True,
        text=True,
        timeout=300
    )
    return result.stdout

# 或通过API (如果Kimi CLI运行在server模式)
def call_kimi_api(prompt: str) -> str:
    """通过HTTP API调用"""
    import requests
    resp = requests.post(
        'http://localhost:8080/chat',
        json={'prompt': prompt}
    )
    return resp.json()['response']
```

## Kimi CLI 功能

| 功能 | 说明 |
|------|------|
| 读取文件 | 理解和分析代码库 |
| 写入文件 | 生成和修改代码 |
| 执行命令 | 运行Shell命令 |
| 搜索 | 搜索文件和代码 |
| 网页抓取 | 获取网页信息 |

## 集成状态

- [x] Kimi CLI已安装 (v1.12.0)
- [ ] 登录完成 (需要用户手动执行)
- [ ] ACP Server配置
- [ ] OpenClaw Tool集成

## 快速开始

1. 登录Kimi CLI:
   ```bash
   kimi
   /login
   ```

2. 启动ACP Server:
   ```bash
   kimi acp --port 8080
   ```

3. 在OpenClaw中使用:
   通过API调用 `http://localhost:8080`

## 注意事项

- Kimi CLI需要登录后才能使用完整功能
- ACP Server模式支持MCP工具调用
- 默认端口8080，可自定义
