"""
图表生成模块 - QuickChart API
自动生成股价走势图、K 线图等
"""
import requests
import pandas as pd
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import io

# QuickChart API 配置
QUICKCHART_BASE = "https://quickchart.io/chart"

# 图表主题配色
CHART_THEMES = {
    'default': {
        'bgColor': 'white',
        'gridColor': 'rgba(0, 0, 0, 0.1)',
        'textColor': '#333',
        'lineColors': ['#2563eb', '#dc2626', '#16a34a']
    },
    'dark': {
        'bgColor': 'rgba(30, 30, 30, 1)',
        'gridColor': 'rgba(255, 255, 255, 0.1)',
        'textColor': '#eee',
        'lineColors': ['#3b82f6', '#ef4444', '#22c55e']
    },
    'professional': {
        'bgColor': 'white',
        'gridColor': 'rgba(0, 0, 0, 0.05)',
        'textColor': '#1f2937',
        'lineColors': ['#059669', '#dc2626', '#2563eb']
    }
}


def generate_line_chart(
    data: List[Tuple[str, float]],
    title: str = "股价走势",
    width: int = 800,
    height: int = 400,
    theme: str = 'default'
) -> str:
    """
    生成折线图
    
    Args:
        data: 数据列表 [(日期，价格), ...]
        title: 图表标题
        width: 宽度
        height: 高度
        theme: 主题
    
    Returns:
        图表 URL
    """
    # 分离日期和价格
    labels = [d[0] for d in data]
    prices = [d[1] for d in data]
    
    # 计算涨跌幅颜色
    if len(prices) > 1:
        is_up = prices[-1] > prices[0]
        line_color = CHART_THEMES[theme]['lineColors'][0 if is_up else 1]
    else:
        line_color = CHART_THEMES[theme]['lineColors'][0]
    
    chart_config = {
        'type': 'line',
        'data': {
            'labels': labels,
            'datasets': [{
                'label': '价格',
                'data': prices,
                'borderColor': line_color,
                'backgroundColor': line_color + '20',  # 半透明填充
                'borderWidth': 2,
                'fill': True,
                'tension': 0.1,
                'pointRadius': 3,
                'pointHoverRadius': 5
            }]
        },
        'options': {
            'responsive': False,
            'maintainAspectRatio': False,
            'plugins': {
                'title': {
                    'display': True,
                    'text': title,
                    'font': {'size': 16}
                },
                'legend': {
                    'display': False
                },
                'tooltip': {
                    'mode': 'index',
                    'intersect': False
                }
            },
            'scales': {
                'x': {
                    'display': True,
                    'grid': {
                        'color': CHART_THEMES[theme]['gridColor']
                    },
                    'ticks': {
                        'color': CHART_THEMES[theme]['textColor'],
                        'maxRotation': 45,
                        'minRotation': 45
                    }
                },
                'y': {
                    'display': True,
                    'grid': {
                        'color': CHART_THEMES[theme]['gridColor']
                    },
                    'ticks': {
                        'color': CHART_THEMES[theme]['textColor']
                    }
                }
            }
        }
    }
    
    # 构建 URL
    import urllib.parse
    chart_url = f"{QUICKCHART_BASE}?c={urllib.parse.quote(str(chart_config))}&w={width}&h={height}&f=png"
    
    return chart_url


def generate_multi_line_chart(
    data_dict: Dict[str, List[Tuple[str, float]]],
    title: str = "多股票对比",
    width: int = 800,
    height: int = 400,
    theme: str = 'default'
) -> str:
    """
    生成多折线对比图
    
    Args:
        data_dict: {股票名：[(日期，价格), ...], ...}
        title: 图表标题
        width: 宽度
        height: 高度
        theme: 主题
    
    Returns:
        图表 URL
    """
    # 获取所有日期标签（取第一个股票的）
    first_key = list(data_dict.keys())[0]
    labels = [d[0] for d in data_dict[first_key]]
    
    # 构建数据集
    datasets = []
    colors = CHART_THEMES[theme]['lineColors']
    
    for i, (name, data) in enumerate(data_dict.items()):
        prices = [d[1] for d in data]
        color = colors[i % len(colors)]
        
        datasets.append({
            'label': name,
            'data': prices,
            'borderColor': color,
            'backgroundColor': color + '00',  # 不填充
            'borderWidth': 2,
            'fill': False,
            'tension': 0.1,
            'pointRadius': 2
        })
    
    chart_config = {
        'type': 'line',
        'data': {
            'labels': labels,
            'datasets': datasets
        },
        'options': {
            'responsive': False,
            'maintainAspectRatio': False,
            'plugins': {
                'title': {
                    'display': True,
                    'text': title,
                    'font': {'size': 16}
                },
                'legend': {
                    'display': True,
                    'position': 'top'
                }
            },
            'scales': {
                'x': {
                    'display': True,
                    'grid': {'color': CHART_THEMES[theme]['gridColor']},
                    'ticks': {'color': CHART_THEMES[theme]['textColor']}
                },
                'y': {
                    'display': True,
                    'grid': {'color': CHART_THEMES[theme]['gridColor']},
                    'ticks': {'color': CHART_THEMES[theme]['textColor']}
                }
            }
        }
    }
    
    import urllib.parse
    chart_url = f"{QUICKCHART_BASE}?c={urllib.parse.quote(str(chart_config))}&w={width}&h={height}&f=png"
    
    return chart_url


