# 🚀 Kimi 自动化工作流完整指南

> Kimi 写代码 → 自动测试 → 保存记忆 → 发送通知

---

## 📋 目录

1. [架构图](#架构图)
2. [快速开始](#快速开始)
3. [工作流详解](#工作流详解)
4. [配置说明](#配置说明)
5. [使用示例](#使用示例)
6. [故障排除](#故障排除)

---

## 🏗 架构图

```
┌─────────────┐
│   用户输入   │
│  "任务描述"  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         Kimi 自动化工作流                │
│  ┌───────────────────────────────────┐  │
│  │  Step 1: Kimi 编写代码             │  │
│  │  - 执行 kimi 命令                  │  │
│  │  - 实现功能/修复 bug              │  │
│  └──────────────┬────────────────────┘  │
│                 │                        │
│                 ▼                        │
│  ┌───────────────────────────────────┐  │
│  │  Step 2: 自动测试                  │  │
│  │  - 检测测试框架                   │  │
│  │  - 运行 pytest/npm test           │  │
│  └──────────────┬────────────────────┘  │
│                 │                        │
│                 ▼                        │
│  ┌───────────────────────────────────┐  │
│  │  Step 3: 保存记忆                  │  │
│  │  - 记录到 LanceDB                 │  │
│  │  - 保存决策上下文                 │  │
│  └──────────────┬────────────────────┘  │
│                 │                        │
│                 ▼                        │
│  ┌───────────────────────────────────┐  │
│  │  Step 4: 发送通知                  │  │
│  │  - Telegram 推送                  │  │
│  │  - 任务完成报告                   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   完成通知   │
│  ✅ 或 ❌    │
└─────────────┘
```

---

## 🎯 快速开始

### 1. 安装依赖

```bash
# 确保已安装
kimi --version          # Kimi CLI
python3 --version       # Python 3.10+
```

### 2. 配置 Kimi

```bash
# 登录 Kimi
kimi /login

# 选择 Kimi Code 平台并完成 OAuth
```

### 3. 测试工作流

```bash
cd /home/kyj/.openclaw/workspace

# 运行简单工作流
python3 kimi_workflow.py "写一个 Python 函数，计算阶乘"
```

---

## 📖 工作流详解

### Step 1: Kimi 编写代码

**功能**: 调用 Kimi CLI 执行编程任务

**配置**:
```python
timeout = 300  # 5 分钟超时
workdir = "/path/to/project"
```

**输出**:
- ✅ 代码已生成/修改
- ❌ 任务失败（超时或错误）

**日志**:
```json
{
  "stage": "STEP1",
  "message": "Kimi 开始编写代码：写一个 Python 函数",
  "data": {"success": true}
}
```

---

### Step 2: 自动测试

**功能**: 自动检测并运行项目测试

**自动检测**:
```python
if pytest.ini or tests/:     → pytest -v
if package.json:             → npm test
if Makefile:                 → make test
else:                        → 跳过测试
```

**配置**:
```bash
# 跳过测试
python3 kimi_workflow.py "任务" --skip-test

# 自定义测试命令
python3 kimi_workflow.py "任务" --test-command "pytest tests/test_login.py"
```

---

### Step 3: 保存记忆

**功能**: 将任务结果保存到 LanceDB 记忆系统

**保存内容**:
```python
{
  "text": "Kimi 完成了任务：实现登录功能\n结果：成功完成",
  "category": "fact",
  "scope": "global",
  "importance": 0.7,
  "tags": ["kimi", "workflow", "code-task"],
  "metadata": {
    "task": "实现登录功能",
    "timestamp": "2026-03-13T12:00:00",
    "workflow": "kimi-auto"
  }
}
```

**检索**:
```python
# 之后可以检索相关记忆
memory_recall(query="登录功能实现")
```

---

### Step 4: 发送通知

**功能**: 通过 Telegram 发送任务完成通知

**通知内容**:
```
🤖 Kimi 工作流完成

📝 任务：实现登录功能
📊 状态：✅ 成功
⏰ 时间：2026-03-13 12:00
```

**处理流程**:
1. 工作流写入 `pending_notifications.json`
2. Cron 每 5 分钟调用 `notification_processor.py`
3. 发送到 Telegram
4. 移动到 `sent_notifications.json`

---

## ⚙️ 配置说明

### 工作流配置

**文件**: `kimi_workflow.py`

```python
# 修改默认配置
workflow = KimiWorkflow(
    workdir="/home/kyj/.openclaw/workspace",  # 工作目录
    timeout=300  # Kimi 超时（秒）
)
```

### Cron 配置

**文件**: `cron_kimi.conf`

```bash
# 通知处理 - 每 5 分钟
notification_processor,*/5 * * * *,python3 notification_processor.py

# 记忆备份 - 每天凌晨 2 点
memory_backup,0 2 * * *,python3 auto_archive_memory.py

# 任务清理 - 每周日
kimi_cleanup,0 3 * * 0,find ... -mtime +30 -delete
```

### 日志文件

| 文件 | 用途 |
|------|------|
| `kimi_workflow.log` | 工作流执行日志 |
| `kimi_tasks.log` | Kimi 任务历史 |
| `pending_notifications.json` | 待发送通知 |
| `sent_notifications.json` | 已发送通知 |

---

## 💡 使用示例

### 示例 1: 简单函数

```bash
python3 kimi_workflow.py "写一个 Python 函数，计算斐波那契数列"
```

**预期输出**:
```
============================================================
🚀 Kimi 自动化工作流
============================================================
📂 工作目录：/home/kyj/.openclaw/workspace
📝 任务：写一个 Python 函数，计算斐波那契数列
============================================================

[STEP1] 🚀 Kimi 开始编写代码：写一个 Python 函数...
✅ Kimi 完成代码编写

[STEP2] 🧪 开始自动测试
⏭️  跳过测试

[STEP3] 🧠 保存记忆到 LanceDB
✅ 记忆已保存

[STEP4] 📱 发送通知
✅ 通知已加入队列

============================================================
🎉 工作流成功完成！
============================================================
```

---

### 示例 2: Web 应用功能

```bash
cd /path/to/web-app
python3 kimi_workflow.py "添加用户注册 API 端点"
```

**自动流程**:
1. Kimi 创建 `/api/register` 端点
2. 运行 `npm test` 或 `pytest`
3. 保存 API 设计决策
4. 发送完成通知

---

### 示例 3: Bug 修复

```bash
python3 kimi_workflow.py "修复内存泄漏，在 src/store.ts 第 130 行" --skip-test
```

**说明**: 使用 `--skip-test` 跳过测试（适合快速修复）

---

### 示例 4: 自定义测试

```bash
python3 kimi_workflow.py "实现登录功能" \
  --test-command "pytest tests/test_login.py -v"
```

---

### 示例 5: 长时间任务

```bash
python3 kimi_workflow.py "重构数据库层" --timeout 600
```

**说明**: 设置 10 分钟超时

---

## 📊 日志查看

### 查看工作流日志

```bash
# 实时查看
tail -f /home/kyj/.openclaw/workspace/kimi_workflow.log

# 查看最近的执行
cat /home/kyj/.openclaw/workspace/kimi_workflow.log | tail -50
```

### 查看通知历史

```bash
# 已发送通知
cat /home/kyj/.openclaw/workspace/sent_notifications.json | jq .

# 待发送通知
cat /home/kyj/.openclaw/workspace/pending_notifications.json
```

### 查看记忆

```bash
# LanceDB 记忆
openclaw memory list --limit 10

# 工作流记忆
cat /home/kyj/.openclaw/workspace/memory/workflow_memories.json
```

---

## 🔧 故障排除

### 问题 1: Kimi CLI 未响应

**症状**: Step 1 卡住或超时

**解决方案**:
```bash
# 检查 Kimi 状态
kimi --version

# 重新登录
kimi /login

# 增加超时
python3 kimi_workflow.py "任务" --timeout 600
```

---

### 问题 2: 测试失败

**症状**: Step 2 报告测试失败

**解决方案**:
```bash
# 查看测试输出
cd /path/to/project
pytest -v

# 跳过测试（临时）
python3 kimi_workflow.py "任务" --skip-test

# 修复测试后重试
python3 kimi_workflow.py "重新运行测试" --test-command "pytest"
```

---

### 问题 3: 通知未发送

**症状**: Step 4 完成但未收到 Telegram 通知

**解决方案**:
```bash
# 手动触发通知处理
python3 notification_processor.py

# 检查 OpenClaw 状态
openclaw status

# 查看通知队列
cat pending_notifications.json
```

---

### 问题 4: 记忆未保存

**症状**: Step 3 失败

**解决方案**:
```bash
# 检查 LanceDB
openclaw memory stats

# 手动保存
python3 -c "
from pathlib import Path
import json
memory_file = Path('memory/workflow_memories.json')
memory_file.parent.mkdir(exist_ok=True)
memory_file.write_text('{}')
"
```

---

## 📈 最佳实践

### 1. 分步执行大任务

```bash
# ❌ 不要
python3 kimi_workflow.py "重构整个项目"

# ✅ 更好
python3 kimi_workflow.py "1. 分析当前架构"
python3 kimi_workflow.py "2. 提出重构方案"
python3 kimi_workflow.py "3. 实施第一阶段"
```

### 2. 保存关键决策

```bash
# 工作流自动保存后，手动补充重要信息
memory_store "选择 PostgreSQL 因为需要 ACID 事务", importance=0.9
```

### 3. 监控工作流健康

```bash
# 每天检查工作流日志
grep "ERROR" kimi_workflow.log | tail -10

# 监控成功率
cat kimi_workflow.log | grep "WORKFLOW.*完成" | jq -s 'group_by(.success) | map(length)'
```

### 4. 优化超时设置

```bash
# 简单任务：60 秒
python3 kimi_workflow.py "写工具函数" --timeout 60

# 中等任务：300 秒
python3 kimi_workflow.py "实现 API" --timeout 300

# 大型任务：600 秒
python3 kimi_workflow.py "重构模块" --timeout 600
```

---

## 🔗 相关资源

- [Kimi CLI 文档](https://www.kimi.com/code/docs/kimi-cli/)
- [OpenClaw 记忆系统](./memory-lancedb-pro/README_CN.md)
- [OpenClaw Cron](https://docs.openclaw.ai)
- [工作流脚本](./kimi_workflow.py)

---

*最后更新：2026-03-13*
*版本：1.0*
