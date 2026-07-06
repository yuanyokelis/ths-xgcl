"""
Volume Engine 单元测试占位（pytest）

测试目标：保证 Volume Engine 在空数据、合理数据下返回结构化结果。
"""
import pandas as pd
from core.engine import BaseEngine


def test_volume_engine_placeholder():
    # 构造空数据
    df = pd.DataFrame(columns=['date','open','high','low','close','volume','turnover'])

    class DummyVolume(BaseEngine):
        def compute(self, kline: pd.DataFrame):
            if kline.empty:
                return {'score': 0.0, 'max_score': 25.0, 'details': {'reason': 'empty'}}
            return {'score': 10.0, 'max_score': 25.0, 'details': {}}

    engine = DummyVolume(params={})
    res = engine.compute(df)
    assert isinstance(res, dict)
    assert 'score' in res and 'max_score' in res
    assert res['max_score'] == 25.0
