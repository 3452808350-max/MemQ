"""
Day 1: 数据加载与初步探索
目标：成功读取数据并了解其结构
"""

import pandas as pd

# 1. 读取数据
# 注意：你的文件是 .xls 但实际是 CSV 格式，用 pd.read_csv
df = pd.read_csv('data/movies.csv')

# 2. 查看基本信息
print("=" * 50)
print("数据形状（行数, 列数）:", df.shape)
print("=" * 50)

print("\n" + "=" * 50)
print("列名:")
print("=" * 50)
print(df.columns.tolist())

print("\n" + "=" * 50)
print("前 5 行数据:")
print("=" * 50)
print(df.head())

print("\n" + "=" * 50)
print("数据类型:")
print("=" * 50)
print(df.dtypes)

print("\n" + "=" * 50)
print("基本统计信息:")
print("=" * 50)
print(df.describe())

print("\n" + "=" * 50)
print("缺失值统计:")
print("=" * 50)
print(df.isnull().sum())

# 3. 保存一个精简版供查看（可选）
# df.head(100).to_csv('../data/movies_sample.csv', index=False)
# print("\n已保存前100行到 movies_sample.csv")
