# Debian Server 爬虫部署指南

> **目标**: 在 Debian Server 上部署智能爬虫系统  
> **服务器**: Debian Server (106.53.186.90)  
> **日期**: 2026-03-04  
> **用途**: 外刊抓取、雅思资料、数据分析

---

## 🎯 部署优势

### 为什么部署在 Debian Server？

| 优势 | 说明 |
|------|------|
| **带宽优势** | 服务器带宽通常比家用宽带更稳定 |
| **代理集成** | 可直接使用 Clash 代理访问国外网站 |
| **24/7 运行** | 服务器不停机，可定时抓取 |
| **不占本地资源** | 爬虫运行不影响本地使用 |
| **IP 稳定性** | 服务器 IP 更稳定，不易被封 |

---

## 📋 爬虫架构

```
┌─────────────────┐
│  OpenClaw       │ (本地)
│  (Kaguya)       │
└────────┬────────┘
         │ SSH 调用
         ▼
┌─────────────────┐
│  Debian Server  │ (106.53.186.90)
│  ├─ Spider      │ (爬虫脚本)
│  ├─ Clash       │ (智能代理)
│  └─ Kimi API    │ (AI 分析)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   目标网站       │
│ (国内直连/      │
│  国外代理)      │
└─────────────────┘
```

---

## 🚀 快速部署

### 步骤 1: 安装 Python 依赖

```bash
#!/bin/bash
# install_dependencies.sh

echo "📦 安装爬虫依赖..."

apt update
apt install -y python3 python3-pip python3-venv

# 创建爬虫目录
mkdir -p /opt/spider
cd /opt/spider

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装核心库
pip install requests beautifulsoup4 lxml
pip install scrapy playwright
pip install feedparser newspaper3k

# 安装 Playwright 浏览器
playwright install chromium

echo "✅ 依赖安装完成"
```

---

### 步骤 2: 创建基础爬虫框架

```python
#!/usr/bin/env python3
"""
spider_base.py - 基础爬虫框架
支持智能代理、自动重试、内容提取
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import os
import time

class SmartSpider:
    """智能爬虫基类"""
    
    def __init__(self, use_proxy=False):
        """
        初始化爬虫
        
        Args:
            use_proxy: 是否使用代理（访问国外网站时启用）
        """
        self.use_proxy = use_proxy
        self.session = requests.Session()
        
        # 设置 User-Agent（避免被反爬）
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 配置代理（如果启用）
        if use_proxy:
            self.session.proxies.update({
                'http': 'http://127.0.0.1:7890',
                'https': 'http://127.0.0.1:7890'
            })
        
        # 输出目录
        self.output_dir = '/opt/spider/output'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def fetch(self, url, retry=3, timeout=30):
        """
        抓取网页
        
        Args:
            url: 目标 URL
            retry: 重试次数
            timeout: 超时时间
        
        Returns:
            HTML 内容
        """
        for i in range(retry):
            try:
                print(f"🕷️  抓取：{url}")
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                response.encoding = response.apparent_encoding
                return response.text
            except Exception as e:
                print(f"⚠️  抓取失败 ({i+1}/{retry}): {e}")
                if i < retry - 1:
                    time.sleep(2 ** i)  # 指数退避
                else:
                    raise
        
        return None
    
    def extract_text(self, html, selector=None):
        """
        提取文本内容
        
        Args:
            html: HTML 内容
            selector: CSS 选择器（可选）
        
        Returns:
            提取的文本
        """
        soup = BeautifulSoup(html, 'lxml')
        
        if selector:
            elements = soup.select(selector)
            return '\n'.join([elem.get_text(strip=True) for elem in elements])
        else:
            # 提取正文（智能识别）
            # 移除无用标签
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            # 提取所有段落
            paragraphs = soup.find_all('p')
            return '\n\n'.join([p.get_text(strip=True) for p in paragraphs])
    
    def extract_title(self, html):
        """提取标题"""
        soup = BeautifulSoup(html, 'lxml')
        title = soup.find('title')
        return title.get_text(strip=True) if title else '无标题'
    
    def save(self, content, filename):
        """
        保存内容到文件
        
        Args:
            content: 内容（字符串或字典）
            filename: 文件名
        """
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            if isinstance(content, str):
                f.write(content)
            else:
                json.dump(content, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存：{filepath}")
        return filepath
    
    def fetch_and_save(self, url, filename, selector=None):
        """
        一站式：抓取 + 提取 + 保存
        
        Args:
            url: 目标 URL
            filename: 保存文件名
            selector: CSS 选择器
        """
        html = self.fetch(url)
        if not html:
            return None
        
        title = self.extract_title(html)
        content = self.extract_text(html, selector)
        
        result = {
            'title': title,
            'url': url,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        self.save(result, filename)
        return result

# 使用示例
if __name__ == "__main__":
    # 创建爬虫（启用代理访问国外网站）
    spider = SmartSpider(use_proxy=True)
    
    # 抓取外刊文章
    url = "https://www.theguardian.com/commentisfree/2026/mar/04/example-article"
    result = spider.fetch_and_save(url, "guardian_article.json")
    
    print(f"\n📝 标题：{result['title']}")
    print(f"📊 字数：{len(result['content'])}")
```

