"""
集成测试：tests/test_integration.py
验证从头到尾的关键工具能在小数据集上运行（选股导出与回测运行器等）。
"""
import shutil
from pathlib import Path
import pandas as pd
import yaml

from python.tools.selection_exporter import run_directory as run_selection
from python.tools.backtest_runner import run_directory as run_backtest


def make_sample_stocks(tmp_dir: Path):
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for s in ['AAA','BBB']:
        df = pd.DataFrame({
            'date': pd.date_range('2020-01-01', periods=60),
            'open': [10 + i*0.02 for i in range(60)],
            'high': [10.5 + i*0.02 for i in range(60)],
            'low': [9.8 + i*0.02 for i in range(60)],
            'close': [10.2 + i*0.02 for i in range(60)],
            'volume': [1000 + (i%5)*50 for i in range(60)],
            'amount': [10000 + i*10 for i in range(60)],
        })
        df.to_csv(tmp_dir / f"{s}.csv", index=False)
    return list(tmp_dir.glob('*.csv'))


def test_end_to_end(tmp_path):
    data_dir = tmp_path / 'data'
    out_sel = tmp_path / 'out_sel'
    out_bt = tmp_path / 'out_bt'
    make_sample_stocks(data_dir)
    params = yaml.safe_load(open('config/parameters.yaml'))
    # 运行选股
    run_selection(data_dir, out_sel, params)
    assert (out_sel / 'selection_results.csv').exists()
    # 运行回测
    run_backtest(data_dir, out_bt, params)
    assert (out_bt / 'backtest_summary.csv').exists()
