"""
突破评分引擎
检测平台/箱体/三角等的近似突破并评分
输出：{ 'series': pd.Series, 'max_score':10.0, 'details': dict }
"""
from core.engine import BaseEngine
import pandas as pd
import numpy as np

class BreakoutEngine(BaseEngine):
    def compute(self, kline: pd.DataFrame):
        df = kline.copy()
        days = int(self.params.get('breakout', {}).get('BREAK_DAYS', 30))
        mult = float(self.params.get('breakout', {}).get('BREAK_VOLUME_MULT', 2.0))
        hh = df['high'].rolling(days, min_periods=1).max()
        ll = df['low'].rolling(days, min_periods=1).min()
        vol = df['volume'].fillna(0)
        prev_vol = vol.shift(1).fillna(0)

        def score_row(c, hhi, v, pv):
            if c>hhi and v>pv*mult and pv>0:
                return 10
            if c>hhi:
                return 4
            return 0

        series = pd.Series([score_row(c,h,v,pv) for c,h,v,pv in zip(df['close'], hh.shift(1).fillna(df['close']), vol, prev_vol)], index=df.index)
        return {'series': series, 'max_score':10.0, 'details': {}}
