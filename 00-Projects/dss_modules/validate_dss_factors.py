"""
DSS 真实数据因子全量验证脚本

使用方法:
    python validate_dss_factors.py --data-path /path/to/dss_data.csv --output ./reports
"""
import pandas as pd
import numpy as np
import argparse
import sys
from pathlib import Path
from factor_validation_batch import FactorValidationBatch, BatchValidationReport


def load_dss_data(data_path: str) -> pd.DataFrame:
    """
    加载 DSS 数据
    
    支持格式:
    - CSV: date, symbol, factor1, factor2, ..., return
    - Parquet: 同上
    - Feather: 同上
    
    Args:
        data_path: 数据文件路径
        
    Returns:
        DataFrame with columns: date, symbol, [factors], return
    """
    path = Path(data_path)
    
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {data_path}")
    
    # 根据扩展名选择加载方式
    if path.suffix == '.csv':
        df = pd.read_csv(data_path)
    elif path.suffix == '.parquet':
        df = pd.read_parquet(data_path)
    elif path.suffix == '.feather':
        df = pd.read_feather(data_path)
    else:
        raise ValueError(f"不支持的数据格式: {path.suffix}")
    
    print(f"✓ 数据加载成功: {len(df)} 行, {len(df.columns)} 列")
    print(f"  日期范围: {df['date'].min()} ~ {df['date'].max()}")
    print(f"  股票数量: {df['symbol'].nunique()}")
    
    return df


def auto_detect_factors(df: pd.DataFrame, 
                       exclude_cols: list = None) -> list:
    """
    自动识别因子列
    
    排除标准列: date, symbol, return, open, high, low, close, volume
    
    Args:
        df: DataFrame
        exclude_cols: 额外排除的列
        
    Returns:
        因子列名列表
    """
    if exclude_cols is None:
        exclude_cols = []
    
    # 标准排除列
    standard_excludes = ['date', 'symbol', 'return', 'open', 'high', 'low', 
                        'close', 'volume', 'adj_close', 'turnover', 'vwap']
    
    all_excludes = set(standard_excludes + exclude_cols)
    
    # 识别因子列 (数值型且不在排除列表)
    factor_cols = [
        col for col in df.columns
        if col not in all_excludes
        and pd.api.types.is_numeric_dtype(df[col])
    ]
    
    print(f"✓ 自动识别到 {len(factor_cols)} 个因子:")
    for i, col in enumerate(factor_cols[:10], 1):
        print(f"  {i}. {col}")
    if len(factor_cols) > 10:
        print(f"  ... 和另外 {len(factor_cols)-10} 个因子")
    
    return factor_cols