---

### 步骤 3: 创建外刊爬虫

```python
#!/usr/bin/env python3
"""
magazine_spider.py - 外刊爬虫
支持：卫报、BBC、科学美国人等
"""

from spider_base import SmartSpider
from datetime import datetime
import feedparser

class MagazineSpider(SmartSpider):
    """外刊爬虫"""
    
    def __init__(self):
        super().__init__(use_proxy=True)  # 默认启用代理
        
        # 外刊 RSS 源
        self.rss_feeds = {
            'guardian': 'https://www.theguardian.com/rss',
            'bbc': 'http://feeds.bbci.co.uk/news/rss.xml',
            'scientific_american': 'https://www.scientificamerican.com/rss/',
            'economist': 'https://www.economist.com/the-world-this-week/rss.xml'
        }
        
        # 外刊网站配置
        self.sites = {
            'guardian': {
                'url': 'https://www.theguardian.com',
                'selector': 'div.article-body',
                'proxy': True
            },
            'bbc': {
                'url': 'https://www.bbc.com',
                'selector': 'article div[data-testid="article-body"]',
                'proxy': False  # BBC 国内可访问
            }
        }
    
    def fetch_latest_articles(self, source, limit=5):
        """
        获取最新文章列表（通过 RSS）
        
        Args:
            source: 外刊来源（guardian/bbc/...）
            limit: 获取数量
        
        Returns:
            文章列表
        """
        if source not in self.rss_feeds:
            print(f"❌ 未知来源：{source}")
            return []
        
        print(f"📰 获取 {source} 最新文章...")
        feed = feedparser.parse(self.rss_feeds[source])
        
        articles = []
        for entry in feed.entries[:limit]:
            articles.append({
                'title': entry.title,
                'link': entry.link,
                'published': entry.get('published', ''),
                'summary': entry.get('summary', '')[:200]
            })
        
        print(f"✅ 获取到 {len(articles)} 篇文章")
        return articles
    
    def fetch_full_article(self, url, source='guardian'):
        """
        抓取全文
        
        Args:
            url: 文章 URL
            source: 来源
        
        Returns:
            完整文章内容
        """
        if source not in self.sites:
            print(f"⚠️  未知来源，使用通用模式")
            return self.fetch_and_save(url, f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        site_config = self.sites[source]
        
        # 创建爬虫（根据网站决定是否使用代理）
        spider = SmartSpider(use_proxy=site_config['proxy'])
        
        html = spider.fetch(url)
        if not html:
            return None
        
        result = {
            'title': spider.extract_title(html),
            'url': url,
            'content': spider.extract_text(html, site_config['selector']),
            'source': source,
            'timestamp': datetime.now().isoformat()
        }
        
        filename = f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        spider.save(result, filename)
        
        return result
    
    def daily_fetch(self, sources=None, limit=3):
        """
        每日定时抓取
        
        Args:
            sources: 外刊来源列表
            limit: 每个来源抓取数量
        """
        if sources is None:
            sources = ['guardian', 'bbc']
        
        print(f"📅 开始每日抓取任务：{sources}")
        
        all_articles = []
        for source in sources:
            # 获取文章列表
            articles = self.fetch_latest_articles(source, limit)
            
            # 抓取全文（前 3 篇）
            for article in articles[:3]:
                print(f"\n📝 抓取：{article['title']}")
                try:
                    full = self.fetch_full_article(article['link'], source)
                    if full:
                        all_articles.append(full)
                except Exception as e:
                    print(f"⚠️  抓取失败：{e}")
                
                # 礼貌延迟
                import time
                time.sleep(2)
        
        # 生成汇总
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'sources': sources,
            'total': len(all_articles),
            'articles': all_articles
        }
        
        filename = f"daily_{datetime.now().strftime('%Y%m%d')}.json"
        self.save(summary, filename)
        
        print(f"\n✅ 每日抓取完成！共 {len(all_articles)} 篇文章")
        return summary

# 使用示例
if __name__ == "__main__":
    spider = MagazineSpider()
    
    # 获取最新文章列表
    articles = spider.fetch_latest_articles('guardian', limit=5)
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']}")
    
    # 抓取全文
    if articles:
        full = spider.fetch_full_article(articles[0]['link'], 'guardian')
        print(f"\n📝 标题：{full['title']}")
        print(f"📊 字数：{len(full['content'])}")
    
    # 每日定时抓取
    # spider.daily_fetch(['guardian', 'bbc'], limit=3)
```