def generate_bar_chart(
    data: List[Tuple[str, float]],
    title: str = "涨跌幅对比",
    width: int = 800,
    height: int = 400,
    theme: str = 'default',
    horizontal: bool = False
) -> str:
    """
    生成柱状图
    
    Args:
        data: [(名称，数值), ...]
        title: 标题
        width: 宽度
        height: 高度
        theme: 主题
        horizontal: 是否横向
    
    Returns:
        图表 URL
    """
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    
    # 根据正负设置颜色
    bg_colors = []
    for v in values:
        if v > 0:
            bg_colors.append(CHART_THEMES[theme]['lineColors'][2])  # 绿色
        else:
            bg_colors.append(CHART_THEMES[theme]['lineColors'][1])  # 红色
    
    chart_config = {
        'type': 'bar' if not horizontal else 'bar',
        'data': {
            'labels': labels,
            'datasets': [{
                'label': '数值',
                'data': values,
                'backgroundColor': bg_colors,
                'borderColor': bg_colors,
                'borderWidth': 1
            }]
        },
        'options': {
            'responsive': False,
            'maintainAspectRatio': False,
            'indexAxis': 'y' if horizontal else 'x',
            'plugins': {
                'title': {
                    'display': True,
                    'text': title,
                    'font': {'size': 16}
                },
                'legend': {
                    'display': False
                }
            },
            'scales': {
                'x': {
                    'display': True,
                    'grid': {'color': CHART_THEMES[theme]['gridColor']},
                    'ticks': {'color': CHART_THEMES[theme]['textColor']}
                },
                'y': {
                    'display': True,
                    'grid': {'color': CHART_THEMES[theme]['gridColor']},
                    'ticks': {'color': CHART_THEMES[theme]['textColor']}
                }
            }
        }
    }
    
    import urllib.parse
    chart_url = f"{QUICKCHART_BASE}?c={urllib.parse.quote(str(chart_config))}&w={width}&h={height}&f=png"
    
    return chart_url


def generate_candlestick_chart(
    data: List[Dict],
    title: str = "K 线图",
    width: int = 800,
    height: int = 500
) -> str:
    """
    生成 K 线图（简化版，用 OHLC 图表）
    
    Args:
        data: [{date, open, high, low, close}, ...]
        title: 标题
        width: 宽度
        height: 高度
    
    Returns:
        图表 URL
    """
    # Chart.js 不支持原生 K 线图，这里用简化的折线 + 柱状组合
    labels = [d['date'] for d in data]
    closes = [d['close'] for d in data]
    
    # 计算涨跌
    colors = []
    for i in range(len(closes)):
        if i == 0:
            colors.append('#9ca3af')
        elif closes[i] > closes[i-1]:
            colors.append(CHART_THEMES['default']['lineColors'][2])  # 绿
        else:
            colors.append(CHART_THEMES['default']['lineColors'][1])  # 红
    
    chart_config = {
        'type': 'line',
        'data': {
            'labels': labels,
            'datasets': [{
                'label': '收盘价',
                'data': closes,
                'borderColor': '#2563eb',
                'backgroundColor': '#2563eb20',
                'borderWidth': 2,
                'fill': True,
                'tension': 0.1,
                'pointRadius': 2
            }]
        },
        'options': {
            'responsive': False,
            'maintainAspectRatio': False,
            'plugins': {
                'title': {
                    'display': True,
                    'text': title,
                    'font': {'size': 16}
                },
                'legend': {
                    'display': False
                }
            },
            'scales': {
                'x': {
                    'display': True,
                    'grid': {'color': 'rgba(0,0,0,0.1)'},
                    'ticks': {'maxRotation': 45, 'minRotation': 45}
                },
                'y': {
                    'display': True,
                    'grid': {'color': 'rgba(0,0,0,0.1)'}
                }
            }
        }
    }
    
    import urllib.parse
    chart_url = f"{QUICKCHART_BASE}?c={urllib.parse.quote(str(chart_config))}&w={width}&h={height}&f=png"
    
    return chart_url


