#!/usr/bin/env python3
"""
金融数据架构测试
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import os
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("DSS金融数据架构测试")
print("="*60)

from dss_modules.financial_data_store import FinancialDataStore, create_financial_store
import pandas as pd
import numpy as np

# 创建存储
store = create_financial_store()

print("\n📊 1. 测试数据保存（不可变）")
print("-"*50)

# 模拟股票数据
np.random.seed(42)
dates = pd.date_range('2026-03-01', '2026-03-25', freq='D')
prices = 100 + np.cumsum(np.random.randn(len(dates)) * 2)

df = pd.DataFrame({
    'date': dates,
    'open': prices,
    'high': prices + np.abs(np.random.randn(len(dates))),
    'low': prices - np.abs(np.random.randn(len(dates))),
    'close': prices + np.random.randn(len(dates)),
    'volume': np.random.randint(1000000, 10000000, len(dates))
})

result = store.save_data('600519', df, '2026-03-25', 'price')
print(f"保存状态: {result['status']}")
print(f"文件哈希: {result['hash'][:16]}...")
if result['status'] == 'created':
    print(f"数据行数: {result['rows']}")

# 再次保存（幂等测试）
result2 = store.save_data('600519', df, '2026-03-25', 'price')
print(f"再次保存: {result2['status']} (幂等)")

print("\n📊 2. 测试版本控制")
print("-"*50)

version = store.create_version(
    trade_date='2026-03-25',
    description='收盘后数据快照',
    metadata={'source': 'baostock', 'processed': True}
)

print(f"版本ID: {version.version_id}")
print(f"交易日期: {version.trade_date}")
print(f"数据哈希: {version.data_hash[:16]}...")
print(f"文件数量: {version.file_count}")

print("\n📊 3. 测试更正机制（追加而非覆盖）")
print("-"*50)

correction = store.add_correction(
    symbol='600519',
    field='close',
    old_value=100.5,
    new_value=100.55,
    reason='数据源修正'
)

print(f"更正ID: {correction.correction_id}")
print(f"字段: {correction.field}")
print(f"原值: {correction.old_value}")
print(f"新值: {correction.new_value}")
print(f"原因: {correction.reason}")

# 列出所有更正
corrections = store.list_corrections()
print(f"\n更正记录数: {len(corrections)}")

print("\n📊 4. 测试血缘追踪")
print("-"*50)

# 创建血缘链
source_node = store.add_lineage(
    name='原始行情数据',
    node_type='source',
    transform_params={'source': 'baostock', 'symbol': '600519'}
)
print(f"源节点: {source_node.node_id}")

clean_node = store.add_lineage(
    name='去噪处理',
    node_type='transform',
    input_nodes=[source_node.node_id],
    transform_params={'method': 'kalman', 'Q': 0.005, 'R': 0.5}
)
print(f"处理节点: {clean_node.node_id}")

feature_node = store.add_lineage(
    name='技术指标',
    node_type='transform',
    input_nodes=[clean_node.node_id],
    transform_params={'indicators': ['RSI', 'MACD', 'MA']}
)
print(f"特征节点: {feature_node.node_id}")

output_node = store.add_lineage(
    name='选股评分',
    node_type='output',
    input_nodes=[feature_node.node_id],
    transform_params={'model': 'xgboost'}
)
print(f"输出节点: {output_node.node_id}")

# 追溯血缘
print("\n血缘追溯:")
lineage_chain = store.trace_lineage(output_node.node_id)
for node in lineage_chain:
    print(f"  ← {node.name} ({node.node_type})")

print("\n📊 5. 测试审计追踪")
print("-"*50)

audit = store.get_audit_trail('600519')
print(f"版本数: {len(audit['versions'])}")
print(f"更正数: {len(audit['corrections'])}")
print(f"血缘节点: {audit['lineage_nodes']}")

print("\n📊 6. 测试数据完整性验证")
print("-"*50)

# 获取保存的文件路径
data_dir = '/home/kyj/.openclaw/workspace/dss_data/data'
for root, dirs, files in os.walk(data_dir):
    for f in files:
        if f.endswith('.parquet'):
            file_path = os.path.join(root, f)
            verify = store.verify_data(file_path)
            print(f"文件: {f[:30]}...")
            print(f"  完整性: {'✅' if verify['valid'] else '❌'}")
            print(f"  哈希: {verify.get('hash', 'N/A')[:16]}...")

print("\n" + "="*60)
print("✅ 金融数据架构测试完成!")
print("="*60)

print("\n📁 数据存储位置:")
print(f"  {store.base_path}")
print(f"  ├── data/          # 数据文件")
print(f"  ├── _versions/     # 版本快照")
print(f"  ├── _corrections/  # 更正记录")
print(f"  └── _lineage/      # 血缘图")