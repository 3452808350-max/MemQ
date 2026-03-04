# 网页信息获取方法汇总

> **整理时间**: 2026-03-04  
> **适用场景**: 雅思资料、外刊阅读、技术文档、数据分析

---

## 📋 方法总览

| 方法 | 工具 | 适用场景 | 难度 |
|------|------|---------|------|
| **web_fetch** | OpenClaw 工具 | 快速抓取网页文本 | ⭐ |
| **browser** | OpenClaw 工具 | 需要交互的网页 | ⭐⭐ |
| **Kimi Remote API** | Debian Server | 需要 AI 分析的网页 | ⭐⭐ |
| **RSS 订阅** | Feedly/Inoreader | 定期更新的外刊 | ⭐ |
| **API 接口** | 各网站官方 API | 结构化数据 | ⭐⭐⭐ |
| **Python 爬虫** | requests/BeautifulSoup | 批量抓取 | ⭐⭐⭐ |

---

## 1️⃣ web_fetch - 快速抓取

### 特点
- ✅ **最简单** - 一行命令
- ✅ **免费** - 无需配置
- ✅ **快速** - 直接返回 Markdown
- ❌ **局限** - 只能抓取静态内容

### 使用方式

```python
# OpenClaw 工具调用
web_fetch(
    url="https://www.theguardian.com/commentisfree",
    extractMode="markdown",  # 或 "text"
    maxChars=10000
)
```

### 适用场景
- 新闻文章
- 博客文章
- 技术文档
- 维基百科

### 示例

```
用户：帮我抓取这篇外刊
AI: 使用 web_fetch 工具获取 https://xxx.com/article
```

### 限制
- 无法处理 JavaScript 渲染的页面
- 无法登录验证
- 有反爬的网站可能失败

---

## 2️⃣ browser - 浏览器自动化

### 特点
- ✅ **功能强大** - 可交互、可截图
- ✅ **处理 JS** - 支持动态网页
- ✅ **可登录** - 可处理验证
- ❌ **较慢** - 需要启动浏览器
- ❌ **复杂** - 需要配置选择器

### 使用方式

```python
# 打开网页
browser(action="open", targetUrl="https://www.economist.com")

# 截图
browser(action="screenshot", fullPage=True)

# 点击元素
browser(action="act", request={
    "kind": "click",
    "ref": "article-title"
})

# 提取内容
browser(action="snapshot", refs="aria")
```

### 适用场景
- 需要登录的网站
- 动态加载的内容
- 需要截图的页面
- 复杂交互

### 示例

```
用户：帮我下载这篇付费文章
AI: 1. browser.open 打开网址
    2. browser.click 点击登录
    3. browser.type 输入账号密码
    4. browser.screenshot 截图保存
```

---

## 3️⃣ Kimi Remote API - 智能分析

### 特点
- ✅ **AI 分析** - 抓取 + 总结一步完成
- ✅ **代理支持** - 通过 Debian Server 访问国外网站
- ✅ **智能路由** - 国内直连，国外代理
- ❌ **依赖服务器** - 需要 Debian Server 运行
- ❌ **延迟较高** - 需要 SSH 隧道

### 架构

```
本地 OpenClaw
    ↓ SSH 隧道 (端口 5000)
Debian Server (106.53.186.90)
    ↓ Clash 代理 (智能路由)
目标网站 (国内直连/国外代理)
    ↓ 返回内容
Kimi AI 分析总结
    ↓ 返回结果
本地 OpenClaw
```

### 使用方式

```python
# 通过 SSH 调用
ssh root@106.53.186.90 "
curl http://localhost:5000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    \"prompt\": \"请抓取并总结 https://www.economist.com/latest-article\",
    \"session\": \"web-summary\"
  }'
"
```

### 适用场景
- 需要 AI 总结的长文章
- 需要访问的国外网站
- 批量处理多个网页
- 需要提取关键信息

### 示例

```
用户：帮我总结今天的经济学人文章
AI: 1. 通过 SSH 隧道调用 Kimi Remote API
    2. Kimi 访问网页并抓取内容
    3. Kimi 分析并总结要点
    4. 返回总结结果
```

---

## 4️⃣ RSS 订阅 - 定期更新