---

### 步骤 4: 创建雅思资料爬虫

```python
#!/usr/bin/env python3
"""
ielts_spider.py - 雅思资料爬虫
抓取：雅思官网、British Council、雅思论坛
"""

from spider_base import SmartSpider
from datetime import datetime

class IELTSSpider(SmartSpider):
    """雅思资料爬虫"""
    
    def __init__(self):
        super().__init__(use_proxy=False)  # 雅思网站国内可访问
        
        self.sources = {
            'ielts_official': {
                'url': 'https://www.ielts.org/',
                'name': '雅思官网'
            },
            'british_council': {
                'url': 'https://www.britishcouncil.org/ielts',
                'name': 'British Council'
            },
            'ielts_blog': {
                'url': 'https://ieltsblog.com/',
                'name': '雅思博客'
            }
        }
    
    def fetch_writing_samples(self, limit=5):
        """
        抓取写作范文
        
        Args:
            limit: 抓取数量
        
        Returns:
            范文列表
        """
        print("📝 抓取雅思写作范文...")
        
        # 示例：从雅思博客抓取
        url = "https://ieltsblog.com/ielts-writing-task-2-samples/"
        html = self.fetch(url)
        
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        
        samples = []
        articles = soup.find_all('article', limit=limit)
        
        for article in articles:
            title_elem = article.find('h2') or article.find('h3')
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            link_elem = article.find('a')
            link = link_elem['href'] if link_elem else ''
            
            samples.append({
                'title': title,
                'link': link,
                'type': 'writing_sample'
            })
        
        print(f"✅ 获取到 {len(samples)} 篇范文")
        return samples
    
    def fetch_vocabulary(self, topic=None):
        """
        抓取词汇资料
        
        Args:
            topic: 话题（education/environment/...）
        
        Returns:
            词汇列表
        """
        print(f"📚 抓取词汇资料...")
        
        # 这里可以扩展具体抓取逻辑
        vocabulary = {
            'education': ['tuition fees', 'academic performance', 'higher education'],
            'environment': ['climate change', 'carbon footprint', 'sustainable'],
            'technology': ['artificial intelligence', 'automation', 'digitalization']
        }
        
        if topic and topic in vocabulary:
            return {'topic': topic, 'words': vocabulary[topic]}
        else:
            return vocabulary
    
    def daily_practice_materials(self):
        """
        获取每日练习材料
        
        Returns:
            练习材料包
        """
        print("📖 准备每日练习材料...")
        
        materials = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'reading': self.fetch_writing_samples(1),
            'vocabulary': self.fetch_vocabulary(),
            'topics': ['education', 'environment', 'technology']
        }
        
        filename = f"ielts_daily_{datetime.now().strftime('%Y%m%d')}.json"
        self.save(materials, filename)
        
        return materials

# 使用示例
if __name__ == "__main__":
    spider = IELTSSpider()
    
    # 获取写作范文
    samples = spider.fetch_writing_samples(3)
    for sample in samples:
        print(f"- {sample['title']}")
    
    # 获取词汇
    vocab = spider.fetch_vocabulary('education')
    print(f"\n📚 教育话题词汇：{vocab['words']}")
    
    # 准备每日练习
    materials = spider.daily_practice_materials()
    print(f"\n✅ 已生成每日练习材料")
```

