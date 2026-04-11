# MemPalace vs LCM (OpenClaw Context Manager) 对比分析

**日期**: 2026-04-10  
**目的**: 比较两个 AI 记忆系统的架构、功能和适用场景

---

## 核心架构对比

| 维度 | MemPalace | LCM (OpenClaw) |
|------|-----------|----------------|
| **设计理念** | Palace 建筑（Wings/Rooms/Halls） | Token Budget + Layered Context |
| **存储引擎** | ChromaDB | LanceDB |
| **压缩方式** | AAAK (损失压缩) | LLM Compressor (语义压缩) |
| **知识图谱** | SQLite KG (时序实体关系) | 无独立 KG，依赖 Memory Store |
| **基准分数** | 96.6% LongMemEval R@5 (raw) | 无公开基准 |
| **MCP 工具** | 19 个 | 通过 LCM tools (grep/describe/expand) |

---

## 存储结构对比

### MemPalace Palace 架构

```
Wing (人/项目)
  ├── Room (主题: auth, billing...)
  │   ├── Hall (记忆类型: facts, events...)
  │   │   ├── Closet (摘要 → AAAK)
  │   │   └── Drawer (原始文件 - verbatim)
  │   └── Hall 连接 (halls 走廊)
  └── Tunnel (跨 Wing 连接)
```

**特点**：
- 34% 检索提升（wing + room 过滤）
- AAAK 压缩（实验性，目前 regresses）
- Knowledge Graph 时序追踪

### LCM Layered Context

```
Layer 0: Identity (~50 tokens) - always loaded
Layer 1: Critical facts (~120 tokens) - always loaded
Layer 2: Room recall (on demand)
Layer 3: Deep search (semantic query)
```

**特点**：
- Token Budget 管理（warning/critical 阈值）
- FIFO/Priority 截断
- LLM 语义压缩
- Multi-Agent Fork/Coordinator

---

## 功能对比表

| 功能 | MemPalace | LCM |
|------|-----------|-----|
| **语义搜索** | ✅ ChromaDB vector + BM25 | ✅ LanceDB vector + BM25 |
| **结构过滤** | ✅ Wing/Room/Hall | ⚠️ Priority Layer (不同理念) |
| **原始保存** | ✅ Drawer (verbatim) | ✅ Message History (raw) |
| **压缩** | ⚠️ AAAK (lossy, regresses) | ✅ LLM Compressor (semantic) |
| **知识图谱** | ✅ SQLite KG (时序) | ❌ 无独立 KG |
| **Agent Diary** | ✅ 每个 Agent Wing | ⚠️ MultiAgentContext (fork) |
| **Token 预算** | ❌ 无 explicit 管理 | ✅ TokenBudget (阈值检测) |
| **截断策略** | ❌ 无 explicit 截断 | ✅ FIFO/Priority Truncator |
| **多 Agent** | ⚠️ Agent Wing (简单) | ✅ Fork/Coordinator/Merge |
| **任务通知** | ❌ 无 | ✅ TaskNotificationService |
| **Hook 自动保存** | ✅ Stop/PreCompact | ⚠️ 需手动集成 |
| **MCP 集成** | ✅ 19 tools | ✅ 4 tools (grep/describe/expand/expand_query) |
| **本地运行** | ✅ 100% 本地 | ✅ 100% 本地 |
| **开源** | ✅ MIT | ✅ OpenClaw 内置 |

---

## Benchmark 对比

### MemPalace

| Benchmark | Mode | Score |
|-----------|------|-------|
| LongMemEval R@5 | Raw (ChromaDB) | 96.6% |
| LongMemEval R@5 | Hybrid + Haiku rerank | 100% |
| LoCoMo R@10 | Raw | 60.3% |
| Palace structure | Wing+room | +34% R@10 |
| AAAK mode | Lossy compression | 84.2% (regresses) |

### LCM

| Benchmark | Score |
|-----------|-------|
| 无公开基准 | - |
| MemQ Recall@1 | 90% (DSS 项目) |

---

## 适用场景对比

### MemPalace 优势场景

1. **对话记忆持久化** - 适合长期 AI 对话存档
2. **项目历史追溯** - "为什么我们选了 Postgres?"
3. **团队协作记忆** - 多人决策、分工追踪
4. **知识图谱场景** - 实体关系时序追踪
5. **MCP 工具集成** - Claude Code/Gemini CLI

### LCM 优势场景

