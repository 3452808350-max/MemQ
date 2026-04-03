# MEMORY.md - 长期记忆

## 项目状态

### Claude Plugin (2026-04-02 完成 ✅)
- **位置**: `/home/kyj/文档/IELTS-Obsidian/Projects/claude-plugin/`
- **架构**: 基于 Claude Code 多 Agent 系统
- **模块**: 6个全部实现 (Agent Definitions, Fork Subagent, Task Notification, Message Passing, Coordinator Mode, Permission System)
- **测试**: 46个全部通过
- **Git**: commit `3156f72`, 已推送至 notes 仓库

### DSS 选股系统
- **版本**: v4.3
- **准确率**: 58.2%
- **MemQ Recall@1**: 90%

### 待办事项
1. 横盘检测优化
2. 国际视角情绪异步化

## 技术配置
- 阿里云 text-embedding-v2 模型已配置并测试

### Context Manager 上下文管理器 (2026-04-02 完成 ✅)
- **位置**: `/home/kyj/.openclaw/workspace/context-manager-impl/`
- **架构**: 基于 Claude Code 上下文管理 + OpenClaw 短期记忆融合
- **阶段**: P0/P1/P2/P3 全部完成
- **测试**: 90个全部通过
- **核心模块**:
  - TokenBudget - Token 预算管理
  - MessageHistory - 消息历史管理
  - PriorityTruncator - 优先级截断
  - LLMCompressor - LLM 压缩
  - MultiAgentContext - 多 Agent 上下文 (Fork/Coordinator/Merge)
  - TaskNotificationService - 任务通知服务
  - LanceDBStorageAdapter - memory-lancedb-pro 存储适配器

## 最近状态
- 2026-04-03: 系统维护日，状态检查完成，双项目稳定运行
- 2026-04-02: 🎉 双项目完成日！Claude Plugin (46测试) + Context Manager (90测试) 全部通过
- 2026-04-01: 系统运行正常，DSS v4.3 准确率 58.2%

---
*此文件记录重要的长期记忆，定期从日常日志中提炼更新*