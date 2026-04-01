# MEMORY-projects.md - 项目历史

## 2026-02-17: DSS v2.0 重大突破

**关键成就：**
1. ✅ 完成 DSS 改进计划所有 4 个步骤
2. ✅ 发现并集成 Alpha Vantage API (Key: MXAYBEBGFHR6PHYW)
3. ✅ 实现 Walk Forward 验证框架
4. ✅ XGBoost 模型在 AAPL 上达到 55% 方向准确率

**技术决策：**
- 优先使用 Alpha Vantage 而非 yfinance（避免速率限制）
- Walk Forward 验证是防止过拟合的关键
- 保持项目简洁，不创建冗余脚本

**重要发现：**
- 项目已有现成 API 资源
- 免费 API 限制：25 次/天，100 天历史数据
- XGBoost 在股票预测中表现优于传统模型

---

## OpenClaw 多 Agent 系统

**学习要点：**
- 每个 Agent 是独立大脑（workspace + 身份 + 会话）
- 通过 bindings 路由消息到不同 Agent
- 可以配置不同模型（如 Qwen 3.5）给不同 Agent

**配置方法：**
```bash
openclaw agents add <agentId>
```

**协作方式：**
- 使用 `sessions_spawn` 工具调用其他 Agent
- 可以指定 `agentId` 和任务进行协作

---

## 项目架构原则

1. **简洁性** - 避免脚本臃肿，一个文件完成一个功能
2. **实用性** - 优先使用现有资源（如 API Key）
3. **可扩展性** - 支持多 Agent 协作
4. **验证严谨** - Walk Forward 防止数据泄漏

---

## 未来方向

1. **论文精读** - 系统学习量化交易论文
2. **定时分析** - 自动化每日市场分析
3. **多 Agent 协作** - 配置 Qwen 作为第二个 Agent
4. **数据增强** - 获取更多历史数据

---

## 2026-02-25: 插件集成

### Everything Claude Code
- 整合到 `~/skills/everything-claude-code/`
- 包含 5 个 Agent + 7 个 Skill

### Memory LanceDB Pro
- 克隆自 https://github.com/win4r/memory-lancedb-pro
- 混合检索 (Vector + BM25)
- Cross-Encoder 重排
- 配置使用 DashScope embedding

---

## 2026-03-02: 多 AI 协作流程规范 ✨

**背景**：设计 DSS 宏观事件分析模块时的灵感——复杂代码项目适合多 AI 协作

**工作流程**：
```
Minimax 2.5 (初版) → README.md → Qwen 3.5 (审查改进) → 迭代 → 终版 → LanceDB Pro → 清理 context
```

**核心机制**：
| 机制 | 说明 |
|------|------|
| 📄 README 交接 | AI 之间通过 README.md 传递上下文，每个 AI 完成后更新 |
| 🗂️ 临时 Workspace | 使用临时 workspace 隔离任务，避免污染主 workspace |
| 💾 知识沉淀 | 终版文档存入 LanceDB Pro 长期记忆 |
| 🧹 Context 清理 | 任务完成后清理 context，避免影响后续任务 |

**适用场景**：
- 多模块代码项目
- 需要迭代的设计任务
- 需要不同 AI 专长的协作（如 Minimax 写代码 + Qwen 审查）

**技术实现**：
- 使用 `sessions_spawn` 创建子 Agent 会话
- 每个 Agent 完成后更新 `README.md`
- 最终成果通过 `kimi_upload_file` 或 `message.send` 发送
- 长期记忆通过 LanceDB Pro 插件存储（使用 `memory_store` 工具）

**详情**：`memory/2026-03-02.md`

---

*最后更新：2026-03-02*
