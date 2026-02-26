# MEMORY-projects.md - 项目历史

## 2026-02-17: DSS v2.0 重大突破

**关键成就：**
1. ✅ 完成DSS改进计划所有4个步骤
2. ✅ 发现并集成Alpha Vantage API (Key: MXAYBEBGFHR6PHYW)
3. ✅ 实现Walk Forward验证框架
4. ✅ XGBoost模型在AAPL上达到55%方向准确率

**技术决策：**
- 优先使用Alpha Vantage而非yfinance（避免速率限制）
- Walk Forward验证是防止过拟合的关键
- 保持项目简洁，不创建冗余脚本

**重要发现：**
- 项目已有现成API资源
- 免费API限制：25次/天，100天历史数据
- XGBoost在股票预测中表现优于传统模型

---

## OpenClaw多Agent系统

**学习要点：**
- 每个Agent是独立大脑（workspace + 身份 + 会话）
- 通过bindings路由消息到不同Agent
- 可以配置不同模型（如Qwen 3.5）给不同Agent

**配置方法：**
```bash
openclaw agents add <agentId>
```

**协作方式：**
- 使用 `sessions_spawn` 工具调用其他Agent
- 可以指定 `agentId` 和任务进行协作

---

## 项目架构原则

1. **简洁性** - 避免脚本臃肿，一个文件完成一个功能
2. **实用性** - 优先使用现有资源（如API Key）
3. **可扩展性** - 支持多Agent协作
4. **验证严谨** - Walk Forward防止数据泄漏

---

## 未来方向

1. **论文精读** - 系统学习量化交易论文
2. **定时分析** - 自动化每日市场分析
3. **多Agent协作** - 配置Qwen作为第二个Agent
4. **数据增强** - 获取更多历史数据

---

## 2026-02-25: 插件集成

### Everything Claude Code
- 整合到 `~/skills/everything-claude-code/`
- 包含5个Agent + 7个Skill

### Memory LanceDB Pro
- 克隆自 https://github.com/win4r/memory-lancedb-pro
- 混合检索 (Vector + BM25)
- Cross-Encoder 重排
- 配置使用 DashScope embedding

---

*最后更新: 2026-02-25*
