# Claude Plugin for OpenClaw

将 Claude Code 的多 Agent 架构移植为 OpenClaw 插件

## 模块拆分

```
claude-plugin/
├── modules/
│   ├── 01-agent-definitions/      # Agent 定义格式 (最高优先级)
│   ├── 02-fork-subagent/          # Fork Subagent 优化
│   ├── 03-task-notification/      # Task Notification 协议
│   ├── 04-message-passing/        # Agent 间消息传递
│   ├── 05-coordinator-mode/       # Coordinator Mode (最复杂)
│   └── 06-permission-system/      # Permission 规则引擎
├── tests/
│   └── module-*/
└── docs/
    └── architecture.md
```

## 依赖关系

```
01-agent-definitions (基础)
        ↓
02-fork-subagent ───→ 03-task-notification
        ↓                    ↓
04-message-passing ←────────┘
        ↓
05-coordinator-mode (依赖 01-04)
        ↓
06-permission-system (可选增强)
```

## 开发顺序

1. **Module 01**: Agent 定义格式 - 基础设施
2. **Module 02**: Fork Subagent - 高频使用，性能关键
3. **Module 03**: Task Notification - 核心协议
4. **Module 04**: Message Passing - Agent 间通信
5. **Module 05**: Coordinator Mode - 完整编排
6. **Module 06**: Permission System - 安全增强

## 每个模块结构

```
modules/XX-module-name/
├── spec.md              # 模块规格说明书
├── implementation.md    # 实现细节
├── openclaw-api.ts      # OpenClaw API 包装
├── tests/
│   ├── unit.test.ts
│   └── integration.test.ts
└── examples/
    └── example-*.ts
```
