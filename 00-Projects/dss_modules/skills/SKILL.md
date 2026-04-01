---
name: "dss-browser-search"
description: "DSS浏览器自动化搜索CLI - 使用Playwright搜索Seeking Alpha、Yahoo Finance、Google Finance和财经新闻。支持反爬检测绕过。"
---

# dss-browser-search

浏览器自动化搜索CLI，使用Playwright进行真实的浏览器操作。支持Seeking Alpha、Yahoo Finance、Google Finance和财经新闻搜索。

## 安装

```bash
# 安装依赖
pip install playwright click beautifulsoup4 lxml

# 安装浏览器
playwright install chromium

# 安装CLI
cd /home/kyj/.openclaw/workspace/dss_modules
pip install -e .
```

## 命令

### seeking-alpha - 搜索分析文章

```bash
browser-search seeking-alpha <SYMBOL>
browser-search seeking-alpha BABA
browser-search seeking-alpha AAPL --json
```

输出：
- 文章标题
- 作者
- 分析师评级
- 发布日期
- 摘要
- 链接

### yahoo-finance - 搜索股票数据

```bash
browser-search yahoo-finance <SYMBOL>
browser-search yahoo-finance AAPL
browser-search yahoo-finance TSLA --json
```

输出：
- 股票名称和价格
- 涨跌幅
- 市值、P/E、成交量
- 52周区间
- 相关新闻

### google-finance - 搜索股票数据

```bash
browser-search google-finance <SYMBOL>
browser-search google-finance GOOGL --json
```

### news - 搜索财经新闻

```bash
browser-search news <KEYWORD>
browser-search news "中概股"
browser-search news "AAPL earnings" --source bing
browser-search news "美联储" --limit 5
```

### all - 综合搜索

```bash
browser-search all <SYMBOL>
browser-search all BABA --json
```

同时搜索Yahoo Finance、Google Finance和Seeking Alpha。

## 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--json` | 输出JSON格式 | 否 |
| `--limit N` | 最大结果数 | 10 |
| `--headful` | 显示浏览器窗口（调试） | 否 |
| `--timeout MS` | 页面加载超时 | 30000 |

## 反爬措施

1. 真实Chromium浏览器
2. 随机延迟（2-5秒）
3. User-Agent轮换
4. 请求头伪装
5. 人类行为模拟（滚动、鼠标移动）
6. JavaScript注入隐藏webdriver

## 作为模块使用

```python
from browser_search_cli import BrowserSearchCLI
import asyncio

async def search_stock(symbol: str):
    cli = BrowserSearchCLI(headless=True, max_results=5)
    
    # 搜索多个来源
    yf = await cli.search_yahoo_finance(symbol)
    sa = await cli.search_seeking_alpha(symbol)
    
    await cli.close()
    return {
        "yahoo": yf.to_dict(),
        "seeking_alpha": sa.to_dict()
    }

result = asyncio.run(search_stock("BABA"))
```

## JSON输出格式

```json
{
  "query": "BABA",
  "source": "Seeking Alpha",
  "timestamp": "2026-03-25T09:45:00",
  "results": [
    {
      "title": "Alibaba: AI Cloud Growth",
      "url": "https://seekingalpha.com/article/...",
      "source": "Seeking Alpha",
      "snippet": "...",
      "date": "2026-03-24",
      "author": "Investment Research",
      "rating": "Strong Buy"
    }
  ],
  "total": 1,
  "success": true
}
```

## 故障排除

### Playwright未安装

```bash
pip install playwright
playwright install chromium
```

### 浏览器依赖缺失

```bash
playwright install-deps chromium
```

### 被反爬检测

1. 增加`--timeout`
2. 使用`--headful`观察
3. 增加请求间隔

## 与DSS集成

```python
# 在dss_modules中导入使用
from browser_search_cli import BrowserSearchCLI

# 集成到选股系统
async def get_stock_analysis(symbol: str):
    cli = BrowserSearchCLI()
    results = await cli.search_seeking_alpha(symbol)
    await cli.close()
    return results
```

## 链接

- [Playwright文档](https://playwright.dev/python/)
- [CLI-Anything](https://github.com/HKUDS/CLI-Anything)
- [Seeking Alpha](https://seekingalpha.com)
- [Yahoo Finance](https://finance.yahoo.com)
- [Google Finance](https://www.google.com/finance)