### 特点
- ✅ **自动更新** - 无需手动访问
- ✅ **结构化** - 标准格式
- ✅ **免费** - 大多数外刊提供
- ❌ **内容有限** - 通常只有摘要
- ❌ **需要聚合器** - 需要额外工具

### 推荐外刊 RSS

| 外刊 | RSS 地址 | 免费内容 |
|------|---------|---------|
| **BBC News** | http://feeds.bbci.co.uk/news/rss.xml | ✅ 全文 |
| **The Guardian** | https://www.theguardian.com/rss | ✅ 全文 |
| **Scientific American** | https://www.scientificamerican.com/rss/ | ⚠️ 摘要 |
| **The Economist** | https://www.economist.com/the-world-this-week/rss.xml | ⚠️ 摘要 |
| **Time** | http://rss.time.com/webfeeds/content/home.xml | ⚠️ 摘要 |

### 使用方式

```python
# 使用 feedparser 库
import feedparser
feed = feedparser.parse('https://www.theguardian.com/rss')
for entry in feed.entries:
    print(f"标题：{entry.title}")
    print(f"链接：{entry.link}")
    print(f"摘要：{entry.summary}")
```

### 适用场景
- 定期追踪外刊
- 批量获取最新文章
- 建立个人知识库

---

## 5️⃣ API 接口 - 结构化数据

### 特点
- ✅ **官方支持** - 稳定可靠
- ✅ **结构化** - JSON 格式
- ✅ **合法合规** - 符合使用条款
- ❌ **需要注册** - 需要 API Key
- ❌ **有限制** - 调用次数限制

### 推荐 API

| 服务 | API 地址 | 免费额度 |
|------|---------|---------|
| **NewsAPI** | https://newsapi.org/ | 500 次/天 |
| **Guardian Open Platform** | https://open-platform.theguardian.com/ | 5000 次/天 |
| **New York Times** | https://developer.nytimes.com/ | 500 次/天 |
| **Wikipedia** | https://www.mediawiki.org/wiki/API:Main_page | 无限制 |

### 使用方式

```python
import requests

# Guardian API
response = requests.get(
    'https://content.guardianapis.com/search',
    params={
        'api-key': 'your-api-key',
        'q': 'education',
        'order-by': 'newest'
    }
)
articles = response.json()['response']['results']
```

### 适用场景
- 新闻聚合
- 数据分析
- 批量获取文章
- 需要元数据（作者、时间等）

---

## 6️⃣ Python 爬虫 - 批量抓取

### 特点
- ✅ **灵活** - 可定制任何逻辑
- ✅ **批量** - 可抓取大量页面
- ✅ **自动化** - 可定时运行
- ❌ **技术门槛** - 需要编程能力
- ❌ **法律风险** - 需注意 robots.txt

### 推荐库

| 库 | 用途 | 难度 |
|------|------|------|
| **requests** | HTTP 请求 | ⭐ |
| **BeautifulSoup** | HTML 解析 | ⭐⭐ |
| **Scrapy** | 爬虫框架 | ⭐⭐⭐ |
| **Selenium** | 浏览器自动化 | ⭐⭐⭐ |
| **Playwright** | 现代浏览器自动化 | ⭐⭐⭐ |

### 示例代码

```python
import requests
from bs4 import BeautifulSoup

def fetch_article(url):
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取标题
    title = soup.find('h1').text.strip()
    
    # 提取正文
    content = '\n'.join([
        p.text for p in soup.find_all('p')
    ])
    
    return {
        'title': title,
        'content': content,
        'url': url
    }

# 使用
article = fetch_article('https://example.com/article')
print(article['title'])
```

### 适用场景
- 批量抓取外刊
- 建立语料库
- 数据分析项目
- 需要定制逻辑

---

## 🎯 方法选择指南

### 根据需求选择

| 需求 | 推荐方法 | 理由 |
|------|---------|------|
| **快速抓取单篇文章** | web_fetch | 最简单快速 |
| **需要登录的网站** | browser | 可处理验证 |
| **需要 AI 总结** | Kimi Remote API | 抓取 + 分析一步完成 |
| **定期追踪外刊** | RSS 订阅 | 自动更新 |
| **批量获取文章** | Python 爬虫 | 可定制批量逻辑 |
| **需要元数据** | API 接口 | 结构化数据 |
| **国外网站访问** | Kimi Remote API + Clash | 智能代理路由 |

