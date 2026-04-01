# 🚀 MemQ 服务启动完成！

## ✅ 最终方案

### Gateway 启动钩子（主要方式 ⭐）

插件会在 `gateway_start` 时自动启动服务，**无需 systemd**。

**工作原理**：
1. Gateway 启动 → 触发 `gateway_start` 钩子
2. 插件调用 `startMemQServices()`
3. 检查端口，如未运行则启动 Python 服务
4. 服务在后台运行，Gateway 重启后自动恢复

### 手动启动脚本（备用）
```bash
# 启动
/home/kyj/.openclaw/plugins/memory-lancedb-pro/memq-services.sh start

# 查看状态
/home/kyj/.openclaw/plugins/memory-lancedb-pro/memq-services.sh status

# 停止
/home/kyj/.openclaw/plugins/memory-lancedb-pro/memq-services.sh stop
```

---

## 🧪 测试

```bash
# 健康检查
curl http://localhost:5556/health

# 测试评分
curl -X POST http://localhost:5556/score \
  -H "Content-Type: application/json" \
  -d '{"text": "密码文件位置", "category": "fact"}'
```

---

## 📝 下次 Gateway 重启后

服务会自动启动，无需手动操作！

如果服务未运行，检查：
```bash
# 1. 进程
pgrep -f quality_scorer_service

# 2. 日志
tail /tmp/memq_quality.log

# 3. 手动启动
bash /home/kyj/.openclaw/plugins/memory-lancedb-pro/memq-services.sh start
```

---

## 📊 服务架构

```
OpenClaw Gateway 启动
    ↓
gateway_start 钩子触发
    ↓
startup-hook.ts 检查端口
    ↓
如未运行 → spawn python3 quality_scorer_service.py
    ↓
服务在后台运行 (detached)
    ↓
记忆检索时通过 HTTP 调用质量评分
```

---

**当前状态**: ✅ 服务运行中  
**端口**: 5556 (质量评分), 5555 (Bridge)  
**systemd**: ❌ 已禁用（改用 Gateway 钩子）
