#!/usr/bin/env python3
"""
DSS 图表生成演示 - 直接保存图表图片
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

from dss_modules.api_visualization import generate_line_chart, download_chart
from datetime import datetime, timedelta
import os

# 创建图表目录
os.makedirs('/home/kyj/.openclaw/workspace/data/charts', exist_ok=True)

# 生成测试数据（模拟宁德时代 30 日走势）
dates = [(datetime.now() - timedelta(days=i)).strftime('%m-%d') for i in range(30, 0, -1)]
# 模拟股价从 380 到 396
prices = [380 + i * 0.5 + (i % 5) * 0.2 for i in range(30)]
data = list(zip(dates, prices))

print("="*60)
print("📊 DSS 图表生成演示")
print("="*60)

# 生成折线图
print("\n1️⃣ 生成股价走势折线图...")
chart_url = generate_line_chart(
    data, 
    title="宁德时代 (300750) 30 日走势",
    width=800, 
    height=400
)

print(f"   ✅ 图表 URL 已生成")
print(f"   📁 长度：{len(chart_url)} 字符")

# 下载并保存图片
save_path = '/home/kyj/.openclaw/workspace/data/charts/demo_stock_chart.png'
print(f"\n2️⃣ 下载图表到：{save_path}")

image_data = download_chart(chart_url, save_path)

if image_data:
    print(f"   ✅ 下载成功！")
    print(f"   📊 图片大小：{len(image_data)} 字节")
    print(f"   📁 保存位置：{save_path}")
else:
    print(f"   ❌ 下载失败（可能是网络问题）")

# 显示完整 URL（前 200 字符）
print(f"\n3️⃣ 图表 URL (前 200 字符):")
print(f"   {chart_url[:200]}...")

print("\n" + "="*60)
print("📝 查看图表方式:")
print("   1. 复制完整 URL 到浏览器打开")
print("   2. 查看保存的图片文件")
print("   3. 在邮件报告中嵌入 Base64 图片")
print("="*60)
