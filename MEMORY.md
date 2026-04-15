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
1. ✅ 横盘检测优化 - 已完成
2. ✅ 国际视角情绪异步化 - 已完成
3. ⏳ akshare 数据源连接问题 - 待解决

### 已完成优化 (2026-04-04)

#### 1. 横盘检测优化
**文件**: `/home/kyj/文档/anlyse/dss-project/integration/technical_analyzer.py`

**新增功能**:
- `detect_sideways_market()` - 横盘检测主方法
- `calculate_atr()` - 平均真实波幅计算
- `calculate_adx()` - 平均趋向指数计算

**检测指标**:
- 价格波动率 (ATR/价格 < 2.5%)
- 布林带宽度 (< 10% 视为横盘)
- ADX 趋势强度 (< 20 视为无趋势)
- 价格区间持续时间

**输出结果**:
- `is_sideways`: 是否横盘
- `duration`: 横盘持续时间
- `breakout_probability`: 突破概率
- `recommendation`: 操作建议

#### 2. 国际视角情绪异步化
**文件**: `/home/kyj/文档/anlyse/dss-project/integration/real_data_sources.py`

**新增功能**:
- `AsyncSentimentAnalyzer` 类 - 异步情绪分析器
- `get_sentiment_async()` - 异步获取情绪数据
- `get_sentiment_sync()` - 同步包装器（向后兼容）

**特性**:
- 使用 asyncio + aiohttp 并发请求
- 支持 Reddit、NewsAPI、Twitter 多数据源
- TTL 5分钟缓存机制
- 情绪分数加权聚合
- 完全向后兼容

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

## 邮件配置 (2026-04-06 完成 ✅)
- **邮箱**: k.3452808350@zohomail.com
- **SMTP**: smtp.zoho.com:465 (SSL)
- **状态**: 已测试发送成功
- **配置文件**: `/home/kyj/文档/anlyse/dss-project/.env`

### DSS Bug 修复 (2026-04-07)

**修复内容**:
1. `run_daily_prediction.py` 第210-211行变量名错误 (`delta` → `deltas`)
2. 添加 `convert_to_native()` 函数解决 numpy bool JSON 序列化问题

**状态**: ✅ 已修复

## 最近状态
- **2026-04-15 (晚间)**: 🌙 晚间记忆总结完成，系统状态正常。DSS v4.3稳定运行，双项目已完成(Claude Plugin 46测试 + Context Manager 90测试)，akshare数据源问题待解决
- **2026-04-15 (中午)**: 🌞 记忆总结完成，系统正常运行。DSS v4.3稳定，双项目136测试通过，待解决akshare数据源问题
- **2026-04-15 (早间)**: ✅ DSS完整运行！早班预测(6股票/平均56.52/买入000001+601166各65分) + 因子验证(平均60.27/601166最佳66分) + 邮件报告已发送。横盘检测3/6正常，数据源mock模式
- **2026-04-14 (晚间)**: 🌙 记忆总结完成。DSS早班预测：14股票/平均59.46/强烈买入TSLA+002415各70分，买入7只。因子验证平均46.59，NVDA最佳59.81。数据源mock模式，akshare问题待解决
- **2026-04-14 (中午)**: 🌅 记忆总结完成，系统正常运行。DSS早班预测已执行(14股票/平均59.46/强烈买入TSLA+002415)
- **2026-04-14 (早间)**: ✅ DSS完整运行！预测14股票(平均59.46，强烈买入TSLA/002415，买入7只) + 因子验证(平均46.59，NVDA最佳59.81)，邮件已发送。数据源仍为mock模式
- **2026-04-13**: ✅ DSS完整运行！早班预测14股票(平均38.86，持有5/卖出9，横盘检测13/14正常) + 因子验证(平均46.59，NVDA最佳59.81)，邮件已发送。数据源仍为mock模式，akshare连接问题待解决
- **2026-04-12 (晚间)**: 周日系统检查正常，记忆总结完成。DSS v4.3稳定运行，双项目(Claude Plugin + Context Manager)已完成共136测试通过。待解决：akshare数据源连接问题
- **2026-04-12 (中午)**: 系统状态检查完成，项目稳定运行
- **2026-04-11**: 系统正常，记忆总结完成，待解决akshare数据源问题。DSS v4.3稳定运行，双项目(Claude Plugin + Context Manager)已完成共136测试通过
- **2026-04-10**: ✅ DSS 完整运行日！预测(14股票，平均44.36，推荐AMZN买入) + 验证(平均51.96，TSLA/NFLX最佳64分)，邮件系统正常，横盘检测13/14正常
  - ⚠️ 待解决: akshare 数据源连接问题
- **2026-04-09**: DSS 早班预测(14股票，平均45.91，推荐600519买入)，因子验证平均50.72，GOOGL/000001/000858表现最佳
- **2026-04-08**: 系统稳定运行日，DSS v4.3 正常，双项目(Claude Plugin + Context Manager)稳定，邮件系统正常
- **2026-04-07**: ✅ DSS 系统稳定运行！预测(14股票，平均59.99，强烈买入000858) + 验证(平均52.17) + Bug修复(delta→deltas变量名, numpy bool序列化)
- **2026-04-07 (早间)**: ✅ DSS 预测正常运行！14只股票分析完成(平均得分59.99，强烈买入1只)，因子验证邮件已发送
- **2026-04-06 (晚间)**: ✅ DSS 系统完整运行！早班预测(14股票，平均得分42.07) + 因子验证(平均51.14) + 邮件系统配置完成(ZohoMail SMTP已测试)
- **2026-04-06 (早间)**: DSS 预测流程自动化执行，横盘检测正常(11/14股票横盘)，邮件通知系统部署完成
- **2026-04-05 (晚间)**: 定时检查，所有项目稳定运行，无待办事项，系统正常
- **2026-04-05 (中午)**: 定时检查，所有项目稳定运行，无待办事项
- **2026-04-04 (晚间)**: ✅ DSS v4.3 双优化完成！横盘检测 + 国际情绪异步化全部实现
- 2026-04-04: 晚间定时任务运行，记忆总结完成，所有待办事项已清零
- 2026-04-03: 系统维护日，状态检查完成，双项目稳定运行
- 2026-04-02: 🎉 双项目完成日！Claude Plugin (46测试) + Context Manager (90测试) 全部通过
- 2026-04-01: 系统运行正常，DSS v4.3 准确率 58.2%

---
*此文件记录重要的长期记忆，定期从日常日志中提炼更新*