1. **Token 预算管理** - 大模型上下文控制
2. **多 Agent 协作** - Fork/Coordinator/Merge
3. **任务通知** - Subagent 完成通知
4. **动态截断** - FIFO/Priority 自动截断
5. **LLM 压缩** - 语义压缩（保留关键信息）

---

## 技术栈对比

| 层面 | MemPalace | LCM |
|------|-----------|-----|
| **语言** | Python | TypeScript |
| **向量库** | ChromaDB | LanceDB |
| **KG 存储** | SQLite | - |
| **嵌入** | chromadb default | memory-lancedb-pro embedder |
| **压缩** | AAAK (regex) | LLM API |
| **CLI** | mempalace CLI | OpenClaw LCM tools |
| **MCP Server** | Python MCP | OpenClaw built-in |

---

## 集成方案

### 方案 1: MemPalace 作为 OpenClaw MCP

```bash
pip install mempalace
claude mcp add mempalace -- python -m mempalace.mcp_server
```

**优势**: 获得 19 个 MemPalace 工具 + LCM 现有功能  
**劣势**: 两套系统并行，可能有冗余

### 方案 2: 融合架构

```
OpenClaw
  ├── LCM (Token Budget + Multi-Agent)
  │   ├── TokenBudget.ts
  │   ├── MultiAgentContext.ts
  │   └── TaskNotificationService.ts
  └── MemPalace (Storage + KG)
      ├── LanceDBStorageAdapter (替换 ChromaDB?)
      ├── Knowledge Graph (集成 SQLite KG)
      └── Wing/Room 结构 (作为 Scope)
```

**融合点**:
- LanceDB 替换 ChromaDB（OpenClaw 已有 LanceDB）
- Wing/Room 作为 LCM Scope（agent:${wing}:${room}）
- Knowledge Graph 作为 Multi-Agent 上下文共享
- AAAK 作为 Layer 1 压缩选项

### 方案 3: 各司其职

```
LCM → Token/截断/Multi-Agent (session 内)
MemPalace → 长期存储/KG/MCP (跨 session)
```

**分工**:
- LCM 处理 session 内上下文管理
- MemPalace 处理跨 session 长期记忆

---

## 建议融合方向

### 优先级 1: Knowledge Graph 集成

LCM 缺少时序实体关系追踪。MemPalace 的 SQLite KG 可以补充：

```typescript
// 在 MultiAgentContext 中集成 KG
class MultiAgentContext {
  kg: KnowledgeGraph;  // 新增
  
  async mergeResults(results: AgentResult[]) {
    // 记录实体关系
    for (const result of results) {
      this.kg.add_triple(result.agentId, "completed", result.task, {
        valid_from: Date.now()
      });
    }
  }
}
```

### 优先级 2: Wing/Room 作为 Scope

将 MemPalace 的 Wing/Room 结构映射到 LCM Scope：

```
LCM Scope: "agent:coder:session-1"
MemPalace Wing/Room: "wing_project/hall_facts/room_auth"
→ 融合: "wing:project/hall:facts/room:auth"
```

### 优先级 3: AAAK 作为 Layer 1 压缩选项

LCM 的 Layer 1（Critical facts）可以使用 AAAK 压缩：

```typescript
// LLMCompressor 支持 AAAK 模式
class LLMCompressor {
  compress(content: string, mode: "semantic" | "aaak") {
    if (mode === "aaak") {
      return AAAK.compress(content);  // ~170 tokens
    }
    // semantic compression via LLM
  }
}
```

---

## 总结

| 系统 | 定位 | 核心价值 |
|------|------|---------|
| **MemPalace** | 长期记忆系统 | 结构化存储、KG、MCP |
| **LCM** | 上下文管理 | Token 预算、截断、多 Agent |

**建议**：
1. **不替代** - 两系统互补而非替代
2. **融合 KG** - MemPalace KG 补充 LCM 多 Agent 上下文
3. **统一 Scope** - Wing/Room 结构作为 Scope 标准
4. **可选 AAAK** - 作为 Layer 1 压缩选项（目前 regresses，谨慎使用）

---

## 文件位置

| 系统 | 位置 |
|------|------|
| MemPalace | `pip install mempalace` |
| LCM Context Manager | `~/.openclaw/workspace/context-manager-impl/` |
| LCM Tools | OpenClaw built-in (lcm_grep/describe/expand) |

---

*对比生成时间: 2026-04-10T23:50:00+08:00*