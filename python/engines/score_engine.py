"""
Score Engine：聚合各子评分并基于权重计算 0-100 总分
提供 compute_from_series(df) 方法用于从 DataFrame 中已有子评分列计算总分
"""
from core.engine import BaseEngine
import pandas as pd

class ScoreEngine(BaseEngine):
    def __init__(self, params):
        super().__init__(params)
        default_weights = self.params.get('score', {}).get('WEIGHTS', None)
        if default_weights is None:
            self.weights = {
                'VOLUME':0.25,'TREND':0.20,'CHIP':0.15,'MONEY':0.15,'BREAKOUT':0.10,'RISK':0.15
            }
        else:
            self.weights = default_weights

        # normalize weights sum to 1
        total = sum(self.weights.values())
        if total==0:
            total=1
        for k in self.weights:
            self.weights[k]=self.weights[k]/total

        # max scores for normalization
        self.max_scores = {'VOLUME':25.0,'TREND':20.0,'CHIP':15.0,'MONEY':15.0,'BREAKOUT':10.0,'RISK':15.0}

    def compute(self, kline: pd.DataFrame):
        # not used in this context
        raise NotImplementedError

    def compute_from_series(self, df: pd.DataFrame):
        # expects columns: volume_score, trend_score, chip_score, money_score, break_score, risk_score
        vs = df['volume_score'].fillna(0)/self.max_scores['VOLUME']
        ts = df['trend_score'].fillna(0)/self.max_scores['TREND']
        cs = df['chip_score'].fillna(0)/self.max_scores['CHIP']
        ms = df['money_score'].fillna(0)/self.max_scores['MONEY']
        bs = df['break_score'].fillna(0)/self.max_scores['BREAKOUT']
        rs = df['risk_score'].fillna(0)/self.max_scores['RISK']

        total_pct = vs*self.weights['VOLUME'] + ts*self.weights['TREND'] + cs*self.weights['CHIP'] + ms*self.weights['MONEY'] + bs*self.weights['BREAKOUT'] + rs*self.weights['RISK']
        total_score = total_pct*100
        return total_score
