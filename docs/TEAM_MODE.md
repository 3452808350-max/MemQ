# Team Mode 使用指南

解决 subagent 和主 session 响应冲突问题。

## 快速开始

```python
from team_mode import start_team_mode, complete_team_mode

# 启动
start_team_mode("任务描述", subagent_count=4)

# 启动 subagents...

# 完成并汇总
complete_team_mode()
```

## 规则

### 启动前
1. 检查并清理现有 subagent
2. 设置 `team_mode_active = True`

### 进行中
- 主 Session 进入监听模式
- 用户可发送 `/cancel` 中断

### 完成后
- 主 Session **统一汇总响应**
- 清理状态

## 优先级

```
用户直接消息 > Team Mode 汇总 > Subagent 状态
```

## 命令

| 命令 | 功能 |
|------|------|
| `/team <任务>` | 启动 team mode |
| `/cancel` | 取消当前任务 |
| `/status` | 查看状态 |

## 详情

完整设计文档: `TEAM_MODE_PRIORITY.md`
状态管理器: `team_mode.py`
