# 🤖 多 Agent 合作框架调研报告

**调研时间**: 2026-03-17  
**调研范围**: GitHub 开源项目（大企业和研究院优先）

---

## 📊 顶级项目总览

| 项目 | 机构 | Stars | Forks | 语言 | 活跃度 |
|------|------|-------|-------|------|--------|
| **AutoGen** | Microsoft | 55.7k | 8.4k | Python 61% | ⭐⭐⭐⭐⭐ (5 天前) |
| **LangGraph** | LangChain | - | - | Python | ⭐⭐⭐⭐⭐ |
| **OxyGent** | jd-opensource | 1.9k | - | Python | ⭐⭐⭐⭐⭐ (29 分钟前) |
| **NagaAgent** | RTGS2017 | 1.5k | - | Python | ⭐⭐⭐⭐⭐ (13 小时前) |
| **Agent-MCP** | rinadelph | 1.2k | - | TypeScript | ⭐⭐⭐⭐ (25 天前) |
| **LightAgent** | wanxingai | 693 | - | Python | ⭐⭐⭐⭐ (12 天前) |

---

## 🏆 重点推荐项目

### 1. Microsoft AutoGen ⭐⭐⭐⭐⭐

**仓库**: https://github.com/microsoft/autogen

**核心特性**:
- ✅ **多层架构**: Core API → AgentChat API → Extensions API
- ✅ **多语言支持**: Python + .NET
- ✅ **协作模式**: 
  - Two-agent chat (对话式)
  - Group chat (群聊式)
  - AgentTool (工具调用式)
- ✅ **MCP 集成**: 支持 Model Context Protocol
- ✅ **AutoGen Studio**: 无代码 GUI
- ✅ **Magentic-One**: 多 agent 团队（网页浏览 + 代码执行 + 文件处理）

**安装**:
```bash
pip install -U "autogen-agentchat" "autogen-ext[openai]"
pip install -U "autogenstudio"  # GUI
```

**核心代码示例**:
```python
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.tools import AgentTool
from autogen_ext.models.openai import OpenAIChatCompletionClient

# 创建专家 agent
math_agent = AssistantAgent(
    "math_expert", 
    model_client=model_client,
    system_message="You are a math expert.",
)

# Agent 作为工具
math_agent_tool = AgentTool(math_agent, return_value_as_last_message=True)

# 主 agent 调用专家
agent = AssistantAgent(
    "assistant",
    tools=[math_agent_tool],
    max_tool_iterations=10,
)
```

**适用场景**:
- ✅ 复杂任务分解
- ✅ 多角色协作
- ✅ 人机协同
- ✅ 工具链编排

**生态工具**:
- AutoGen Studio (GUI)
- AutoGen Bench (基准测试)
- Magentic-One (现成多 agent 团队)

---

### 2. LangGraph (LangChain) ⭐⭐⭐⭐⭐

**仓库**: https://github.com/langchain-ai/langgraph

**核心特性**:
- ✅ **图结构编排**: 基于状态机的 agent 流程
- ✅ **持久化**: 支持 long-running 对话
- ✅ **人类介入**: Human-in-the-loop
- ✅ **流式执行**: 支持 stream 输出

**适用场景**:
- ✅ 工作流编排
- ✅ 需要状态管理的场景
- ✅ 复杂决策树

---

### 3. OxyGent ⭐⭐⭐⭐

**仓库**: https://github.com/jd-opensource/OxyGent

**核心特性**:
- ✅ Multi-agent collaboration framework
- ✅ 最近活跃 (29 分钟前更新)
- ✅ Python 实现

---

### 4. NagaAgent ⭐⭐⭐⭐

**仓库**: https://github.com/RTGS2017/NagaAgent

**核心特性**:
- ✅ Personal assistant framework
- ✅ Multi-agent collaboration
- ✅ ToolCall 支持
- ✅ MCP 集成
- ✅ 最近更新 (13 小时前)

---

### 5. Agent-MCP ⭐⭐⭐⭐

**仓库**: https://github.com/rinadelph/Agent-MCP

**核心特性**:
- ✅ Model Context Protocol 原生支持
- ✅ TypeScript 实现
- ✅ 多 agent 协调

---

## 🎓 研究院项目

### 学术论文相关

1. **MACRec** (SIGIR 2024)
   - 仓库：https://github.com/wzf2000/MACRec
   - 多 agent 协作推荐系统框架
   - 113 stars

2. **MAM** (医疗诊断)
   - 仓库：https://github.com/yczhou001/MAM
   - 模块化多 agent 医疗诊断
   - 39 stars

3. **FinTalk.v** (金融任务)
   - 仓库：https://github.com/boris-dotv/fintalk.v
   - 金融领域多 agent 协作
   - 39 stars

---

## 🔧 技术对比

| 特性 | AutoGen | LangGraph | CrewAI | OpenClaw |
|------|---------|-----------|--------|----------|
| 多层架构 | ✅ | ✅ | ❌ | ❌ |
| 多语言 | ✅ (Python+.NET) | ❌ | ❌ | ❌ |
| GUI 工具 | ✅ (Studio) | ❌ | ❌ | ❌ |
| MCP 支持 | ✅ | ✅ | ⚠️ | ✅ |
| 状态管理 | ⚠️ | ✅ | ❌ | ⚠️ |
| 人类介入 | ✅ | ✅ | ✅ | ❌ |
| 流式输出 | ✅ | ✅ | ✅ | ✅ |
| 工具调用 | ✅ | ✅ | ✅ | ✅ |
| 记忆系统 | ✅ | ✅ | ✅ | ✅ (MemQ) |

