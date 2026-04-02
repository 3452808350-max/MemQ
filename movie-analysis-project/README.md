# 电影数据分析项目 🎬

> 一周从零到完整数据分析报告

## 项目结构

```
movie-analysis-project/
├── data/               # 原始数据和清洗后的数据
├── notebooks/          # Jupyter Notebook 分析过程
├── scripts/            # Python 脚本
├── output/             # 图表和最终报告
└── README.md          # 项目说明
```

## 七天计划

| 天数 | 任务 | 产出 |
|------|------|------|
| Day 1 | 环境搭建 + 数据加载 | 成功读取数据 |
| Day 2 | 数据清洗 | 干净的数据集 |
| Day 3 | 探索性分析 | 数据洞察 |
| Day 4 | 可视化 | 图表 |
| Day 5 | 进阶分析 | 深度结论 |
| Day 6 | 推荐系统 | recommend() 函数 |
| Day 7 | 整合报告 | 完整报告 |

## 数据集字段说明

- `id`: 电影ID
- `original_title`: 电影名称
- `budget`: 预算（美元）
- `revenue`: 收入（美元）
- `vote_average`: 平均评分（0-10）
- `vote_count`: 评分人数
- `genres`: 类型（多值，\|分隔）
- `cast`: 演员（多值，\|分隔）
- `director`: 导演
- `release_year`: 发行年份
- `runtime`: 片长（分钟）
- `overview`: 剧情简介

## 启动方式

```bash
# 进入项目目录
cd movie-analysis-project

# 启动 Jupyter
jupyter notebook

# 或运行脚本
python scripts/day1_load_data.py
```
