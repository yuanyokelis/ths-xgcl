"""
校准单元测试 tests/test_calibrator.py
"""
from pathlib import Path
import shutil
from python.tools.calibrator import Calibrator
import yaml


def make_dummy_stock_for_calib():
    p = Path('tests/tmp_calib')
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)
    import pandas as pd
    for s in ['AAA','BBB']:
        df = pd.DataFrame({
            'date': pd.date_range('2020-01-01', periods=120),
            'open': [10 + i*0.02 for i in range(120)],
            'high': [10.5 + i*0.02 for i in range(120)],
            'low': [9.8 + i*0.02 for i in range(120)],
            'close': [10.2 + i*0.02 for i in range(120)],
            'volume': [1000 + (i%5)*50 for i in range(120)],
            'amount': [10000 + i*10 for i in range(120)],
        })
        df.to_csv(p / f"{s}.csv", index=False)
    return p


def test_calibrator_runs_quick():
    p = make_dummy_stock_for_calib()
    with open('config/parameters.yaml', 'r', encoding='utf-8') as f:
        base_params = yaml.safe_load(f)
    out = Path('tests/calib_out')
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    cal = Calibrator(base_params=base_params, input_path=p, out_dir=out, step=0.5, quick=True)
    best = cal.run()
    assert 'weights' in best
    assert (Path('config') / 'parameters_calibrated.yaml').exists()
