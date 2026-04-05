# Team Mode 优先度机制

## 问题描述

使用 Team Mode (多 Subagent 协作) 后，主 Session 有时无法正常响应用户消息。

## 根因分析

1. **消息路由冲突** - Subagent 和主 Session 都可能尝试响应同一条消息
2. **状态混淆** - 系统可能将主 Session 的响应误认为是 Subagent 的完成通知
3. **响应竞争** - 多个 Agent 同时尝试发送消息到同一频道

## 解决方案：优先度机制

### 核心原则

```
用户直接消息 > Subagent 完成通知 > 内部状态更新
```

### 实现机制

#### 1. 消息类型标记

```python
class MessagePriority:
    CRITICAL = 0    # 用户直接提问、紧急通知
    HIGH = 1        # 主 Session 响应
    NORMAL = 2      # Subagent 完成报告
    LOW = 3         # 内部日志、调试信息
```

#### 2. Team Mode 使用规则

**启动 Team Mode 前：**
```python
# 1. 检查是否有活跃 subagent
active = subagents(action="list")
if active["active"]:
    # 等待或终止现有 subagent
    pass

# 2. 设置 team_mode 标志
set_state("team_mode_active", True)
set_state("team_mode_start_time", now())
```

**Team Mode 进行中：**
```python
# 1. 主 Session 进入"监听模式"
# 2. 不主动响应用户消息（除非明确取消 team mode）
# 3. 定期 poll subagent 状态
```

**Team Mode 完成后：**
```python
# 1. 清理 team_mode 标志
set_state("team_mode_active", False)

# 2. 主动拉取所有 subagent 结果
results = []
for subagent in recent_subagents:
    history = sessions_history(sessionKey=subagent["sessionKey"], limit=10)
    results.append(parse_result(history))

# 3. 主 Session 统一汇总并响应
send_unified_response(results)
```

#### 3. 用户消息中断机制

```python
def on_user_message(message):
    # 检查 team mode 状态
    if get_state("team_mode_active"):
        # 用户发送了新消息，优先响应用户
        if is_cancel_command(message):
            kill_all_subagents()
            clear_team_mode()
            respond("Team mode 已取消，现在直接为您服务")
        else:
            # 可选：继续 team mode 或中断
            respond("Team mode 正在进行中。发送 /cancel 取消，或等待完成...")
    else:
        # 正常处理
        process_message(message)
```

#### 4. 响应去重机制

```python
# 在 .agent-state.json 中跟踪
{
    "lastResponse": {
        "messageId": "6437",
        "timestamp": "2026-04-05T18:55:00",
        "responder": "main|subagent:xxx",
        "content_hash": "sha256:..."
    },
    "teamMode": {
        "active": false,
        "startTime": null,
        "subagents": []
    }
}
```

### 具体实施步骤

#### 步骤 1: 修改 AGENTS.md 添加 Team Mode 规则

```markdown
## Team Mode 使用规范

### 启动前
1. 检查并清理现有 subagent
2. 设置 team_mode_active 标志
3. 记录启动时间

### 进行中
1. 主 Session 进入监听模式
2. 用户可随时发送 /cancel 中断
3. 每 30 秒 poll 一次 subagent 状态

### 完成后
1. 清理 team_mode_active 标志
2. 拉取所有 subagent 结果
3. 主 Session 统一汇总响应
4. 更新 .agent-state.json
```

#### 步骤 2: 创建 Team Mode 状态管理器

```python
# team_mode_manager.py
class TeamModeManager:
    def __init__(self):
        self.state_file = ".agent-state.json"
    
    def start(self, subagent_count):
        """启动 team mode"""
        state = self._load_state()
        state["teamMode"] = {
            "active": True,
            "startTime": datetime.now().isoformat(),
            "subagentCount": subagent_count,
            "completed": []
        }
        self._save_state(state)
    
    def complete(self):
        """完成 team mode"""
        state = self._load_state()
        state["teamMode"]["active"] = False
        state["teamMode"]["endTime"] = datetime.now().isoformat()
        self._save_state(state)
    
    def is_active(self):
        """检查是否处于 team mode"""
        state = self._load_state()
        return state.get("teamMode", {}).get("active", False)
    
    def should_respond(self, message_id):
        """判断是否应该响应此消息"""
        state = self._load_state()
        last = state.get("lastResponse", {})
        
        # 避免重复响应
        if last.get("messageId") == message_id:
            return False
        
        # team mode 期间，只有主 Session 汇总消息可以响应
        if state.get("teamMode", {}).get("active"):
            return False
        
        return True
```

#### 步骤 3: 修改 subagent 调用逻辑

```python
# 使用 team mode 时
def run_team_mode(tasks):
    manager = TeamModeManager()
    
    # 1. 启动前清理
    if manager.is_active():
        # 等待或取消现有任务
        pass
    
    # 2. 设置状态
    manager.start(len(tasks))
    
    # 3. 启动 subagents
    subagent_ids = []
    for task in tasks:
        result = sessions_spawn(
            runtime="subagent",
            task=task,
            mode="run"
        )
        subagent_ids.append(result["sessionKey"])
    
    # 4. 等待完成（带用户中断检查）
    while True:
        time.sleep(5)
        
        # 检查用户是否发送了新消息
        if has_new_user_message():
            # 用户有急事，暂停或取消
            break
        
        # 检查 subagent 状态
        status = subagents(action="list")
        if not status["active"]:
            break
    
    # 5. 完成处理
    manager.complete()
    
    # 6. 拉取结果并汇总
    results = collect_subagent_results(subagent_ids)
    return summarize_results(results)
```

### 用户命令

| 命令 | 功能 |
|------|------|
| `/team <任务>` | 启动 team mode |
| `/cancel` | 取消当前 team mode |
| `/status` | 查看 team mode 状态 |
| `/subagent <任务>` | 单个子agent（非 team mode）|

### 最佳实践

1. **Team Mode 适合**：复杂任务、并行处理、代码审查
2. **单 Subagent 适合**：简单任务、快速修复
3. **直接响应适合**：简单问答、状态查询

### 测试验证

```python
# 测试用例
1. 启动 team mode → 发送用户消息 → 应收到中断提示
2. team mode 完成 → 应收到统一汇总响应
3. 快速连续发送 /subagent → 应排队或拒绝
4. 检查 .agent-state.json → teamMode.active 应正确
```

---

## 实施计划

1. ✅ 设计文档（本文件）
2. ⬜ 更新 AGENTS.md 添加规则
3. ⬜ 实现 TeamModeManager 类
4. ⬜ 修改 subagent 调用逻辑
5. ⬜ 测试验证
6. ⬜ 文档更新
