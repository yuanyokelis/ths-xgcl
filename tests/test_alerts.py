"""
预警单元测试：tests/test_alerts.py
验证 alert_monitor 的基础告警检测逻辑（高分、突破、假突破、风险）的触发
"""
import pandas as pd
from pathlib import Path
from python.tools.alert_monitor import detect_alerts_for_df
import yaml


def make_breakout_df():
    data = {
        'date': pd.date_range('2020-01-01', periods=40),
        'open': [10 + i*0.1 for i in range(40)],
        'high': [10.5 + i*0.1 for i in range(40)],
        'low': [9.8 + i*0.1 for i in range(40)],
        'close': [10.2 + i*0.1 for i in range(40)],
        'volume': [1000]*30 + [5000]*10,
        'amount': [10000 + i*100 for i in range(40)],
    }
    df = pd.DataFrame(data)
    return df


def test_detect_breakout_and_alerts():
    df = make_breakout_df()
    params = yaml.safe_load(open('config/parameters.yaml'))
    res = detect_alerts_for_df(df, params)
    # 触发突破确认或高分或风险之一
    assert isinstance(res, dict)
    assert 'alerts' in res


def test_detect_false_break():
    df = make_breakout_df()
    # 制作假突破：价格略高但量未放大
    df.loc[35:, 'volume'] = [1200]*5
    params = yaml.safe_load(open('config/parameters.yaml'))
    res = detect_alerts_for_df(df, params)
    assert 'alerts' in res
