# MEMORY.md - Kaguya 的长期记忆

_最后更新：2026-03-31_

---

## 🧠 核心记忆

### Clawteam 委托策略（2026-03-26 确立）

**核心规则**：主 Agent 只负责验收和监控，不执行具体任务

**触发条件**：
- 数据获取失败、模块报错、代码调试
- 批量操作 (>3个)、研究任务、代码重构、测试生成

**验收标准**：
- 任务完成、无工具调用异常、输出质量合格、无幻觉

**升级条件**：同一任务 2 次失败 → 主 Agent 接手

**文档**：`CLAWTEAM_DELEGATION.md`

---

### MemQ → OpenClaw 集成（2026-03-26 完成）

**架构**：
```
OpenClaw Gateway
    └── memory-lancedb-pro 插件
            └── openclaw_plugin.py
                    └── MemQProOptimized
```

**修复的问题**：
- BM25 中文分词：使用 `_tokenize()` 按字符分割
- async/sync 兼容：使用 `run_async()` 安全运行协程
- aiohttp session 生命周期：每次创建新 session

**嵌入配置**：
- Provider: `openai-compatible` (阿里云)
- Model: `text-embedding-v3`
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Dimensions: 1024

**文件**：
- `~/.openclaw/workspace/memq/plugins/memq_pro_optimized.py`
- `~/.openclaw/plugins/memory-lancedb-pro/openclaw_plugin.py`

---

### DSS选股系统 v4.3（2026-03-25 完成）

**项目定位**：智能选股系统（技术面+基本面+情绪分析+去噪）

**模块架构**：
```
dss_v4.py                    # 主程序
dss_modules/
├── data_loader.py           # 数据获取
├── features.py              # 技术指标计算
├── models.py                # ML模型
├── financial_data_store.py  # 金融数据存储（新增）
├── news_crawler.py          # 新浪财经新闻
├── eastmoney_crawler.py     # 东方财富研报+资金流向
├── seeking_alpha_crawler.py # 中概股分析
├── research_report_crawler.py # 研报摘要
├── browser_search_cli.py    # 浏览器搜索CLI (v2.0 并行优化)
└── news_sentiment.py        # 情绪分析
denoiser/                    # 去噪模块
```

**金融数据架构**：
- 不可变存储：内容寻址，SHA256哈希命名
- 版本控制：时间旅行查询，版本快照
- 血缘追踪：完整加工链记录
- 追加更正：审计合规，不覆盖历史

**核心改进**：
- 去噪：Kalman滤波 (Q=0.005, R=0.5)，MACD稳定性+73%
- 准确率：54% → **58.2%** (+4%)
- 数据源：新浪+东方财富+Seeking Alpha，多源fallback
- 情绪分析：技术情绪(-40~+40) + 新闻情绪(-20~+20) + 资金流向(-15~+15)

**最佳参数**：
```python
Denoiser(method='kalman', process_noise=0.005, measurement_noise=0.5)
RSI周期: 9 (默认14)
MACD: (15, 30, 9) (默认12,26,9)
```

---

### Kimi CLI 集成（2026-03-25 完成）

**集成方式**：使用Kimi账号额度，非百炼API

**文件**：
- `kimi_runner.py` - Print模式封装
- `kimi_wire.py` - Wire模式封装（JSON-RPC）
- `kimi_memq_agent.py` - 持久化记忆Agent
- `kimi-dss-agent/` - Agent配置目录

**使用**：
```python
from kimi_memq_agent import KimiMemQAgent
agent = KimiMemQAgent()
result = agent.chat("问题")  # 带记忆的对话
result = agent.analyze_stock('sh.600519')  # 股票分析
```

**Wire模式**：结构化双向通信，JSON-RPC 2.0协议

---

### Denoiser 去噪模块（2026-03-24 完成）

**支持方法**：
| 方法 | 特点 | 推荐场景 |
|------|------|----------|
| Kalman | 实时性好 | DSS系统首选 |
| Wavelet | 细节保留 | 价格保真度高 |
| SSA | 趋势分离 | 趋势/季节性分析 |
| EMD | 自适应 | 非平稳信号 |
| VMD | 模态清晰 | 多周期分析 |

**测试结果**：SSA SNR=14.1dB最高，Kalman MSE最低

---

### MemQ Pro 项目（2026-03-16 完成）

**项目定位**：混合检索记忆系统（向量 + BM25 + 质量评分）

**关键成果**：
- Recall@1: 90%（+50% vs BM25）
- Recall@3/5: 100%
- 噪声识别：90.9%

**仓库**：https://github.com/3452808350-max/MemQ

---

## 📝 待办事项

- [ ] 横盘检测逻辑优化（当前准确率0%）
- [ ] 国际视角情绪异步化
- [x] ~~浏览器搜索CLI速度优化~~ ✅ 2026-03-27
- [x] ~~MemQ 中文分词修复~~ ✅ 2026-03-26
- [x] ~~MemQ 阿里云嵌入集成~~ ✅ 2026-03-26
- [x] ~~Clawteam 委托策略~~ ✅ 2026-03-26

---

## 🔐 敏感信息（仅主会话可见）

- Kimi Remote API Token: `kimi-remote-api-token-2026`
- Kimi Remote API 部署：106.53.186.90，SSH 隧道本地端口 5000
- 密码文件位置：`/home/kyj/文档/pawsswd.md`（注意拼写）
- Notes仓库：git@github.com:3452808350-max/notes.git

---

_这份记忆由 Kaguya 维护，随时间不断更新。_