def generate_pie_chart(
    data: List[Tuple[str, float]],
    title: str = "持仓分布",
    width: int = 500,
    height: int = 500
) -> str:
    """
    生成饼图
    
    Args:
        data: [(名称，数值), ...]
        title: 标题
        width: 宽度
        height: 高度
    
    Returns:
        图表 URL
    """
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    
    colors = [
        '#2563eb', '#dc2626', '#16a34a', '#f59e0b', '#8b5cf6',
        '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
    ]
    
    chart_config = {
        'type': 'pie',
        'data': {
            'labels': labels,
            'datasets': [{
                'data': values,
                'backgroundColor': colors[:len(labels)],
                'borderWidth': 2,
                'borderColor': 'white'
            }]
        },
        'options': {
            'responsive': False,
            'maintainAspectRatio': False,
            'plugins': {
                'title': {
                    'display': True,
                    'text': title,
                    'font': {'size': 16}
                },
                'legend': {
                    'display': True,
                    'position': 'right'
                }
            }
        }
    }
    
    import urllib.parse
    chart_url = f"{QUICKCHART_BASE}?c={urllib.parse.quote(str(chart_config))}&w={width}&h={height}&f=png"
    
    return chart_url


def download_chart(chart_url: str, save_path: str = None) -> Optional[bytes]:
    """
    下载图表图片
    
    Args:
        chart_url: 图表 URL
        save_path: 保存路径（可选）
    
    Returns:
        图片二进制数据
    """
    try:
        response = requests.get(chart_url, timeout=10)
        response.raise_for_status()
        
        image_data = response.content
        
        if save_path:
            with open(save_path, 'wb') as f:
                f.write(image_data)
            print(f"✓ 图表已保存：{save_path}")
        
        return image_data
    except Exception as e:
        print(f"[!] 下载图表错误：{e}")
        return None


def chart_to_base64(chart_url: str) -> Optional[str]:
    """
    将图表转换为 Base64 编码（用于邮件 HTML）
    
    Args:
        chart_url: 图表 URL
    
    Returns:
        Base64 字符串
    """
    image_data = download_chart(chart_url)
    if image_data:
        return base64.b64encode(image_data).decode('utf-8')
    return None


# 测试
if __name__ == "__main__":
    print("="*60)
    print("DSS 图表生成模块测试")
    print("="*60)
    
    # 测试数据
    dates = [(datetime.now() - timedelta(days=i)).strftime('%m-%d') for i in range(30, 0, -1)]
    prices = [100 + i * 0.5 + (i % 7) * 0.3 for i in range(30)]
    data = list(zip(dates, prices))
    
    # 测试折线图
    print("\n📈 生成折线图...")
    line_chart = generate_line_chart(data, "测试股票 30 日走势")
    print(f"   URL: {line_chart[:100]}...")
    
    # 测试多股票对比
    print("\n📊 生成多股票对比图...")
    multi_data = {
        '股票 A': data,
        '股票 B': [(d, p * 1.1) for d, p in data],
        '股票 C': [(d, p * 0.95) for d, p in data]
    }
    multi_chart = generate_multi_line_chart(multi_data, "多股票对比")
    print(f"   URL: {multi_chart[:100]}...")
    
    # 测试柱状图
    print("\n📉 生成柱状图...")
    bar_data = [
        ('股票 A', 5.2), ('股票 B', -2.1), ('股票 C', 3.8),
        ('股票 D', -1.5), ('股票 E', 7.3)
    ]
    bar_chart = generate_bar_chart(bar_data, "涨跌幅对比")
    print(f"   URL: {bar_chart[:100]}...")
    
    # 测试饼图
    print("\n🥧 生成饼图...")
    pie_data = [('A 股', 60), ('美股', 25), ('加密货币', 10), ('现金', 5)]
    pie_chart = generate_pie_chart(pie_data, "资产配置")
    print(f"   URL: {pie_chart[:100]}...")
    
    print("\n" + "="*60)
    print("✅ 图表 URL 可在浏览器中打开查看")
