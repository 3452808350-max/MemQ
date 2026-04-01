# DSS Browser Search CLI

浏览器自动化搜索CLI，使用Playwright进行真实的浏览器操作。

## 功能

- **Seeking Alpha** - 搜索中概股分析文章
- **Yahoo Finance** - 获取股票报价和相关新闻
- **Google Finance** - 获取股票数据和相关新闻
- **财经新闻** - 搜索Google News或Bing News

## 安装

```bash
# 安装依赖
pip install playwright click beautifulsoup4 lxml

# 安装浏览器
playwright install chromium

# 安装CLI（可选，用于全局命令）
cd /home/kyj/.openclaw/workspace/dss_modules
pip install -e .
```

## 命令

### 搜索Seeking Alpha分析文章

```bash
# 直接运行
python browser_search_cli.py seeking-alpha BABA

# 全局命令（安装后）
browser-search seeking-alpha BABA
browser-search seeking-alpha AAPL --json
```

### 搜索Yahoo Finance

```bash
browser-search yahoo-finance AAPL
browser-search yahoo-finance TSLA --json
```

### 搜索Google Finance

```bash
browser-search google-finance GOOGL
browser-search google-finance MSFT --json
```

### 搜索财经新闻

```bash
browser-search news "中概股"
browser-search news "AAPL earnings" --source bing
browser-search news "美联储" --limit 5
```

### 综合搜索

```bash
browser-search all BABA
browser-search all TSLA --json
```

## 选项

- `--json` - 输出JSON格式
- `--limit N` - 最大结果数（默认10）
- `--headful` - 显示浏览器窗口（调试用）
- `--timeout MS` - 页面加载超时（默认30000毫秒）

## 反爬措施

1. **真实浏览器行为** - 使用Playwright的Chromium浏览器
2. **随机延迟** - 每次请求间隔2-5秒
3. **User-Agent轮换** - 随机选择常见浏览器UA
4. **请求头伪装** - 模拟真实浏览器请求头
5. **人类行为模拟** - 随机滚动和鼠标移动
6. **JavaScript注入** - 隐藏webdriver属性

## 作为模块使用

```python
from browser_search_cli import BrowserSearchCLI
import asyncio

async def main():
    cli = BrowserSearchCLI(headless=True)
    
    # 搜索Seeking Alpha
    sa_result = await cli.search_seeking_alpha("BABA")
    print(f"Found {sa_result.total} articles")
    
    # 搜索Yahoo Finance
    yf_result = await cli.search_yahoo_finance("AAPL")
    if yf_result.results:
        quote = yf_result.results[0]
        print(f"Price: ${quote.price}")
    
    await cli.close()

asyncio.run(main())
```

## 输出示例

### Yahoo Finance

```
============================================================
Yahoo Finance: AAPL
============================================================

📈 AAPL - Apple Inc.
    价格: $178.72 (+1.23%)
    市值: 2.8T
    P/E: 29.45
    成交量: 52.3M
    52周区间: 124.17 - 199.62

📰 相关新闻:

  【1】Apple's AI Strategy Takes Shape
      日期: 2 hours ago
      来源: Reuters
      链接: https://finance.yahoo.com/news/...
```

### Seeking Alpha

```
============================================================
Seeking Alpha 分析文章: BABA
============================================================

【1】Alibaba: AI Cloud Growth Accelerates
    作者: Investment Research
    评级: Strong Buy
    日期: 2026-03-24
    摘要: Alibaba's cloud division shows strong momentum in AI infrastructure...
    链接: https://seekingalpha.com/article/...

【2】BABA Stock: Value At These Levels?
    作者: Value Hunter
    评级: Buy
    日期: 2026-03-23
    摘要: With a P/E under 15, Alibaba presents compelling value for long-term...
    链接: https://seekingalpha.com/article/...
```

## 注意事项

1. 首次运行需要安装Playwright浏览器：`playwright install chromium`
2. 某些网站可能有登录要求或验证码
3. 建议设置合理的请求间隔，避免被封禁
4. 使用`--headful`选项可以看到浏览器操作过程，便于调试

## 故障排除

### Playwright未安装

```
❌ 错误: Playwright 未安装

请运行以下命令安装:
  pip install playwright
  playwright install chromium
```

### 浏览器启动失败

```bash
# 安装系统依赖
playwright install-deps chromium

# 或者使用系统浏览器
playwright install chromium
```

### 反爬检测

如果遇到反爬检测，可以：
1. 增加`--timeout`参数
2. 使用`--headful`模式观察
3. 增加请求间隔

## License

MIT License