---

### 步骤 5: 创建定时任务

```bash
#!/bin/bash
# setup_cron.sh - 配置定时抓取任务

echo "⏰ 配置定时任务..."

# 添加到 crontab
(crontab -l 2>/dev/null | grep -v spider; \
echo "# 每日 8:00 抓取外刊" \
"0 8 * * * cd /opt/spider && source venv/bin/activate && python3 magazine_spider.py >> /var/log/spider.log 2>&1"; \
echo "# 每日 9:00 抓取雅思资料" \
"0 9 * * * cd /opt/spider && source venv/bin/activate && python3 ielts_spider.py >> /var/log/spider.log 2>&1"; \
echo "# 每周日清理旧文件" \
"0 3 * * 0 find /opt/spider/output -name '*.json' -mtime +30 -delete") | crontab -

echo "✅ 定时任务已配置"
echo ""
echo "当前 crontab:"
crontab -l
```

---

### 步骤 6: 创建 OpenClaw 集成接口

```python
#!/usr/bin/env python3
"""
openclaw_bridge.py - OpenClaw 调用接口
"""

from flask import Flask, request, jsonify
from magazine_spider import MagazineSpider
from ielts_spider import IELTSSpider
import os

app = Flask(__name__)

@app.route('/spider/fetch', methods=['POST'])
def fetch_url():
    """抓取指定 URL"""
    data = request.json
    url = data.get('url')
    use_proxy = data.get('proxy', False)
    
    if not url:
        return jsonify({'error': 'Missing URL'}), 400
    
    spider = SmartSpider(use_proxy=use_proxy)
    result = spider.fetch_and_save(url, f"manual_{url.replace('/', '_')}.json")
    
    return jsonify(result)

@app.route('/magazine/latest', methods=['POST'])
def fetch_magazine():
    """抓取外刊"""
    data = request.json
    source = data.get('source', 'guardian')
    limit = data.get('limit', 3)
    
    spider = MagazineSpider()
    articles = spider.fetch_latest_articles(source, limit)
    
    return jsonify({'articles': articles})

@app.route('/ielts/materials', methods=['GET'])
def get_ielts_materials():
    """获取雅思资料"""
    spider = IELTSSpider()
    materials = spider.daily_practice_materials()
    
    return jsonify(materials)

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'service': 'spider-api'})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)
```

---

### 步骤 7: 一键部署脚本

