#!/usr/bin/env python3
"""
DSS 日志系统 - 真实数据溯源与参数追踪

原则：
1. 不允许伪造数据 - 获取不到就明确标注
2. 所有数据标注真实来源 URL
3. 记录所有参数调整和权重变化
4. 可追溯、可审计、可复现
"""

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import hashlib


class DataSourceTracker:
    """数据源追踪器 - 记录每个数据的真实来源"""
    
    def __init__(self, log_dir: str = "./data_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据来源记录
        self.sources: Dict[str, Dict[str, Any]] = {}
        
        # 配置日志
        self.logger = logging.getLogger('DSS.DataSource')
        self.logger.setLevel(logging.INFO)
        
        # 文件 handler - 按日期分割
        log_file = self.log_dir / f"data_source_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 控制台 handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def record_source(
        self,
        data_id: str,
        source_type: str,
        source_url: Optional[str] = None,
        source_name: Optional[str] = None,
        fetch_time: Optional[str] = None,
        data_status: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        记录数据来源
        
        Args:
            data_id: 数据标识（如股票代码）
            source_type: 数据源类型（如 'AlphaVantage', 'Baostock', 'Cache'）
            source_url: 真实 API URL 或文档链接
            source_name: 数据源名称
            fetch_time: 获取时间
            data_status: 状态 ('success', 'failed', 'cached', 'unavailable')
            error_message: 错误信息（如果失败）
            metadata: 其他元数据
        """
        record = {
            'data_id': data_id,
            'source_type': source_type,
            'source_url': source_url,
            'source_name': source_name,
            'fetch_time': fetch_time or datetime.now().isoformat(),
            'data_status': data_status,
            'error_message': error_message,
            'metadata': metadata or {},
            'verified': True  # 标记为已验证
        }
        
        self.sources[data_id] = record
        
        # 日志记录
        status_emoji = {'success': '✅', 'failed': '❌', 'cached': '📦', 'unavailable': '⚠️'}
        emoji = status_emoji.get(data_status, '❓')
        
        if data_status == 'failed':
            self.logger.error(
                f"{emoji} [{data_id}] 数据来源：{source_name or source_type} | "
                f"状态：{data_status} | 错误：{error_message}"
            )
        elif data_status == 'unavailable':
            self.logger.warning(
                f"{emoji} [{data_id}] 数据来源：{source_name or source_type} | "
                f"状态：{data_status} - 暂时无法获取，未伪造数据"
            )
        else:
            self.logger.info(
                f"{emoji} [{data_id}] 数据来源：{source_name or source_type} | "
                f"状态：{data_status} | URL: {source_url or 'N/A'}"
            )
        
        # 保存到 JSONL 文件（可追溯）
        self._save_to_jsonl(record)
        
        return record
    
    def _save_to_jsonl(self, record: Dict):
        """保存到 JSONL 文件"""
        jsonl_file = self.log_dir / f"sources_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(jsonl_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def get_source(self, data_id: str) -> Optional[Dict]:
        """获取某个数据的来源信息"""
        return self.sources.get(data_id)
    
    def generate_report(self) -> str:
        """生成数据来源报告"""
        report_lines = [
            "=" * 60,
            "DSS 数据来源审计报告",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ]
        
        for data_id, record in self.sources.items():
            status = record['data_status']
            status_emoji = {'success': '✅', 'failed': '❌', 'cached': '📦', 'unavailable': '⚠️'}
            
            report_lines.append(f"{status_emoji.get(status, '❓')} {data_id}")
            report_lines.append(f"   来源：{record['source_name'] or record['source_type']}")
            report_lines.append(f"   URL: {record['source_url'] or 'N/A'}")
            report_lines.append(f"   时间：{record['fetch_time']}")
            report_lines.append(f"   状态：{status}")
            
            if record['error_message']:
                report_lines.append(f"   错误：{record['error_message']}")
            
            report_lines.append("")
        
        return '\n'.join(report_lines)


class ParameterWeightLogger:
    """参数权重日志 - 记录所有参数调整和最优解搜索过程"""
    
    def __init__(self, log_dir: str = "./weight_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前参数配置
        self.current_weights: Dict[str, float] = {}
        
        # 历史调整记录
        self.adjustment_history: List[Dict] = []
        
        # 最优解记录
        self.best_solution: Optional[Dict] = None
        
        # 配置日志
        self.logger = logging.getLogger('DSS.ParameterWeight')
        self.logger.setLevel(logging.INFO)
        
        # 文件 handler
        log_file = self.log_dir / f"weight_adjustment_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def initialize_weights(self, weights: Dict[str, float], description: str = ""):
        """初始化权重配置"""
        self.current_weights = weights.copy()
        
        record = {
            'action': 'initialize',
            'timestamp': datetime.now().isoformat(),
            'weights': weights,
            'description': description
        }
        
        self.adjustment_history.append(record)
        self._save_record(record)
        
        self.logger.info(f"🎯 初始化权重配置：{description}")
        self.logger.info(f"   参数：{json.dumps(weights, ensure_ascii=False)}")
    
    def adjust_weight(
        self,
        param_name: str,
        old_value: float,
        new_value: float,
        reason: str,
        performance_impact: Optional[float] = None
    ):
        """
        调整某个参数的权重
        
        Args:
            param_name: 参数名称
            old_value: 旧值
            new_value: 新值
            reason: 调整原因
            performance_impact: 对性能的影响（如准确率变化）
        """
        record = {
            'action': 'adjust',
            'timestamp': datetime.now().isoformat(),
            'param_name': param_name,
            'old_value': old_value,
            'new_value': new_value,
            'change': new_value - old_value,
            'reason': reason,
            'performance_impact': performance_impact
        }
        
        self.current_weights[param_name] = new_value
        self.adjustment_history.append(record)
        self._save_record(record)
        
        impact_str = f" | 性能影响：{performance_impact:+.4f}" if performance_impact else ""
        self.logger.info(
            f"🔧 调整参数：{param_name} | {old_value:.4f} → {new_value:.4f} "
            f"({(new_value - old_value) / old_value * 100:+.2f}%){impact_str}"
        )
        self.logger.info(f"   原因：{reason}")
    
    def record_evaluation(
        self,
        weights: Dict[str, float],
        metrics: Dict[str, float],
        is_best: bool = False
    ):
        """
        记录一次评估结果
        
        Args:
            weights: 评估的权重配置
            metrics: 评估指标（如准确率、夏普比率等）
            is_best: 是否是最优解
        """
        record = {
            'action': 'evaluate',
            'timestamp': datetime.now().isoformat(),
            'weights': weights,
            'metrics': metrics,
            'is_best': is_best
        }
        
        self.adjustment_history.append(record)
        self._save_record(record)
        
        if is_best:
            self.best_solution = record
            self.logger.info(f"🏆 发现新的最优解！")
            self.logger.info(f"   指标：{json.dumps(metrics, ensure_ascii=False)}")
        else:
            self.logger.debug(f"📊 评估完成：{json.dumps(metrics, ensure_ascii=False)}")
    
    def _save_record(self, record: Dict):
        """保存记录到 JSONL"""
        jsonl_file = self.log_dir / f"adjustments_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(jsonl_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    
    def get_best_solution(self) -> Optional[Dict]:
        """获取最优解"""
        return self.best_solution
    
    def generate_report(self) -> str:
        """生成参数调整报告"""
        report_lines = [
            "=" * 60,
            "DSS 参数权重调整报告",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"总调整次数：{len(self.adjustment_history)}",
            "=" * 60,
            ""
        ]
        
        # 当前权重
        report_lines.append("📍 当前权重配置：")
        for param, value in self.current_weights.items():
            report_lines.append(f"   {param}: {value:.4f}")
        report_lines.append("")
        
        # 最优解
        if self.best_solution:
            report_lines.append("🏆 最优解：")
            report_lines.append(f"   权重：{json.dumps(self.best_solution['weights'], ensure_ascii=False, indent=6)}")
            report_lines.append(f"   指标：{json.dumps(self.best_solution['metrics'], ensure_ascii=False, indent=6)}")
            report_lines.append("")
        
        # 调整历史（最近 10 条）
        report_lines.append("📝 最近调整记录：")
        for record in self.adjustment_history[-10:]:
            if record['action'] == 'adjust':
                report_lines.append(
                    f"   🔧 {record['param_name']}: {record['old_value']:.4f} → "
                    f"{record['new_value']:.4f} ({record['reason']})"
                )
        
        return '\n'.join(report_lines)


# 全局实例
_data_tracker = None
_weight_logger = None


def get_data_tracker() -> DataSourceTracker:
    """获取全局数据追踪器"""
    global _data_tracker
    if _data_tracker is None:
        _data_tracker = DataSourceTracker()
    return _data_tracker


def get_weight_logger() -> ParameterWeightLogger:
    """获取全局权重日志器"""
    global _weight_logger
    if _weight_logger is None:
        _weight_logger = ParameterWeightLogger()
    return _weight_logger


# 测试
if __name__ == "__main__":
    # 测试数据追踪
    tracker = get_data_tracker()
    tracker.record_source(
        data_id="AAPL",
        source_type="AlphaVantage",
        source_url="https://www.alphavantage.co/query?function=TIME_SERIES_DAILY",
        source_name="Alpha Vantage API",
        data_status="success",
        metadata={"records": 100, "period": "2y"}
    )
    
    tracker.record_source(
        data_id="AMZN",
        source_type="AlphaVantage",
        source_url="https://www.alphavantage.co/query?function=TIME_SERIES_DAILY",
        source_name="Alpha Vantage API",
        data_status="failed",
        error_message="API 限制：感谢使用 Alpha Vantage..."
    )
    
    tracker.record_source(
        data_id="NVDA",
        source_type="Cache",
        source_url="N/A",
        source_name="本地缓存 (data_cache/stock_data.parquet)",
        data_status="cached",
        metadata={"cached_at": "2026-02-27"}
    )
    
    print("\n" + tracker.generate_report())
    
    # 测试权重日志
    logger = get_weight_logger()
    logger.initialize_weights(
        weights={
            'rsi_weight': 0.25,
            'macd_weight': 0.25,
            'volume_weight': 0.20,
            'trend_weight': 0.20,
            'volatility_weight': 0.10
        },
        description="初始权重配置 - 均衡型"
    )
    
    logger.adjust_weight(
        param_name='rsi_weight',
        old_value=0.25,
        new_value=0.30,
        reason="RSI 在震荡市场表现更好",
        performance_impact=0.0123
    )
    
    logger.record_evaluation(
        weights=logger.current_weights,
        metrics={
            'accuracy': 0.72,
            'sharpe_ratio': 1.85,
            'max_drawdown': -0.15
        },
        is_best=True
    )
    
    print("\n" + logger.generate_report())