### 根据难度选择

| 难度 | 方法 | 学习曲线 |
|------|------|---------|
| **⭐ 入门** | web_fetch, RSS | 无需编程 |
| **⭐⭐ 进阶** | browser, Kimi API, API 接口 | 基础编程 |
| **⭐⭐⭐ 高级** | Python 爬虫 | 完整开发能力 |

---

## 📊 性能对比

| 方法 | 速度 | 稳定性 | 成本 | 合法性 |
|------|------|--------|------|--------|
| **web_fetch** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 免费 | ✅ |
| **browser** | ⭐⭐ | ⭐⭐⭐⭐ | 免费 | ✅ |
| **Kimi API** | ⭐⭐⭐ | ⭐⭐⭐⭐ | 服务器成本 | ✅ |
| **RSS** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 免费 | ✅ |
| **API 接口** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 部分付费 | ✅ |
| **Python 爬虫** | ⭐⭐⭐ | ⭐⭐⭐ | 免费 | ⚠️ 需注意 |

---

## 🛠️ 我们当前的配置

### 已配置工具

| 工具 | 状态 | 位置 |
|------|------|------|
| **web_fetch** | ✅ 可用 | OpenClaw 内置 |
| **browser** | ✅ 可用 | OpenClaw 内置 |
| **Kimi Remote API** | ✅ 运行中 | Debian Server (106.53.186.90:5000) |
| **Clash 代理** | ✅ 运行中 | Debian Server (106.53.186.90:7890) |
| **SSH 隧道** | ✅ 已建立 | 本地 5000 → Debian Server 5000 |

### 推荐工作流

```
1. 简单文章 → web_fetch
2. 需要总结 → Kimi Remote API
3. 国外网站 → Kimi API + Clash 代理
4. 需要交互 → browser
5. 批量抓取 → Python 爬虫 (自建)
```

---

## 📝 使用示例

### 示例 1: 抓取外刊文章

```
用户：帮我抓取今天的卫报文章
AI: 使用 web_fetch 工具
     https://www.theguardian.com/latest-article
     提取模式：markdown
     返回：文章全文
```

### 示例 2: 总结经济学人

```
用户：总结这篇经济学人
AI: 通过 SSH 隧道调用 Kimi Remote API
     Kimi 访问网页 → 抓取内容 → AI 总结
     返回：300 字摘要 + 关键观点
```

### 示例 3: 访问付费内容

```
用户：下载这篇付费文章
AI: 使用 browser 工具
     1. 打开网页
     2. 登录账号
     3. 抓取内容
     4. 保存为 Markdown
```

### 示例 4: 批量获取外刊

```
用户：获取最近 10 篇雅思相关文章
AI: 使用 Python 脚本
     1. RSS 获取文章列表
     2. 循环调用 web_fetch
     3. 保存到本地目录
     4. 生成索引文件
```

---

## ⚠️ 注意事项

### 法律合规
- ✅ 遵守 robots.txt
- ✅ 尊重版权
- ✅ 控制抓取频率
- ❌ 不要抓取付费内容（除非有账号）
- ❌ 不要大规模抓取（可能被封 IP）

### 技术注意
- 设置 User-Agent
- 添加请求延迟
- 处理异常情况
- 缓存已抓取内容
- 使用代理（如需访问国外网站）

### 最佳实践
- 优先使用官方 API
- 其次使用 RSS
- 最后考虑爬虫
- 定期清理缓存
- 记录抓取日志

---

## 🔮 未来扩展

### 可添加的功能
- [ ] 自动摘要生成
- [ ] 多语言翻译
- [ ] 语音朗读（TTS）
- [ ] 知识图谱构建
- [ ] 定期自动抓取
- [ ] 内容分类标签

### 可集成的服务
- [ ] Pocket（稍后读）
- [ ] Notion（知识库）
- [ ] Obsidian（笔记）
- [ ] Feedly（RSS 聚合）
- [ ] IFTTT（自动化）

---

*整理完成时间：2026-03-04*  
*适用于：OpenClaw + Debian Server 架构*
