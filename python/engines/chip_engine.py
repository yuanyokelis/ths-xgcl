"""
筹码评分引擎（优先使用兼容层的真实筹码数据，否则使用近似算法）
输出：{ 'series': pd.Series, 'max_score':15.0, 'details': dict }
"""
from core.engine import BaseEngine
import pandas as pd
import numpy as np

class ChipEngine(BaseEngine):
    def compute(self, kline: pd.DataFrame):
        df = kline.copy()
        days = int(self.params.get('chip', {}).get('CHIP_DAYS', 60))
        # 检查是否有兼容层参数指示真实筹码可用
        compat = self.params.get('compat', {})
        if compat.get('has_winner') or compat.get('has_cost'):
            # 假设有真实筹码数据列 'chip_locked_pct'
            if 'chip_locked_pct' in df.columns:
                series = df['chip_locked_pct'].fillna(0).clip(0,100)/100*15
                return {'series': series, 'max_score':15.0, 'details': {'method':'real'}}
        # 近似算法：基于换手率与振幅
        if 'turnover' in df.columns:
            turnover = df['turnover'].fillna(0)
            tr = (df['high'] - df['low'])/df['low'].replace(0, np.nan)
            tr = tr.fillna(0)
            # 锁定度高 -> 高分
            lock_approx = turnover.rolling(days, min_periods=1).apply(lambda x: (x<0.5).sum())/days*100
            def score_row(x, amp):
                if x>60:
                    return 15
                if x>30 and amp<0.05:
                    return 12
                if x>20:
                    return 8
                return 4
            series = pd.Series([score_row(x,a) for x,a in zip(lock_approx, tr)], index=df.index)
            return {'series': series, 'max_score':15.0, 'details': {'method':'approx'}}
        # 无法计算
        series = pd.Series([5]*len(df), index=df.index)
        return {'series': series, 'max_score':15.0, 'details': {'method':'fallback'}}