---

## 💡 设计模式

### 1. Hierarchical Orchestration (分层编排)

```
User → Coordinator Agent → Specialist Agents → Tools
```

**AutoGen 实现**:
```python
coordinator = AssistantAgent("coordinator", system_message="Coordinate experts")
math_expert = AssistantAgent("math_expert")
code_expert = AssistantAgent("code_expert")

# Coordinator 调用专家
coordinator.tools = [AgentTool(math_expert), AgentTool(code_expert)]
```

### 2. Peer-to-Peer Chat (对等对话)

```
Agent A ↔ Agent B ↔ Agent C
```

**AutoGen 实现**:
```python
from autogen_agentchat.teams import RoundRobinGroupChat

team = RoundRobinGroupChat([agent1, agent2, agent3])
await team.run(task="Solve this problem together")
```

### 3. Workflow Pipeline (工作流管道)

```
Input → Agent1 → Agent2 → Agent3 → Output
```

**LangGraph 实现**:
```python
from langgraph.graph import StateGraph

workflow = StateGraph(State)
workflow.add_node("agent1", agent1_func)
workflow.add_node("agent2", agent2_func)
workflow.add_edge("agent1", "agent2")
```

### 4. Tool-Based Collaboration (工具协作)

```
Main Agent → [Tool: Agent A, Tool: Agent B]
```

**AutoGen 实现**:
```python
agent_tool = AgentTool(specialist_agent, return_value_as_last_message=True)
main_agent.tools = [agent_tool]
```

---

## 🎯 与 OpenClaw 集成建议

### 方案 A：借鉴 AutoGen 架构

**Core API** → 现有的 `sessions_spawn` + `subagents`
**AgentChat API** → 新的高级编排层
**Extensions API** → 现有的插件系统

**实现**:
```python
# OpenClaw AgentChat
from openclaw.agents import CoordinatorAgent, SpecialistAgent

coordinator = CoordinatorAgent(
    "task_coordinator",
    specialists=[
        SpecialistAgent("coder", tools=["exec", "write"]),
        SpecialistAgent("researcher", tools=["web_search", "web_fetch"]),
    ]
)

await coordinator.run(task="帮我创建一个多 agent 协作系统")
```

### 方案 B：集成 AutoGen

直接使用 AutoGen 作为 OpenClaw 的多 agent 引擎：

```bash
pip install autogen-agentchat
```

**OpenClaw 插件**:
```python
# openclaw-autogen 插件
from autogen_agentchat.agents import AssistantAgent

@api.registerTool("autogen_team")
async def create_team(params):
    team = RoundRobinGroupChat([...])
    return await team.run(task=params.task)
```

### 方案 C：参考 LangGraph 状态机

为 OpenClaw 添加状态管理：

```python
# 状态定义
class AgentState:
    current_task: str
    completed_steps: List[str]
    pending_actions: List[str]
    results: Dict

# 状态转换
@agent.on("task_received")
async def handle_task(event, state):
    state.pending_actions.append(event.task)
    return state
```

---

## 📋 最佳实践总结

### 1. 角色设计

- **Coordinator/Manager**: 任务分解和分配
- **Specialist/Expert**: 特定领域专家
- **Critic/Reviewer**: 质量检查
- **Executor**: 实际执行

### 2. 通信模式

- **Direct Message**: 一对一
- **Broadcast**: 一对多
- **Shared Memory**: 共享状态
- **Message Queue**: 异步队列

### 3. 冲突解决

- **Voting**: 投票决策
- **Priority**: 优先级排序
- **Human Review**: 人工审核
- **Consensus**: 共识机制

### 4. 性能优化

- **Parallel Execution**: 并行执行
- **Caching**: 结果缓存
- **Lazy Loading**: 延迟加载
- **Batch Processing**: 批处理

---

## 🚀 下一步行动

### 短期 (1-2 周)

1. **学习 AutoGen 架构**
   - 阅读文档：https://microsoft.github.io/autogen/
   - 运行示例代码
   - 测试 AutoGen Studio

2. **设计 OpenClaw 多 agent API**
   - 定义 Coordinator Agent
   - 实现 Specialist Agent
   - 添加 AgentTool 支持

3. **实现基础协作模式**
   - Two-agent chat
   - Round-robin group chat
   - Hierarchical orchestration

### 中期 (1 个月)

1. **状态管理系统**
   - 实现 AgentState
   - 添加持久化支持
   - 支持 human-in-the-loop

2. **工具链编排**
   - 工具自动发现
   - 工具组合优化
   - 错误恢复机制

3. **可视化界面**
   - 参考 AutoGen Studio
   - 实现 workflow 编辑器
   - 添加调试工具

### 长期 (3 个月)

1. **生态系统建设**
   - 第三方 agent 市场
   - 模板库
   - 基准测试

2. **性能优化**
   - 分布式执行
   - 负载均衡
   - 自动扩缩容

---

## 📚 参考资料

- **AutoGen**: https://github.com/microsoft/autogen
- **AutoGen 文档**: https://microsoft.github.io/autogen/
- **AutoGen Studio**: https://github.com/microsoft/autogen/tree/main/python/packages/autogen-studio
- **LangGraph**: https://github.com/langchain-ai/langgraph
- **CrewAI**: https://github.com/crewAIInc/crewAI

---

**报告生成**: Kaguya  
**最后更新**: 2026-03-17 10:54
