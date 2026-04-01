# 📁 项目导航指南

> 最后更新：2026-04-01
> 用途：快速定位项目文件

---

## 🗂️ 目录结构

```
~/.openclaw/workspace/
├── 00-Archive/          # 归档、备份、历史代码
├── 00-Data/             # 数据、缓存、日志、记忆
├── 00-Docs/             # 文档、笔记、学习资料
├── 00-Projects/         # 核心项目代码 ⭐
├── 00-Reports/          # 报告、总结、分析文档
├── 00-Scripts/          # 工具脚本、辅助程序
└── 00-Tools/            # 插件、服务、工具
```

---

## 🚀 核心项目 (00-Projects/)

| 项目 | 路径 | 说明 |
|------|------|------|
| **DSS 选股系统** | `dss_modules/` | 智能选股系统 v4.3，准确率 58.2% |
| **MemQ 记忆** | `memq/` | 混合检索记忆系统，Recall@1 90% |
| **Kimi Agent** | `kimi-dss-agent/` | Kimi 集成 Agent |
| **ClawTeam** | `ClawTeam/` | 委托系统，主 Agent 只验收 |
| **OpenClaw** | `openclaw/` | OpenClaw 核心代码 |
| **去噪模块** | `denoiser/` | Kalman/SSA/Wavelet 信号去噪 |
| **DSS 配置** | `dss-project/` | 项目规范和技能定义 |
| **Skills** | `skills/` | OpenClaw 技能目录 |
| **Tests** | `tests/` | 测试用例 |
| **.agents** | `.agents/` | Agent 配置 |

### 快速启动
```bash
# DSS 选股
cd ~/.openclaw/workspace/00-Projects/dss_modules && python dss_v4.py

# MemQ 测试
cd ~/.openclaw/workspace/00-Projects/memq && python benchmark.py

# ClawTeam 委托
cat ~/.openclaw/workspace/00-Projects/ClawTeam/CLAWTEAM_DELEGATION.md
```

---

## 📊 数据目录 (00-Data/)

| 目录 | 内容 |
|------|------|
| `data/` | 通用数据 |
| `data_cache/` | 缓存数据 |
| `data_logs/` | 日志文件 |
| `dss_data/` | DSS 选股数据 |
| `lancedb/` | 向量数据库 |
| `memory/` | 记忆文件 |
| `PerLTQA/` | PerLTQA 数据集 |
| `synthetic_perltqa/` | 合成数据集 |

---

## 📝 文档 (00-Docs/)

| 目录 | 内容 |
|------|------|
| `docs/` | OpenClaw 官方文档 |
| `everything-claude-code/` | Claude Code 架构分析 |
| `ielts_materials/` | IELTS 学习资料 |
| `notes/` | 个人笔记 |
| `writing/` | 写作练习 |

---

## 🔧 脚本 (00-Scripts/)

常用脚本快速查找：

| 功能 | 文件名 |
|------|--------|
| GitHub 自动推送 | `auto_push_github.sh` |
| 内存归档 | `auto_archive_memory.py` |
| Git 同步 | `ai_git_sync.py` |
| 上下文清理 | `cleanup_context.sh` |
| 配置 Ollama | `configure_ollama_lan.sh` |
| 安装 Watchdog | `install_watchdog.sh` |

---

## 🛠️ 工具 (00-Tools/)

| 工具 | 说明 |
|------|------|
| `cli-anything/` | CLI 工具 |
| `obsidian-openclaw-plugin/` | Obsidian 插件 |
| `openclaw-maintenance-skill/` | 维护技能 |
| `openclaw-min-bundle/` | 最小包 |
| `dsd-player/` | DSD 播放器 |
| `tools/` | 通用工具 |
| `kimi_tool.js` | Kimi CLI 工具 |

---

## 📈 报告 (00-Reports/)

按主题分类：
- `DSS_*` - DSS 选股系统报告
- `KIMI_*` - Kimi 集成报告
- `MEMORY_*` - 记忆系统报告
- `MINIMAX_*` - MiniMax 测试报告
- `PERFORMANCE_*` - 性能优化报告
- `PROJECT_*` - 项目总结
- `SECURITY_*` - 安全事件报告
- `WEBDAV_*` - WebDAV 配置报告
- `GPU_*` / `AMD_*` / `ROCm_*` - GPU 相关
- `SSH_*` / `DEBIAN_*` - 服务器配置

---

## 🗃️ 归档 (00-Archive/)

| 内容 | 说明 |
|------|------|
| `claude-code-leaked/` | Claude Code 源代码（敏感） |
| `analysis/` | 旧分析文件 |
| `archive/` | 归档文件 |
| `temp_memory/` | 临时记忆 |
| `notes_test/` | 测试笔记 |
| `*.zip` / `*.tar.gz` | 压缩包 |

---

## 🔗 快捷方式 (~/)

```bash
~/evolver      → ~/.openclaw/workspace/00-Projects/evolver
~/qlib         → ~/.openclaw/workspace/00-Projects/qlib
~/RD-Agent     → ~/.openclaw/workspace/00-Projects/RD-Agent
```

---

## ⚡ 常用命令

```bash
# 查看最新 DSS 报告
cat ~/.openclaw/workspace/00-Reports/DSS_V4_IMPROVEMENTS.md

# 查看记忆状态
cat ~/.openclaw/workspace/00-Data/memory/MEMORY.md

# 运行 DSS 快速选股
cd ~/.openclaw/workspace/00-Projects/dss_modules && python dss_quick_pick.py

# 查看待办
grep -r "TODO\|FIXME\|待办" ~/.openclaw/workspace/00-Projects/ 2>/dev/null | head -10

# 搜索报告
grep -l "关键词" ~/.openclaw/workspace/00-Reports/*.md
```

---

## 📌 待办事项

来自 MEMORY.md：
- [ ] 横盘检测逻辑优化（当前准确率0%）
- [ ] 国际视角情绪异步化

---

*这份指南由我维护，项目结构调整时同步更新。*
