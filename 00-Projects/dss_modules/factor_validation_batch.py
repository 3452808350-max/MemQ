"""
因子验证全量测试模块
支持批量因子验证、报告生成、结果对比
"""
import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from factor_validation import FactorValidator, FactorValidationResult


@dataclass
class BatchValidationReport:
    """批量验证报告"""
    timestamp: str
    total_factors: int
    passed_factors: int
    failed_factors: int
    results: List[Dict]
    summary: Dict
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'total_factors': self.total_factors,
            'passed_factors': self.passed_factors,
            'failed_factors': self.failed_factors,
            'pass_rate': f"{self.passed_factors/self.total_factors*100:.1f}%" if self.total_factors > 0 else "0%",
            'results': self.results,
            'summary': self.summary
        }


class FactorValidationBatch:
    """
    批量因子验证器
    
    功能:
    1. 批量验证多个因子
    2. 生成对比报告
    3. 筛选有效因子
    4. 导出结果
    """
    
    def __init__(self,
                 ic_ir_threshold: float = 0.3,
                 pathway_threshold: float = 0.7,
                 min_ic_size: int = 10,
                 n_groups: int = 10):
        """
        Args:
            ic_ir_threshold: IC/IR 通过阈值
            pathway_threshold: 多轨道稳定性阈值
            min_ic_size: 最小样本量
            n_groups: 分组数量
        """
        self.validator = FactorValidator(
            ic_ir_threshold=ic_ir_threshold,
            pathway_threshold=pathway_threshold,
            min_ic_size=min_ic_size,
            n_groups=n_groups
        )
        self.thresholds = {
            'ic_ir': ic_ir_threshold,
            'pathway': pathway_threshold
        }
    
    def validate_single(self,
                       df: pd.DataFrame,
                       factor_col: str,
                       return_col: str,
                       date_col: str = 'date') -> FactorValidationResult:
        """验证单个因子"""
        return self.validator.validate(
            df, factor_col, return_col, date_col, factor_col
        )
    
    def validate_batch(self,
                      df: pd.DataFrame,
                      factor_cols: List[str],
                      return_col: str,
                      date_col: str = 'date') -> BatchValidationReport:
        """批量验证多个因子"""
        results = []
        passed = 0
        failed = 0
        
        print(f"开始批量验证 {len(factor_cols)} 个因子...")
        print("-" * 60)
        
        for i, factor in enumerate(factor_cols, 1):
            print(f"[{i}/{len(factor_cols)}] 验证因子: {factor}...", end=' ')
            
            try:
                result = self.validate_single(df, factor, return_col, date_col)
                result_dict = result.to_dict()
                results.append(result_dict)
                
                if result.pass_validation:
                    passed += 1
                    print(f"✓ 通过 (IR={result.ir:.2f}, 稳定性={result.pathway_stability:.2f})")
                else:
                    failed += 1
                    print(f"✗ 未通过 (IR={result.ir:.2f}, 稳定性={result.pathway_stability:.2f})")
                    
            except Exception as e:
                print(f"✗ 错误: {str(e)}")
                failed += 1
                results.append({
                    'factor_name': factor,
                    'error': str(e),
                    'pass_validation': False
                })
        
        print("-" * 60)
        print(f"验证完成: {passed} 通过, {failed} 未通过")
        
        # 生成汇总统计
        valid_results = [r for r in results if 'error' not in r]
        summary = self._generate_summary(valid_results)
        
        return BatchValidationReport(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_factors=len(factor_cols),
            passed_factors=passed,
            failed_factors=failed,
            results=results,
            summary=summary
        )
    
    def _generate_summary(self, results: List[Dict]) -> Dict:
        """生成汇总统计"""
        if not results:
            return {}
        
        # 提取数值指标
        ics = [r['ic_mean'] for r in results if 'ic_mean' in r]
        irs = [r['ir'] for r in results if 'ir' in r]
        sharpes = [r['sharpe_ls'] for r in results if 'sharpe_ls' in r]
        stabilities = [r['pathway_stability'] for r in results if 'pathway_stability' in r]
        
        def safe_stats(values):
            if not values:
                return {'mean': None, 'std': None, 'max': None, 'min': None}
            return {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'max': float(max(values)),
                'min': float(min(values))
            }
        
        return {
            'ic_statistics': safe_stats(ics),
            'ir_statistics': safe_stats(irs),
            'sharpe_statistics': safe_stats(sharpes),
            'stability_statistics': safe_stats(stabilities),
            'thresholds': self.thresholds
        }
    
    def get_valid_factors(self, report: BatchValidationReport) -> List[str]:
        """获取通过验证的因子列表"""
        return [
            r['factor_name'] for r in report.results
            if r.get('pass_validation', False)
        ]
    
    def get_top_factors(self,
                       report: BatchValidationReport,
                       metric: str = 'ir',
                       n: int = 5) -> List[Dict]:
        """获取排名靠前的因子"""
        valid_results = [
            r for r in report.results
            if 'error' not in r and metric in r
        ]
        
        sorted_results = sorted(
            valid_results,
            key=lambda x: abs(x[metric]),
            reverse=True
        )
        
        return sorted_results[:n]
    
    def export_report(self,
                     report: BatchValidationReport,
                     output_path: str,
                     format: str = 'json') -> str:
        """导出验证报告"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            file_path = output_path.with_suffix('.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
                
        elif format == 'csv':
            file_path = output_path.with_suffix('.csv')
            results_df = pd.DataFrame(report.results)
            results_df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
        elif format == 'markdown':
            file_path = output_path.with_suffix('.md')
            self._export_markdown(report, file_path)
            
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        return str(file_path)
    
    def _export_markdown(self, report: BatchValidationReport, file_path: Path):
        """导出 Markdown 格式报告"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 因子验证报告\n\n")
            f.write(f"**生成时间**: {report.timestamp}\n\n")
            
            # 汇总
            f.write("## 汇总\n\n")
            f.write(f"- 总因子数: {report.total_factors}\n")
            f.write(f"- 通过: {report.passed_factors}\n")
            f.write(f"- 未通过: {report.failed_factors}\n")
            f.write(f"- 通过率: {report.passed_factors/report.total_factors*100:.1f}%\n\n")
            
            # 阈值
            f.write("## 阈值设置\n\n")
            f.write(f"- IC/IR 阈值: {self.thresholds['ic_ir']}\n")
            f.write(f"- 多轨道稳定性阈值: {self.thresholds['pathway']}\n\n")
            
            # 详细结果
            f.write("## 详细结果\n\n")
            f.write("| 因子 | IC | IR | 夏普 | 稳定性 | 半衰期 | 单调性 | 状态 |\n")
            f.write("|------|-----|-----|------|--------|--------|--------|------|\n")
            
            for r in report.results:
                if 'error' in r:
                    f.write(f"| {r['factor_name']} | - | - | - | - | - | - | 错误 |\n")
                else:
                    status = "✓" if r['pass_validation'] else "✗"
                    f.write(f"| {r['factor_name']} | {r['ic_mean']:.4f} | "
                           f"{r['ir']:.2f} | {r['sharpe_ls']:.2f} | "
                           f"{r['pathway_stability']:.2f} | {r['half_life']} | "
                           f"{r['monotonicity_score']:.2f} | {status} |\n")


