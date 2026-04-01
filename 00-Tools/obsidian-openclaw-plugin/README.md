# OpenClaw Chat for Obsidian

在 Obsidian 中与 OpenClaw AI 助手实时对话的插件。

## 功能特性

- 🐾 **实时 WebSocket 连接** - 与 OpenClaw Gateway 保持长连接
- 💬 **侧边栏聊天面板** - 不离开 Obsidian 即可对话
- 💾 **保存对话记录** - 一键保存聊天记录到指定文件夹
- 🏷️ **AI 自动标签** - 让 OpenClaw 分析当前笔记并生成标签
- 🔐 **API Key 认证** - 支持从文件读取 API Key

## 安装

### 手动安装

1. 下载本插件的 release 文件
2. 解压到 `VaultFolder/.obsidian/plugins/openclaw-chat/`
3. 重启 Obsidian
4. 在设置中启用插件

### 开发安装

```bash
cd obsidian-openclaw-plugin
npm install
npm run dev
```

然后将编译后的文件复制到插件目录。

## 配置

在 Obsidian 设置中找到 "OpenClaw Chat"：

| 设置项 | 说明 | 默认值 |
|--------|------|--------|
| Gateway 地址 | OpenClaw WebSocket 地址 | `ws://localhost:3000/ws` |
| API Key 文件路径 | 存储 API Key 的文件 | `~/文档/openclaw-api-key.txt` |
| 聊天记录文件夹 | 保存对话的文件夹 | `ClawChats` |
| 自动保存对话 | 是否自动保存每次对话 | 关闭 |

## 使用方法

### 基础聊天

1. 点击左侧边栏的 🐾 图标打开聊天面板
2. 点击「连接」按钮连接到 OpenClaw
3. 在输入框输入消息，按 `Shift+Enter` 发送

### 保存对话

点击「保存对话」按钮，当前对话会被保存到 `ClawChats/YYYY-MM-DD.md`。

### AI 标签功能

1. 在 Obsidian 中打开任意笔记
2. 点击「AI标签」按钮
3. OpenClaw 会分析笔记内容并返回建议的标签

## 快捷键

- `Shift+Enter` - 发送消息

## 开发

### 构建

```bash
npm run build
```

### 开发模式（热重载）

```bash
npm run dev
```

## 文件结构

```
obsidian-openclaw-plugin/
├── manifest.json      # 插件配置
├── main.ts            # 主代码
├── styles.css         # 样式
├── package.json       # 依赖
├── tsconfig.json      # TypeScript 配置
└── esbuild.config.mjs # 构建配置
```

## 协议

MIT
