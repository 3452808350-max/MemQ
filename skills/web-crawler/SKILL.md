# Web Crawler Skill

用于快速爬取网页信息的工具。

## 功能

| 功能 | 命令 |
|------|------|
| 获取链接 | `crawl links <url>` |
| 获取图片 | `crawl images <url>` |
| 获取表格 | `crawl table <url>` |
| 获取文章 | `crawl article <url>` |
| 获取JSON | `crawl json <url>` |

## 使用方法

### 命令行

```bash
python3 ~/skills/web-crawler/crawler.py links <url>
python3 ~/skills/web-crawler/crawler.py images <url>
python3 ~/skills/web-crawler/crawler.py table <url>
python3 ~/skills/web-crawler/crawler.py article <url>
python3 ~/skills/web-crawler/crawler.py json <url>
```

### 快速调用

```bash
# 快速获取链接
crawl links https://news.ycombinator.com/

# 快速获取图片
crawl images https://unsplash.com/

# 快速获取表格
crawl table https://example.com/data

# 快速获取文章
crawl article https://example.com/blog

# 快速获取JSON
crawl json https://api.example.com/data
```

## 示例

### 爬取文章

```
输入: crawl article https://example.com/blog
输出: 文章标题和正文内容
```

### 爬取表格

```
输入: crawl table https://example.com/stats
输出: 表格数据（CSV格式显示）
```

## 注意事项

- 遵守目标网站的 robots.txt
- 不要过于频繁爬取
- 用于学习目的，不要用于商业爬虫
