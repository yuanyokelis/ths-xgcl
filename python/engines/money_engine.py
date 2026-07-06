"""
资金行为评分引擎
通过成交额、换手率、K线形态推断吸筹/洗盘/拉升等并给分
输出：{ 'series': pd.Series, 'max_score':15.0, 'details': dict }
"""
from core.engine import BaseEngine
import pandas as pd
import numpy as np

class MoneyEngine(BaseEngine):
    def compute(self, kline: pd.DataFrame):
        df = kline.copy()
        # 使用成交额/换手/连续阳线等特征
        amount_col = 'amount' if 'amount' in df.columns else None
        close = df['close']
        openp = df.get('open', close)
        vol = df.get('volume', pd.Series([0]*len(df)))

        # 连续阳线计数
        up = (close > openp).astype(int)
        consec_up = up.groupby((up!=up.shift()).cumsum()).cumsum()

        def score_row(a, upc, v):
            s = 5
            if a is not None and a>0 and v>0 and v>np.nanmean(v):
                s += 4
            if upc>=3:
                s += 6
            if upc==0 and v>np.nanmean(v)*2:
                s -= 4
            return max(0, min(15, s))

        amounts = df['amount'] if amount_col else pd.Series([0]*len(df))
        # use rolling mean vol for comparison
        vmean = vol.rolling(20, min_periods=1).mean().fillna(0)
        series = pd.Series([score_row(a, u, vv) for a,u,vv in zip(amounts, consec_up, vol)], index=df.index)
        return {'series': series, 'max_score':15.0, 'details': {}}
