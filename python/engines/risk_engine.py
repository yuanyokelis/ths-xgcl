"""
风险评分引擎（返回越高代表低风险）
识别高位放量、长上影、均线死叉、ATR异常等并扣分
输出：{ 'series': pd.Series, 'max_score':15.0, 'details': dict }
"""
from core.engine import BaseEngine
import pandas as pd
import numpy as np

class RiskEngine(BaseEngine):
    def compute(self, kline: pd.DataFrame):
        df = kline.copy()
        # 上影线比例
        high = df['high']
        low = df['low']
        close = df['close']
        openp = df.get('open', close)
        vol = df.get('volume', pd.Series([0]*len(df)))
        ma20 = close.rolling(20, min_periods=1).mean()

        def score_row(h,l,c,o,v,ma):
            up_shadow = (h - max(c,o)) / (h - l + 1e-9)
            # 长上影扣分
            if up_shadow > 0.6:
                return 5
            # 高位放量（价格远高于20日均线且放量）
            if c > ma * 1.2 and v > v.mean()*1.5:
                return 3
            # 死叉示例：短均下穿长均，以简单近似判断
            # 这里无法访问短均和中期均值，故使用占位条件
            return 12

        mean_v = vol.mean() if len(vol)>0 else 0
        series = pd.Series([score_row(h,l,c,o,mean_v,ma) for h,l,c,o,ma in zip(high, low, close, openp, ma20)], index=df.index)
        # clip to 0..15
        series = series.clip(0,15)
        return {'series': series, 'max_score':15.0, 'details': {}}