def validate_dss_factors(data_path: str,
                         output_dir: str = './reports',
                         ic_ir_threshold: float = 0.3,
                         pathway_threshold: float = 0.7,
                         factor_cols: list = None,
                         date_col: str = 'date',
                         return_col: str = 'return',
                         symbol_col: str = 'symbol',
                         export_formats: list = None):
    """
    验证 DSS 因子
    
    Args:
        data_path: 数据文件路径
        output_dir: 报告输出目录
        ic_ir_threshold: IC/IR 阈值
        pathway_threshold: 多轨道稳定性阈值
        factor_cols: 指定因子列 (None=自动识别)
        date_col: 日期列名
        return_col: 收益列名
        symbol_col: 股票代码列名
        export_formats: 导出格式列表 ['json', 'csv', 'markdown']
    """
    print("=" * 60)
    print("DSS 因子全量验证")
    print("=" * 60)
    
    # 1. 加载数据
    print("\n[1/4] 加载数据...")
    df = load_dss_data(data_path)
    
    # 2. 识别因子
    print("\n[2/4] 识别因子...")
    if factor_cols is None:
        factor_cols = auto_detect_factors(df, exclude_cols=[date_col, return_col, symbol_col])
    
    if not factor_cols:
        raise ValueError("未找到任何因子列")
    
    # 3. 数据预处理
    print("\n[3/4] 数据预处理...")
    
    # 确保日期格式正确
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    
    # 删除缺失值
    required_cols = [date_col, symbol_col, return_col] + factor_cols
    df_clean = df[required_cols].dropna()
    
    print(f"  清洗后: {len(df_clean)} 行 (删除 {len(df)-len(df_clean)} 行缺失值)")
    
    # 4. 批量验证
    print("\n[4/4] 批量验证...")
    batch = FactorValidationBatch(
        ic_ir_threshold=ic_ir_threshold,
        pathway_threshold=pathway_threshold
    )
    
    report = batch.validate_batch(df_clean, factor_cols, return_col, date_col)
    
    # 5. 导出报告
    print("\n" + "=" * 60)
    print("导出报告")
    print("=" * 60)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if export_formats is None:
        export_formats = ['json', 'csv', 'markdown']
    
    exported_files = []
    for fmt in export_formats:
        file_path = batch.export_report(
            report, 
            output_path / f'dss_factor_validation_{report.timestamp[:10]}',
            format=fmt
        )
        exported_files.append(file_path)
        print(f"✓ {fmt.upper()}: {file_path}")
    
    # 6. 汇总输出
    print("\n" + "=" * 60)
    print("验证汇总")
    print("=" * 60)
    print(f"总因子数: {report.total_factors}")
    print(f"通过验证: {report.passed_factors} ({report.passed_factors/report.total_factors*100:.1f}%)")
    print(f"未通过: {report.failed_factors}")
    print(f"\n阈值设置:")
    print(f"  IC/IR ≥ {ic_ir_threshold}")
    print(f"  多轨道稳定性 ≥ {pathway_threshold}")
    
    # 有效因子列表
    valid_factors = batch.get_valid_factors(report)
    print(f"\n有效因子列表 ({len(valid_factors)}个):")
    for i, f in enumerate(valid_factors, 1):
        print(f"  {i}. {f}")
    
    # Top 因子
    print(f"\nTop 5 IR 因子:")
    top_ir = batch.get_top_factors(report, metric='ir', n=5)
    for i, f in enumerate(top_ir, 1):
        status = "✓" if f['pass_validation'] else "✗"
        print(f"  {i}. {f['factor_name']}: IR={f['ir']:.2f} {status}")
    
    print(f"\nTop 5 稳定性因子:")
    top_stable = batch.get_top_factors(report, metric='pathway_stability', n=5)
    for i, f in enumerate(top_stable, 1):
        status = "✓" if f['pass_validation'] else "✗"
        print(f"  {i}. {f['factor_name']}: 稳定性={f['pathway_stability']:.2f} {status}")
    
    return report, exported_files


def main():
    parser = argparse.ArgumentParser(description='DSS 因子全量验证')
    parser.add_argument('--data-path', type=str, required=True,
                       help='数据文件路径 (csv/parquet/feather)')
    parser.add_argument('--output', type=str, default='./reports',
                       help='报告输出目录 (默认: ./reports)')
    parser.add_argument('--ic-ir-threshold', type=float, default=0.3,
                       help='IC/IR 阈值 (默认: 0.3)')
    parser.add_argument('--pathway-threshold', type=float, default=0.7,
                       help='多轨道稳定性阈值 (默认: 0.7)')
    parser.add_argument('--date-col', type=str, default='date',
                       help='日期列名 (默认: date)')
    parser.add_argument('--return-col', type=str, default='return',
                       help='收益列名 (默认: return)')
    parser.add_argument('--symbol-col', type=str, default='symbol',
                       help='股票代码列名 (默认: symbol)')
    parser.add_argument('--factors', type=str, nargs='+', default=None,
                       help='指定因子列名 (默认自动识别)')
    parser.add_argument('--formats', type=str, nargs='+', 
                       default=['json', 'csv', 'markdown'],
                       choices=['json', 'csv', 'markdown'],
                       help='导出格式')
    
    args = parser.parse_args()
    
    try:
        report, files = validate_dss_factors(
            data_path=args.data_path,
            output_dir=args.output,
            ic_ir_threshold=args.ic_ir_threshold,
            pathway_threshold=args.pathway_threshold,
            factor_cols=args.factors,
            date_col=args.date_col,
            return_col=args.return_col,
            symbol_col=args.symbol_col,
            export_formats=args.formats
        )
        
        print("\n✓ 验证完成!")
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()