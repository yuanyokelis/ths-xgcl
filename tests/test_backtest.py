"""
回测单元测试：tests/test_backtest.py
验证回测引擎在简单样本上的行为
"""
import pandas as pd
from pathlib import Path
from python.backtest.backtest_engine import BacktestEngine
import yaml


def make_sample_df():
    data = {
        'date': pd.date_range('2020-01-01', periods=60),
        'open': [10 + i*0.05 for i in range(60)],
        'high': [10.5 + i*0.05 for i in range(60)],
        'low': [9.8 + i*0.05 for i in range(60)],
        'close': [10.2 + i*0.05 for i in range(60)],
        'volume': [1000 + (i%10)*100 for i in range(60)],
        'amount': [10000 + i*50 for i in range(60)],
    }
    return pd.DataFrame(data)


def test_backtest_run():
    params = yaml.safe_load(open('config/parameters.yaml'))
    df = make_sample_df()
    engine = BacktestEngine(params=params)
    res = engine.run(df, symbol='TEST')
    assert 'trades' in res
    assert 'equity' in res
    assert 'metrics' in res
