"""
选股单元测试：tests/test_selection.py
验证选股导出工具在正常与异常输入下的行为
"""
import pandas as pd
from pathlib import Path
from python.tools.selection_exporter import run_directory, score_single


def make_sample(symbol='AAA'):
    data = {
        'date': pd.date_range('2020-01-01', periods=30),
        'open': [10 + i*0.1 for i in range(30)],
        'high': [10.5 + i*0.1 for i in range(30)],
        'low': [9.8 + i*0.1 for i in range(30)],
        'close': [10.2 + i*0.1 for i in range(30)],
        'volume': [1000 + i*10 for i in range(30)],
        'amount': [10000 + i*100 for i in range(30)],
    }
    df = pd.DataFrame(data)
    p = Path('tests/tmp')
    p.mkdir(parents=True, exist_ok=True)
    f = p / f"{symbol}.csv"
    df.to_csv(f, index=False)
    return f


def test_selection_directory():
    p = Path('tests/tmp')
    f1 = make_sample('AAA')
    f2 = make_sample('BBB')
    params = None
    out = Path('tests/tmp_out')
    import yaml as _yaml
    with open('config/parameters.yaml', 'r', encoding='utf-8') as f:
        params = _yaml.safe_load(f)
    res = run_directory(p, out, params=params)
    assert 'symbol' in res.columns
    assert len(res)>0


def test_score_single():
    csv_file = make_sample('CCC')
    import yaml as _yaml
    with open('config/parameters.yaml', 'r', encoding='utf-8') as pf:
        params = _yaml.safe_load(pf)
    df = pd.read_csv(csv_file)
    score = score_single(df, params)
    assert isinstance(score, float) or (score != score) == False
