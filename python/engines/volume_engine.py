"""
成交量评分引擎
输出：{ 'series': pd.Series, 'max_score':25.0, 'details': dict }
"""
from core.engine import BaseEngine
import pandas as pd
import numpy as np

class VolumeEngine(BaseEngine):
    def compute(self, kline: pd.DataFrame):
        df = kline.copy()
        n_short = int(self.params.get('volume', {}).get('VOL_MA_SHORT', 5))
        n_long = int(self.params.get('volume', {}).get('VOL_MA_LONG', 20))
        vol = df['volume'].fillna(0)
        vol_ma_s = vol.rolling(n_short, min_periods=1).mean()
        vol_ma_l = vol.rolling(n_long, min_periods=1).mean()

        # 基本评分规则：0-25
        def score_row(v, v_s, v_l):
            if v_l==0:
                return 5
            if v > v_l * 1.5:
                return 25
            if v > v_s * 1.2:
                return 18
            if v > v_s:
                return 12
            return 5

        series = pd.Series([score_row(v, vs, vl) for v,vs,vl in zip(vol, vol_ma_s, vol_ma_l)], index=df.index)
        return {'series': series, 'max_score':25.0, 'details': {}}
