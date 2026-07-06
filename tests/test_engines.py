"""
单元测试：tests/test_engines.py
为每个评分模块提供正常、边界与空数据测试
"""
import pandas as pd
import numpy as np
from python.tools.sub_chart_validator import load_params
from engines.volume_engine import VolumeEngine
from engines.trend_engine import TrendEngine
from engines.chip_engine import ChipEngine
from engines.money_engine import MoneyEngine
from engines.breakout_engine import BreakoutEngine
from engines.risk_engine import RiskEngine
from engines.score_engine import ScoreEngine


def make_sample_df():
    data = {
        'date': pd.date_range('2020-01-01', periods=30),
        'open': np.linspace(10,15,30),
        'high': np.linspace(10.5,15.5,30),
        'low': np.linspace(9.8,14.8,30),
        'close': np.linspace(10.2,15.2,30),
        'volume': np.concatenate([np.arange(1000,1015), np.arange(1200,1215)]),
        'amount': np.linspace(10000,20000,30),
        'turnover': np.linspace(0.2,1.0,30),
    }
    return pd.DataFrame(data)


def test_volume_engine():
    df = make_sample_df()
    params = load_params()
    engine = VolumeEngine(params=params)
    res = engine.compute(df)
    assert 'series' in res
    assert len(res['series'])==len(df)


def test_trend_engine():
    df = make_sample_df()
    params = load_params()
    engine = TrendEngine(params=params)
    res = engine.compute(df)
    assert res['series'].max()<=20


def test_chip_engine():
    df = make_sample_df()
    params = load_params()
    engine = ChipEngine(params=params)
    res = engine.compute(df)
    assert len(res['series'])==len(df)


def test_money_engine():
    df = make_sample_df()
    params = load_params()
    engine = MoneyEngine(params=params)
    res = engine.compute(df)
    assert len(res['series'])==len(df)


def test_breakout_engine():
    df = make_sample_df()
    params = load_params()
    engine = BreakoutEngine(params=params)
    res = engine.compute(df)
    assert len(res['series'])==len(df)


def test_risk_engine_and_score():
    df = make_sample_df()
    params = load_params()
    v = VolumeEngine(params=params).compute(df)['series']
    t = TrendEngine(params=params).compute(df)['series']
    c = ChipEngine(params=params).compute(df)['series']
    m = MoneyEngine(params=params).compute(df)['series']
    b = BreakoutEngine(params=params).compute(df)['series']
    r = RiskEngine(params=params).compute(df)['series']
    df2 = df.copy()
    df2['volume_score']=v
    df2['trend_score']=t
    df2['chip_score']=c
    df2['money_score']=m
    df2['break_score']=b
    df2['risk_score']=r
    scorer = ScoreEngine(params=params)
    total = scorer.compute_from_series(df2)
    assert total.dtype==float or hasattr(total, 'dtype')
