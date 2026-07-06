"""
单元测试：test_main_chart.py
验证 Python 验证脚本在边界条件下的行为
"""
import pandas as pd
from python.tools.main_chart_validator import compute_scores


def test_compute_scores_empty():
    df = pd.DataFrame(columns=['date','open','high','low','close','volume'])
    params = {
        'ma': {'MA_FAST':5,'MA_MID':20,'MA_SLOW':60,'MA_LONG':120},
        'atr': {'ATR_PERIOD':14},
        'volume': {'VOL_MA_SHORT':5,'VOL_MA_LONG':20,'VOLUME_RATE_THRESHOLD':1.5},
        'breakout': {'BREAK_DAYS':30,'BREAK_VOLUME_MULT':2.0},
        'chip': {'CHIP_DAYS':60},
    }
    # Should not raise
    res = compute_scores(df, params)
    assert 'total_score' in res.columns or res.empty


def test_compute_scores_simple():
    data = {
        'date': pd.date_range('2020-01-01', periods=10),
        'open': [10,10.5,10.8,11,11.2,11.5,11.8,12,12.5,12.8],
        'high': [10.6,10.9,11,11.2,11.6,11.9,12,12.6,12.9,13],
        'low': [9.8,10,10.5,10.8,11,11.2,11.6,11.9,12.2,12.5],
        'close': [10.5,10.8,10.9,11.1,11.5,11.8,11.9,12.4,12.7,12.9],
        'volume': [1000,1100,900,1200,1300,1500,1600,1700,1400,1800],
    }
    df = pd.DataFrame(data)
    params = {
        'ma': {'MA_FAST':5,'MA_MID':20,'MA_SLOW':60,'MA_LONG':120},
        'atr': {'ATR_PERIOD':14},
        'volume': {'VOL_MA_SHORT':5,'VOL_MA_LONG':20,'VOLUME_RATE_THRESHOLD':1.5},
        'breakout': {'BREAK_DAYS':30,'BREAK_VOLUME_MULT':2.0},
        'chip': {'CHIP_DAYS':60},
    }
    res = compute_scores(df, params)
    assert 'total_score' in res.columns
    assert res['total_score'].dtype in (int, float) or pd.api.types.is_numeric_dtype(res['total_score'])
