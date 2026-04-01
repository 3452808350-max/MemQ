# OpenClaw Watchdog v2 改进说明

## 主要改进

### 1. 指数退避重试机制
```python
# 配置
BACKOFF_INITIAL_DELAY = 30      # 初始延迟 30 秒
BACKOFF_MAX_DELAY = 600         # 最大延迟 10 分钟
BACKOFF_MULTIPLIER = 2          # 倍数

# 延迟计算示例
第1次失败: 30 秒
第2次失败: 60 秒
第3次失败: 120 秒
第4次失败: 240 秒
第5次+失败: 600 秒（封顶）
```

**解决问题**: 避免服务故障时频繁重启，给系统恢复留出时间。

---

### 2. 分级健康状态

| 状态 | 含义 | 连续失败次数 | 行动 |
|------|------|-------------|------|
| `OK` | 正常 | 0 | 无 |
| `WARNING` | 警告（偶发问题） | 2 | 记录日志，发送通知 |
| `ERROR` | 错误（需要关注） | 3 | 尝试简单修复 |
| `CRITICAL` | 严重（需要立即处理） | 4 | 执行重启 |
| `DEAD` | 服务死亡 | - | 立即重启 |

**解决问题**: 避免对暂时性波动过度反应，只有持续故障才触发重启。

---

### 3. 智能故障检测

#### 容忍度配置
```python
TELEGRAM_ERROR_TOLERANCE = 5        # 5 次错误才判定为故障
TELEGRAM_STALL_TOLERANCE = 3        # 3 次停滞才判定为卡住
```

#### 动态日志检测
```python
def get_latest_log_file(self) -> Optional[Path]:
    """自动找到最新日志文件，不再硬编码日期"""
    log_files = list(Path("/tmp/openclaw").glob("openclaw-*.log"))
    return max(log_files, key=lambda p: p.stat().st_mtime)
```

**解决问题**: 
- v1 硬编码 `2026-03-13` 导致只检查旧日志
- v2 自动找到最新日志文件

---

### 4. 故障趋势分析

```python
# 在 60 分钟内检测到 3 次相同错误视为模式
TREND_ANALYSIS = {
    "enabled": True,
    "window_minutes": 60,
    "pattern_threshold": 3,
}
```

**功能**:
- 记录错误签名和发生时间
- 识别周期性故障
- 输出模式检测警告

---

### 5. 更早的 AI 介入

```python
AI_FIX = {
    "immediate_triggers": [
        "config_error",           # 配置错误
        "kimi_bridge_auth_fail",  # Kimi Bridge 认证失败
        "permission_denied",      # 权限问题
    ]
}
```

**解决问题**: v1 需要重启 3 次后才触发 AI 修复，v2 对配置类错误立即触发。

---

### 6. 改进的控制脚本

```bash
# 查看状态
python3 openclaw-watchdog-ctl.py status

# 查看日志
python3 openclaw-watchdog-ctl.py logs 50

# 故障分析
python3 openclaw-watchdog-ctl.py analyze

# 升级/回滚
python3 openclaw-watchdog-ctl.py upgrade
python3 openclaw-watchdog-ctl.py rollback
```

---

## 配置文件对比

| 配置项 | v1 | v2 |
|--------|-----|-----|
| 检查间隔 | 60秒 | 60秒 |
| 最大重启次数 | 3 | 3 |
| 重启延迟 | 固定 5秒 | 指数退避 30-600秒 |
| 健康状态 | ok/error/dead/stuck | ok/warning/error/critical/dead |
| Telegram 错误阈值 | 2次停滞即重启 | 3次停滞/5次错误 |
| 日志路径 | 硬编码 | 动态检测 |
| 趋势分析 | ❌ | ✅ |
| 分级处理 | ❌ | ✅ |

---

## 日志对比

### v1 日志（频繁重启）
```
2026-03-14 16:13:42 - WARNING - 发现问题：服务功能性故障: Telegram polling 多次停滞 (2 次)
2026-03-14 16:13:44 - WARNING - 已强制杀死进程 277435
2026-03-14 16:13:46 - INFO - Gateway 重启成功
2026-03-14 16:14:50 - WARNING - 发现问题：服务功能性故障: Telegram polling 多次停滞 (2 次)
2026-03-14 16:14:58 - WARNING - 已强制杀死进程 277710
...
```

### v2 日志（智能处理）
```
2026-03-14 16:38:39 - INFO - ✅ 健康状态: ok | PID: 283244 | 端口: True
2026-03-14 16:39:39 - INFO - ✅ 健康状态: ok | PID: 283244 | 端口: True
2026-03-14 16:40:39 - INFO - ⚠️ 健康状态: warning | 连续失败: 2 | 错误签名: telegram_error
2026-03-14 16:41:39 - INFO - ⚠️ 健康状态: error | 连续失败: 3 | 执行修复...
2026-03-14 16:42:39 - INFO - ⚠️ 健康状态: critical | 连续失败: 4 | 准备重启...
2026-03-14 16:42:40 - INFO - 退避等待中，还需等待 30 秒
```

---

## 使用说明

### 立即切换到 v2
```bash
python3 ~/.openclaw/workspace/openclaw-watchdog-ctl.py upgrade
```

### 回滚到 v1
```bash
python3 ~/.openclaw/workspace/openclaw-watchdog-ctl.py rollback
```

### 查看实时日志
```bash
journalctl --user -u openclaw-watchdog -f
# 或
tail -f ~/.openclaw/watchdog_v2.log
```

---

## 后续改进建议

1. **Web Dashboard**: 提供可视化监控界面
2. **预测性维护**: 基于历史数据预测故障
3. **自动配置修复**: AI 自动修复常见配置问题
4. **多节点支持**: 分布式监控多个 Gateway 实例
