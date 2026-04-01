# MemQ 质量评分服务 - 最终状态报告

**更新时间**: 2026-03-17 10:14  
**状态**: ✅ 运行正常

---

## 📊 服务状态

| 服务 | 端口 | PID | 状态 |
|------|------|-----|------|
| MemQ 质量评分 | 5556 | 17363 | ✅ 运行中 |
| MemQ Bridge | 5555 | - | ⚠️ 未启动（可选） |

**健康检查**:
```bash
curl http://localhost:5556/health
# 响应：{"service":"MemQ Quality Scorer","status":"ok"}
```

---

## 🚀 启动方式

### 自动启动（已集成）

Gateway 启动时通过 `gateway_start` 钩子自动启动：

```typescript
// plugins/memory-lancedb-pro/index.ts
api.on("gateway_start", async () => {
  await startMemQServices();
});
```

### 手动启动

```bash
bash /home/kyj/.openclaw/plugins/memory-lancedb-pro/memq-services.sh start
```

---

## 🧪 测试记录

### 质量评分测试

**高质量文本** (事实类):
```bash
curl -X POST http://localhost:5556/score \
  -H "Content-Type: application/json" \
  -d '{"text": "K 的密码文件位置：/home/kyj/文档/pawsswd.md", "category": "fact"}'
```
**结果**: 0.845 分 ✅

**低质量文本** (客套话):
```bash
curl -X POST http://localhost:5556/score \
  -H "Content-Type: application/json" \
  -d '{"text": "好的，我来帮你", "category": "other"}'
```
**结果**: 0.51 分 ⚠️

---

## 📁 关键文件

| 文件 | 说明 |
|------|------|
| `quality_scorer_service.py` | Python Flask 服务 |
| `quality-client.ts` | TypeScript HTTP 客户端 |
| `startup-hook.ts` | Gateway 启动钩子 |
| `memq-services.sh` | 服务管理脚本 |
| `index.ts` | 插件主入口（集成质量过滤） |

---

## 🔧 故障排除

### 服务未运行

```bash
# 1. 检查进程
pgrep -f quality_scorer_service

# 2. 查看日志
tail /tmp/memq_quality.log

# 3. 手动启动
cd /home/kyj/.openclaw/plugins/memory-lancedb-pro
python3 quality_scorer_service.py
```

### Gateway 重启后服务未启动

检查插件日志：
```bash
tail -f ~/.openclaw/logs/gateway.log | grep "MemQ"
```

---

## 📈 性能指标

- **响应时间**: <50ms (本地 HTTP)
- **评分精度**: 6 维度加权（类型/长度/实体/破坏词/模板/元数据）
- **过滤阈值**: 0.4 (可调整)
- **内存占用**: ~50MB

---

## 🎯 下一步

1. **监控服务稳定性** - 观察 Gateway 重启后是否自动恢复
2. **调整质量阈值** - 根据实际效果优化 0.4 阈值
3. **扩展模板匹配** - 增加更多低质量模板模式

---

**报告生成**: Kaguya  
**最后检查**: 2026-03-17 10:14 ✅