```bash
#!/bin/bash
# deploy_all.sh - 一键部署所有爬虫

set -e

echo "🚀 开始部署爬虫系统..."
echo "时间：$(date)"
echo ""

# 步骤 1: 安装依赖
echo "📦 步骤 1: 安装依赖"
bash install_dependencies.sh
echo ""

# 步骤 2: 创建爬虫脚本
echo "📝 步骤 2: 创建爬虫脚本"
cp spider_base.py /opt/spider/
cp magazine_spider.py /opt/spider/
cp ielts_spider.py /opt/spider/
cp openclaw_bridge.py /opt/spider/
echo "✅ 爬虫脚本已创建"
echo ""

# 步骤 3: 配置定时任务
echo "⏰ 步骤 3: 配置定时任务"
bash setup_cron.sh
echo ""

# 步骤 4: 启动 API 服务
echo "🔌 步骤 4: 启动 API 服务"
cd /opt/spider
source venv/bin/activate
nohup python3 openclaw_bridge.py > /var/log/spider_api.log 2>&1 &
echo "✅ API 服务已启动（端口 5001）"
echo ""

# 步骤 5: 测试
echo "🧪 步骤 5: 测试"
sleep 3
curl http://localhost:5001/health && echo "✅ API 正常" || echo "⚠️  API 异常"
echo ""

echo "========================================"
echo "✅ 爬虫系统部署完成！"
echo "========================================"
echo ""
echo "使用方式:"
echo "  cd /opt/spider && source venv/bin/activate"
echo "  python3 magazine_spider.py      # 抓取外刊"
echo "  python3 ielts_spider.py         # 抓取雅思资料"
echo ""
echo "API 调用:"
echo "  curl http://localhost:5001/magazine/latest"
echo ""
echo "定时任务:"
echo "  每天 8:00 - 外刊抓取"
echo "  每天 9:00 - 雅思资料"
echo "  每周日 3:00 - 清理旧文件"
echo ""
```

---

## 📊 部署后的目录结构

```
/opt/spider/
├── venv/                      # Python 虚拟环境
├── output/                    # 抓取结果
│   ├── guardian_20260304_080000.json
│   ├── ielts_daily_20260304.json
│   └── ...
├── spider_base.py             # 基础爬虫
├── magazine_spider.py         # 外刊爬虫
├── ielts_spider.py            # 雅思爬虫
├── openclaw_bridge.py         # OpenClaw 接口
├── install_dependencies.sh    # 安装脚本
├── setup_cron.sh              # 定时任务配置
└── deploy_all.sh              # 一键部署
```

---

## 🎯 使用方式

### 1. 手动抓取

```bash
cd /opt/spider
source venv/bin/activate

# 抓取外刊
python3 magazine_spider.py

# 抓取雅思资料
python3 ielts_spider.py
```

### 2. API 调用

```bash
# 获取最新文章
curl http://localhost:5001/magazine/latest \
  -H "Content-Type: application/json" \
  -d '{"source": "guardian", "limit": 3}'

# 获取雅思资料
curl http://localhost:5001/ielts/materials
```

### 3. OpenClaw 集成

```python
# 通过 SSH 调用
ssh root@106.53.186.90 "
curl http://localhost:5001/spider/fetch \
  -H 'Content-Type: application/json' \
  -d '{\"url\": \"https://xxx.com\", \"proxy\": true}'
"
```

---

## 📝 注意事项

### 法律合规
- ✅ 遵守 robots.txt
- ✅ 控制抓取频率（每 2-3 秒一次）
- ✅ 仅用于个人学习
- ❌ 不要大规模分发抓取内容

### 技术注意
- 设置合理的 User-Agent
- 使用指数退避重试
- 添加请求延迟
- 定期清理旧文件

### 代理使用
- 国内网站：直连（更快）
- 国外网站：Clash 代理（端口 7890）
- 自动切换：根据域名判断

---

## ✅ 部署检查清单

- [ ] Python 依赖已安装
- [ ] 爬虫脚本已创建
- [ ] 定时任务已配置
- [ ] API 服务已启动
- [ ] 测试抓取成功
- [ ] 输出目录可写
- [ ] 日志正常记录

---

*部署指南版本：v1.0*  
*创建时间：2026-03-04*  
*适用于：Debian Server (106.53.186.90)*