def run_batch_validation_example():
    """批量验证示例"""
    print("=" * 60)
    print("批量因子验证示例")
    print("=" * 60)
    
    # 创建模拟数据
    np.random.seed(42)
    
    # 10 个因子
    factors = ['momentum_5', 'momentum_20', 'volatility_20', 'rsi', 'macd',
               'volume_ratio', 'price_position', 'stoch_k', 'williams_r', 'adx']
    
    dates = pd.date_range('2024-01-01', periods=60, freq='D')
    symbols = [f'STOCK_{i:03d}' for i in range(100)]
    
    # 生成数据
    data = []
    for date in dates:
        for symbol in symbols:
            row = {'date': date, 'symbol': symbol}
            
            # 生成因子值
            for factor in factors:
                row[factor] = np.random.randn()
            
            # 生成收益 (与 momentum_20 正相关，与 volatility_20 负相关)
            row['return'] = (row['momentum_20'] * 0.1 - 
                           row['volatility_20'] * 0.05 + 
                           np.random.randn() * 0.02)
            
            data.append(row)
    
    df = pd.DataFrame(data)
    
    # 批量验证
    batch = FactorValidationBatch(
        ic_ir_threshold=0.2,  # 降低阈值以适应模拟数据
        pathway_threshold=0.6
    )
    
    report = batch.validate_batch(df, factors, 'return', 'date')
    
    # 获取有效因子
    valid_factors = batch.get_valid_factors(report)
    print(f"\n有效因子 ({len(valid_factors)}个): {valid_factors}")
    
    # 获取 Top 5 IR 因子
    top_ir = batch.get_top_factors(report, metric='ir', n=5)
    print(f"\nTop 5 IR 因子:")
    for i, f in enumerate(top_ir, 1):
        print(f"  {i}. {f['factor_name']}: IR={f['ir']:.2f}")
    
    # 导出报告
    output_path = batch.export_report(report, 'factor_validation_report', format='markdown')
    print(f"\n报告已导出: {output_path}")
    
    return report


if __name__ == '__main__':
    report = run_batch_validation_example()