"""
因子验证模块 - 借鉴 quant 项目的统计方法
用于 DSS 生产环境的因子有效性检验
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy import stats


@dataclass
class FactorValidationResult:
    """因子验证结果"""
    factor_name: str
    ic_mean: float
    ic_std: float
    ir: float
    sharpe_ls: float
    sortino_long: float
    sortino_short: float
    max_drawdown: float
    calmar_ratio: float
    pathway_stability: float  # 多轨道稳定性得分
    half_life: Optional[int]  # IC半衰期
    monotonicity_score: float  # 单调性得分
    pass_validation: bool
    
    def to_dict(self) -> Dict:
        return {
            'factor_name': self.factor_name,
            'ic_mean': round(self.ic_mean, 4),
            'ic_std': round(self.ic_std, 4),
            'ir': round(self.ir, 2),
            'sharpe_ls': round(self.sharpe_ls, 2),
            'sortino_long': round(self.sortino_long, 2),
            'sortino_short': round(self.sortino_short, 2),
            'max_drawdown': round(self.max_drawdown, 4),
            'calmar_ratio': round(self.calmar_ratio, 2),
            'pathway_stability': round(self.pathway_stability, 2),
            'half_life': self.half_life,
            'monotonicity_score': round(self.monotonicity_score, 2),
            'pass_validation': self.pass_validation
        }


class FactorValidator:
    """
    因子验证器 - 基于 quant 项目的统计方法
    
    核心功能:
    1. IC/IR 计算 (Spearman 秩相关)
    2. 多空夏普比率
    3. 索替诺比率
    4. 多轨道稳健性检验
    5. IC 半衰期分析
    6. 分组单调性检验
    """
    
    def __init__(self, 
                 min_ic_size: int = 10,
                 n_groups: int = 10,
                 annual_trading_days: int = 242,
                 ic_ir_threshold: float = 0.5,
                 pathway_threshold: float = 0.8):
        """
        Args:
            min_ic_size: 计算 IC 的最小样本量
            n_groups: 分组数量
            annual_trading_days: 年化交易日数
            ic_ir_threshold: IC/IR 通过阈值
            pathway_threshold: 多轨道稳定性阈值
        """
        self.min_ic_size = min_ic_size
        self.n_groups = n_groups
        self.annual_trading_days = annual_trading_days
        self.ic_ir_threshold = ic_ir_threshold
        self.pathway_threshold = pathway_threshold
    
    def calc_ic(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """
        计算 Spearman IC (信息系数)
        
        Args:
            factor_values: 因子值序列
            returns: 下期收益序列
            
        Returns:
            Spearman 秩相关系数
        """
        # 过滤有效数据
        valid_idx = factor_values.notna() & returns.notna()
        fac_valid = factor_values[valid_idx]
        ret_valid = returns[valid_idx]
        
        if len(fac_valid) < self.min_ic_size:
            return np.nan
        
        # Spearman 秩相关
        ic, _ = stats.spearmanr(fac_valid, ret_valid)
        return ic
    
    def calc_ic_series(self, 
                       df: pd.DataFrame,
                       date_col: str,
                       factor_col: str,
                       return_col: str) -> pd.Series:
        """
        计算时序 IC 序列
        
        Args:
            df: DataFrame 包含日期、因子值、收益
            date_col: 日期列名
            factor_col: 因子列名
            return_col: 收益列名
            
        Returns:
            每日 IC 序列 (索引为日期列)
        """
        ic_list = []
        
        for date, group in df.groupby(date_col):
            ic = self.calc_ic(group[factor_col], group[return_col])
            ic_list.append({date_col: date, 'ic': ic})
        
        ic_df = pd.DataFrame(ic_list)
        return ic_df.set_index(date_col)['ic']
    
    def calc_ir(self, ic_series: pd.Series) -> float:
        """
        计算 IR (信息比率) = IC均值 / IC标准差
        """
        ic_valid = ic_series.dropna()
        if len(ic_valid) < 2:
            return np.nan
        return ic_valid.mean() / ic_valid.std()
    
    def calc_sharpe(self, returns: pd.Series) -> float:
        """
        计算年化夏普比率
        """
        if len(returns) < 2 or returns.std() == 0:
            return np.nan
        return returns.mean() / returns.std() * np.sqrt(self.annual_trading_days)
    
    def calc_sortino(self, returns: pd.Series) -> float:
        """
        计算年化索替诺比率 (只考虑下行波动)
        """
        downside = returns[returns < 0]
        if len(downside) < 2 or downside.std() == 0:
            return np.nan
        return returns.mean() / downside.std() * np.sqrt(self.annual_trading_days)
    
    def calc_max_drawdown(self, returns: pd.Series) -> float:
        """
        计算最大回撤
        """
        cumulative = (1 + returns).cumprod()
        peak = cumulative.expanding().max()
        drawdown = (peak - cumulative) / peak
        return drawdown.max()
    
    def calc_calmar(self, returns: pd.Series) -> float:
        """
        计算 Calmar 比率 = 年化收益 / 最大回撤
        """
        ann_return = (1 + returns.mean()) ** self.annual_trading_days - 1
        max_dd = self.calc_max_drawdown(returns)
        if max_dd == 0:
            return np.nan
        return ann_return / max_dd
    
    def calc_ic_half_life(self, ic_series: pd.Series, max_lag: int = 60) -> Optional[int]:
        """
        计算 IC 半衰期
        
        Args:
            ic_series: 日频 IC 序列
            max_lag: 最大滞后期
            
        Returns:
            半衰期 (天数), 若未找到返回 None
        """
        ic_1 = ic_series.mean()
        if np.isnan(ic_1) or ic_1 == 0:
            return None
        
        # 计算自相关
        autocorr = [ic_series.autocorr(lag=i) for i in range(1, max_lag + 1)]
        
        # 找到首次 |IC| <= |IC_1| / 2 的位置
        for i, ac in enumerate(autocorr, 1):
            if abs(ac) <= abs(ic_1) / 2:
                return i
        
        return None
    
    def calc_group_returns(self,
                          df: pd.DataFrame,
                          factor_col: str,
                          return_col: str,
                          date_col: str) -> pd.DataFrame:
        """
        计算分组收益
        
        Returns:
            DataFrame 包含各分组收益
        """
        results = []
        
        for date, group in df.groupby(date_col):
            if len(group) < self.n_groups:
                continue
            
            # 按因子值分组
            group['rank'] = group[factor_col].rank(pct=True)
            group['group'] = np.ceil(group['rank'] * self.n_groups).clip(1, self.n_groups)
            
            # 计算每组平均收益
            group_ret = group.groupby('group')[return_col].mean()
            group_ret['date'] = date
            results.append(group_ret)
        
        return pd.DataFrame(results).set_index('date')
    
    def calc_monotonicity(self, group_returns: pd.DataFrame) -> float:
        """
        计算单调性得分
        
        理想情况下: Group_10 > Group_9 > ... > Group_1
        得分范围: -1 到 1, 越高表示单调性越好
        """
        # 计算各分组平均收益
        mean_returns = group_returns.mean()
        
        # 计算排名相关性
        groups = mean_returns.index.astype(int)
        corr, _ = stats.spearmanr(groups, mean_returns.values)
        
        return corr if not np.isnan(corr) else 0.0
    
    def pathway_test(self,
                    df: pd.DataFrame,
                    factor_col: str,
                    return_col: str,
                    date_col: str,
                    n_pathways: int = 20) -> Dict:
        """
        多轨道稳健性测试
        
        通过偏移调仓日期，检验因子是否依赖"特定日期运气"
        
        Args:
            n_pathways: 轨道数量
            
        Returns:
            包含各轨道表现和稳定性得分的字典
        """
        # 获取唯一日期
        dates = df[date_col].unique()
        dates = sorted(dates)
        
        pathway_results = []
        
        for delay in range(n_pathways):
            # 偏移日期索引
            shifted_dates = dates[delay:] + [None] * delay
            date_map = dict(zip(dates, shifted_dates))
            
            # 应用偏移
            df_shifted = df.copy()
            df_shifted['shifted_date'] = df_shifted[date_col].map(date_map)
            df_shifted = df_shifted.dropna(subset=['shifted_date'])
            
            # 如果偏移后数据为空，跳过
            if df_shifted.empty:
                continue
            
            # 计算该轨道的 IC
            ic_series = self.calc_ic_series(df_shifted, 'shifted_date', factor_col, return_col)
            pathway_results.append({
                'pathway': delay,
                'ic_mean': ic_series.mean(),
                'ic_std': ic_series.std(),
                'ir': self.calc_ir(ic_series)
            })
        
        pathway_df = pd.DataFrame(pathway_results)
        
        # 计算稳定性得分 (1 - 变异系数)
        stability = 1 - pathway_df['ic_mean'].std() / abs(pathway_df['ic_mean'].mean())
        
        return {
            'pathway_results': pathway_df,
            'stability_score': max(0, stability),
            'best_pathway': pathway_df.loc[pathway_df['ic_mean'].idxmax(), 'pathway'],
            'worst_pathway': pathway_df.loc[pathway_df['ic_mean'].idxmin(), 'pathway']
        }
    
    def validate(self,
                df: pd.DataFrame,
                factor_col: str,
                return_col: str,
                date_col: str,
                factor_name: str = "unknown") -> FactorValidationResult:
        """
        完整因子验证流程
        
        Args:
            df: 包含因子值和收益的 DataFrame
            factor_col: 因子列名
            return_col: 收益列名
            date_col: 日期列名
            factor_name: 因子名称
            
        Returns:
            FactorValidationResult
        """
        # 1. 计算 IC 序列
        ic_series = self.calc_ic_series(df, date_col, factor_col, return_col)
        
        # 2. 基础统计
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        ir = self.calc_ir(ic_series)
        
        # 3. 分组收益
        group_rets = self.calc_group_returns(df, factor_col, return_col, date_col)
        
        # 4. 多空收益 (假设 Group_10 多头, Group_1 空头)
        if 10 in group_rets.columns and 1 in group_rets.columns:
            long_short = group_rets[10] - group_rets[1]
            sharpe_ls = self.calc_sharpe(long_short)
            sortino_long = self.calc_sortino(group_rets[10])
            sortino_short = self.calc_sortino(group_rets[1])
        else:
            sharpe_ls = sortino_long = sortino_short = np.nan
        
        # 5. 最大回撤和 Calmar
        if not long_short.empty:
            max_dd = self.calc_max_drawdown(long_short)
            calmar = self.calc_calmar(long_short)
        else:
            max_dd = calmar = np.nan
        
        # 6. 多轨道测试
        pathway_result = self.pathway_test(df, factor_col, return_col, date_col)
        stability = pathway_result['stability_score']
        
        # 7. IC 半衰期
        half_life = self.calc_ic_half_life(ic_series)
        
        # 8. 单调性
        monotonicity = self.calc_monotonicity(group_rets)
        
        # 9. 是否通过验证
        pass_val = (abs(ir) >= self.ic_ir_threshold and 
                    stability >= self.pathway_threshold)
        
        return FactorValidationResult(
            factor_name=factor_name,
            ic_mean=ic_mean,
            ic_std=ic_std,
            ir=ir,
            sharpe_ls=sharpe_ls,
            sortino_long=sortino_long,
            sortino_short=sortino_short,
            max_drawdown=max_dd,
            calmar_ratio=calmar,
            pathway_stability=stability,
            half_life=half_life,
            monotonicity_score=monotonicity,
            pass_validation=pass_val
        )


# ============ 便捷函数 ============

def winsorize(series: pd.Series, n: float = 3.0) -> pd.Series:
    """
    缩尾处理 - 来自 quant 项目
    将超过 n 倍标准差的值替换为边界值
    """
    mean, std = series.mean(), series.std()
    return series.clip(mean - n * std, mean + n * std)


def calc_rank_ic(factor_df: pd.DataFrame,
                 return_df: pd.DataFrame,
                 date_col: str = 'date') -> pd.Series:
    """
    计算 Rank IC (跨截面)
    
    Args:
        factor_df: 因子值 DataFrame (date, symbol, factor)
        return_df: 收益 DataFrame (date, symbol, return)
        
    Returns:
        每日 IC 序列
    """
    validator = FactorValidator()
    
    # 合并数据
    merged = factor_df.merge(return_df, on=[date_col, 'symbol'])
    
    return validator.calc_ic_series(merged, date_col, 'factor', 'return')


def quick_validate(factor_df: pd.DataFrame,
                  return_df: pd.DataFrame,
                  factor_name: str = "unknown",
                  date_col: str = 'date') -> Dict:
    """
    快速验证函数 - 一行代码完成因子检验
    
    Example:
        result = quick_validate(factor_df, return_df, "momentum_20")
        print(result['pass_validation'])  # True/False
    """
    validator = FactorValidator()
    
    # 确保日期列格式一致
    factor_df_copy = factor_df.copy()
    return_df_copy = return_df.copy()
    
    # 转换日期列为字符串以确保一致
    if pd.api.types.is_datetime64_any_dtype(factor_df_copy[date_col]):
        factor_df_copy[date_col] = factor_df_copy[date_col].dt.strftime('%Y-%m-%d')
    if pd.api.types.is_datetime64_any_dtype(return_df_copy[date_col]):
        return_df_copy[date_col] = return_df_copy[date_col].dt.strftime('%Y-%m-%d')
    
    merged = factor_df_copy.merge(return_df_copy, on=[date_col, 'symbol'])
    
    result = validator.validate(merged, 'factor', 'return', date_col, factor_name)
    return result.to_dict()
