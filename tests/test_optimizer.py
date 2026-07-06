"""
自动参数优化单元测试（tests/test_optimizer.py）

该测试使用一个非常小的参数空间与一个小样本目录运行优化器的 grid 和 random 模式，验证能否产生输出文件（trials.csv, best_params.yaml）并返回最佳参数。
"""
from pathlib import Path
import yaml
import shutil
from python.tools.optimizer import Optimizer
from pathlib import Path


def make_dummy_stock():
    p = Path('tests/tmp_opt')
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)
    # 生成两只小样本股票CSV
    import pandas as pd
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
        df.to_csv(p / f"{s}.csv", index=False)
    return p


def test_optimizer_grid_and_random():
    p = make_dummy_stock()
    with open('config/param_grid_example.yaml', 'r', encoding='utf-8') as f:
        param_space = yaml.safe_load(f)
    with open('config/parameters.yaml', 'r', encoding='utf-8') as f:
        params = yaml.safe_load(f)
    out = Path('tests/opt_out')
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    opt = Optimizer(params=params, param_space=param_space, input_path=p, out_dir=out, mode='grid', budget=3, quick=True)
    best, trials = opt.run()
    assert (out / 'trials.csv').exists()
    assert (out / 'best_params.yaml').exists()
    # test random
    out2 = Path('tests/opt_out2')
    if out2.exists():
        shutil.rmtree(out2)
    out2.mkdir(parents=True, exist_ok=True)
    opt2 = Optimizer(params=params, param_space=param_space, input_path=p, out_dir=out2, mode='random', budget=3, quick=True)
    best2, trials2 = opt2.run()
    assert (out2 / 'trials.csv').exists()
    assert (out2 / 'best_params.yaml').exists()
