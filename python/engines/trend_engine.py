"""
趋势评分引擎
输出：{ 'series': pd.Series, 'max_score':20.0, 'details': dict }
"""
from core.engine import BaseEngine
import pandas as pd
import numpy as np

class TrendEngine(BaseEngine):
    def compute(self, kline: pd.DataFrame):
        df = kline.copy()
        ma_fast = int(self.params.get('ma', {}).get('MA_FAST', 5))
        ma_mid = int(self.params.get('ma', {}).get('MA_MID', 20))
        ma_slow = int(self.params.get('ma', {}).get('MA_SLOW', 60))

        ma_f = df['close'].rolling(ma_fast, min_periods=1).mean()
        ma_m = df['close'].rolling(ma_mid, min_periods=1).mean()
        ma_s = df['close'].rolling(ma_slow, min_periods=1).mean()

        def score_row(f,m,s):
            # 角度和多头排列给高分
            if f>m and m>s:
                angle = (f - m)/m*100 if m!=0 else 0
                if angle>1:
                    return 20
                if angle>0.3:
                    return 15
                return 10
            # 中性
            if f>m or m>s:
                return 8
            # 空头
            return 3

        series = pd.Series([score_row(f,m,s) for f,m,s in zip(ma_f, ma_m, ma_s)], index=df.index)
        return {'series': series, 'max_score':20.0, 'details': {}}
