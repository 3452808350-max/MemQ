# Harness Lab Skill - OpenClaw 连接接口

连接 code-flow (Harness Lab) 代码执行沙箱平台，用于测试代码执行、约束验证、会话管理等。

## 触发条件

当用户需要以下功能时使用此 skill：
- 执行代码片段并获取结果
- 测试约束验证系统
- 创建和管理执行会话
- 回放和分析执行轨迹
- 测试 Harness Lab API

## 服务配置

### 启动服务

```bash
cd /home/kyj/.openclaw/workspace/code-flow
export $(grep -v '^#' .env | xargs)
source venv/bin/activate

# 启动后端服务
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 4600
```

### API 端点

服务运行在 `http://localhost:4600`，主要端点：

| 端点 | 功能 |
|------|------|
| `/sessions` | 会话管理 |
| `/runs` | 执行运行 |
| `/constraints` | 约束验证 |
| `/artifacts` | 存储管理 |
| `/knowledge` | 知识库 |
| `/context` | 上下文管理 |
| `/prompts` | 提示模板 |
| `/replays` | 回放轨迹 |
| `/policies` | 策略管理 |
| `/workers` | 工作节点 |
| `/system` | 系统状态 |

## OpenClaw 工具函数

### 1. 检查服务状态

```bash
curl -s http://localhost:4600/system/status | jq .
```

### 2. 创建会话

```bash
curl -s -X POST http://localhost:4600/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "test-session", "description": "Test session"}' | jq .
```

### 3. 执行代码

```bash
curl -s -X POST http://localhost:4600/runs \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_id>",
    "code": "print(\"Hello World\")",
    "language": "python"
  }' | jq .
```

### 4. 验证约束

```bash
curl -s -X POST http://localhost:4600/constraints/verify \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Read file /tmp/test.txt",
    "constraints": ["allow-read:/tmp/*"]
  }' | jq .
```

### 5. 获取回放轨迹

```bash
curl -s http://localhost:4600/replays/<run_id> | jq .
```

## Python 客户端示例

```python
import httpx

BASE_URL = "http://localhost:4600"

async def create_session(name: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/sessions", json={"name": name})
        return resp.json()

async def execute_code(session_id: str, code: str, language: str = "python"):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/runs", json={
            "session_id": session_id,
            "code": code,
            "language": language
        })
        return resp.json()

async def verify_constraints(intent: str, constraints: list):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/constraints/verify", json={
            "intent": intent,
            "constraints": constraints
        })
        return resp.json()
```

## 测试流程

### 快速测试

1. **检查服务是否运行**:
   ```bash
   curl -s http://localhost:4600/ | jq .
   ```

2. **创建测试会话**:
   ```bash
   curl -s -X POST http://localhost:4600/sessions -H "Content-Type: application/json" -d '{"name": "quick-test"}' | jq .
   ```

3. **执行简单代码**:
   ```bash
   curl -s -X POST http://localhost:4600/runs -H "Content-Type: application/json" -d '{"session_id": "<id>", "code": "import sys; print(sys.version)"}' | jq .
   ```

### 完整测试

```bash
cd /home/kyj/.openclaw/workspace/code-flow
export $(grep -v '^#' .env | xargs)
source venv/bin/activate
python -m pytest backend/tests/integration/ -v
```

## 环境变量

配置文件位于 `/home/kyj/.openclaw/workspace/code-flow/.env`:

```bash
# 阿里云 DashScope (兼容 OpenAI)
OPENAI_API_KEY=sk-sp-xxx
OPENAI_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
HARNESS_LAB_MODEL_PROVIDER=deepseek  # 必须设为 deepseek（代码只识别此 provider）
HARNESS_LAB_MODEL_NAME=glm-5
HARNESS_DB_URL=postgresql://harness_lab@localhost:5432/harness_lab
HARNESS_REDIS_URL=redis://localhost:6379/0
HARNESS_SANDBOX_IMAGE=harness-lab/sandbox:local
```

## 服务管理

```bash
# 启动服务
cd /home/kyj/.openclaw/workspace/code-flow
export $(grep -v '^#' .env | xargs)
source venv/bin/activate
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 4600 &

# 检查状态
curl -s http://localhost:4600/ | jq .

# 停止服务
pkill -f "uvicorn.*4600"
```

## 注意事项

1. **服务启动**: 需要先启动服务才能调用 API
2. **Docker 权限**: 需要 docker 组权限执行沙箱
3. **数据库依赖**: PostgreSQL 和 Redis 需要运行
4. **API 文档**: 访问 `http://localhost:4600/docs` 查看完整 API 文档