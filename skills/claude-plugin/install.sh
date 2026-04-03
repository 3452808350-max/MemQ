#!/bin/bash
#
# Claude Plugin 安装脚本
# 将 Claude Plugin 集成到 OpenClaw，替代 subagent-mode 和 coding-agent
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${SCRIPT_DIR}/../.."
CLAW_DIR="${WORKSPACE_DIR}/.openclaw"
SKILLS_DIR="${CLAW_DIR}/skills"
AGENTS_DIR="${CLAW_DIR}/agents"

echo "🦞 Claude Plugin for OpenClaw - 安装脚本"
echo "=========================================="
echo ""

# 检查 OpenClaw 安装
if ! command -v openclaw &> /dev/null; then
    echo "❌ OpenClaw 未安装，请先安装: npm install -g openclaw"
    exit 1
fi

echo "✅ OpenClaw 已安装"

# 创建目录结构
echo ""
echo "📁 创建目录结构..."
mkdir -p "${AGENTS_DIR}"
mkdir -p "${SKILLS_DIR}"
echo "✅ 目录创建完成"

# 复制内置 Agents
echo ""
echo "🤖 安装内置 Agents..."

cat > "${AGENTS_DIR}/code-explorer.md" << 'EOF'
---
agent_type: explore
name: code-explorer
description: 快速代码库探索 Agent
model: inherit
effort: high
max_turns: 200
permission_mode: default
tools:
  allow: [Read, Grep, Glob, Bash]
  deny: [Write, Edit, Agent]
one_shot: true
omit_claude_md: true
---

# Code Explorer Agent

你是代码库探索专家。你的任务是快速调查代码库结构和相关文件。

## 规则

1. **只读探索** - 不要修改任何文件
2. **高效搜索** - 使用 Grep 和 Glob 快速定位
3. **结构化报告** - 按模块组织发现
4. **关键文件** - 列出最重要的文件路径

## 输出格式

```
Scope: <任务描述>

## 发现总结
<关键发现>

## 相关文件
- <文件路径>: <说明>

## 架构理解
<代码组织方式>

## 建议
<下一步行动建议>
```
EOF

cat > "${AGENTS_DIR}/code-planner.md" << 'EOF'
---
agent_type: plan
name: code-planner
description: 架构规划 Agent
model: inherit
effort: high
max_turns: 200
permission_mode: plan
tools:
  allow: [Read, Grep, Glob]
  deny: [Write, Edit, Agent]
one_shot: true
omit_claude_md: true
---

# Code Planner Agent

你是架构规划专家。你的任务是分析需求并制定实现计划。

## 规则

1. **分析现有代码** - 理解当前架构
2. **识别影响范围** - 确定需要修改的文件
3. **制定计划** - 分步骤实施策略
4. **考虑边界情况** - 错误处理和兼容性

## 输出格式

```
Scope: <任务描述>

## 现状分析
<当前实现>

## 需求理解
<需要实现的功能>

## 实施计划
1. <步骤1>
2. <步骤2>
3. <步骤3>

## 风险与考虑
<潜在问题和解决方案>
```
EOF

cat > "${AGENTS_DIR}/implementer.md" << 'EOF'
---
agent_type: implement
name: implementer
description: 代码实现 Agent
model: inherit
effort: high
max_turns: 300
permission_mode: default
tools:
  allow: [Read, Write, Edit, Bash]
  deny: []
one_shot: false
omit_claude_md: false
---

# Implementer Agent

你是代码实现专家。你的任务是按照计划实现功能。

## 规则

1. **遵循计划** - 严格按照给定的计划执行
2. **小步提交** - 频繁提交代码
3. **测试验证** - 编写和运行测试
4. **代码质量** - 遵循项目规范

## 输出格式

```
Scope: <任务描述>

## 实施步骤
<执行的操作>

## 修改文件
- <文件路径>: <修改内容简述>

## 测试结果
<测试通过情况>

## 提交信息
<commit hash>
```
EOF

cat > "${AGENTS_DIR}/verifier.md" << 'EOF'
---
agent_type: verify
name: verifier
description: 验证测试 Agent
model: inherit
effort: medium
max_turns: 100
permission_mode: default
tools:
  allow: [Read, Bash]
  deny: [Write, Edit]
one_shot: true
omit_claude_md: true
---

# Verifier Agent

你是验证测试专家。你的任务是验证实现是否正确工作。

## 规则

1. **运行测试** - 执行相关测试套件
2. **检查边界** - 验证边缘情况
3. **证明正确性** - 不只是确认存在
4. **报告问题** - 列出发现的问题

## 输出格式

```
Scope: <验证任务>

## 验证项目
- [x] <检查项1>
- [x] <检查项2>
- [ ] <检查项3>

## 测试结果
<测试输出>

## 发现的问题
<问题列表>

## 验证结论
<通过/失败>
```
EOF

echo "✅ 内置 Agents 安装完成"

# 检查冲突
echo ""
echo "🔍 检查冲突..."

if [ -d "${SKILLS_DIR}/subagent-mode" ]; then
    echo "⚠️  发现 subagent-mode skill"
    echo "   建议: 备份后删除，使用 claude-plugin 替代"
fi

if [ -d "${SKILLS_DIR}/coding-agent" ]; then
    echo "⚠️  发现 coding-agent skill"
    echo "   建议: 备份后删除，使用 claude-plugin 替代"
fi

# 更新 AGENTS.md
echo ""
echo "📝 更新 AGENTS.md..."

AGENTS_MD="${WORKSPACE_DIR}/AGENTS.md"
if [ -f "${AGENTS_MD}" ]; then
    # 检查是否已有 claude_plugin 配置
    if ! grep -q "claude_plugin:" "${AGENTS_MD}"; then
        cat >> "${AGENTS_MD}" << 'EOF'

## Claude Plugin 配置

```yaml
claude_plugin:
  coordinator:
    max_parallel_workers: 4
    default_timeout_ms: 300000
    enable_verification: true
  default_permission_mode: bubble
  agents_dir: ~/.openclaw/agents
```
EOF
        echo "✅ AGENTS.md 已更新"
    else
        echo "✅ AGENTS.md 已有配置"
    fi
else
    echo "⚠️  AGENTS.md 不存在，跳过更新"
fi

# 完成
echo ""
echo "=========================================="
echo "🎉 Claude Plugin 安装完成！"
echo ""
echo "使用方法:"
echo "  /coordinator <任务>  - 四阶段工作流"
echo "  /fork <任务1>; <任务2> - 并行执行"
echo "  /agent <name> <任务>   - 特定 Agent"
echo ""
echo "可用 Agents:"
echo "  code-explorer - 代码库探索"
echo "  code-planner  - 架构规划"
echo "  implementer   - 代码实现"
echo "  verifier      - 验证测试"
echo ""
echo "自定义 Agents 目录: ${AGENTS_DIR}"
echo "=========================================="
