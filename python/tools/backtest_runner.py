"""
回测运行器：命令行工具，批量回测目录内多只股票并生成汇总报告
文件：python/tools/backtest_runner.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import yaml
import argparse
from python.backtest.backtest_engine import BacktestEngine


def load_params(path=Path('config/parameters.yaml')):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_directory(input_dir: Path, out_dir: Path, params: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    engine = BacktestEngine(params=params)
    for f in input_dir.glob('*.csv'):
        try:
            df = pd.read_csv(f, parse_dates=['date']).sort_values('date')
            res = engine.run(df, symbol=f.stem)
            # 存储每只的trades与equity
            sym_dir = out_dir / f.stem
            sym_dir.mkdir(parents=True, exist_ok=True)
            res['trades'].to_csv(sym_dir / 'trades.csv', index=False)
            res['equity'].to_csv(sym_dir / 'equity.csv', index=False)
            # 汇总指标
            metrics = res['metrics']
            metrics['symbol'] = f.stem
            summary.append(metrics)
        except Exception as e:
            print(f"回测 {f.stem} 出错: {e}")
    df_summary = pd.DataFrame(summary).sort_values('annual_return', ascending=False)
    df_summary.to_csv(out_dir / 'backtest_summary.csv', index=False)
    print('批量回测完成，汇总写入', out_dir / 'backtest_summary.csv')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='输入目录，包含多只日线CSV')
    parser.add_argument('--out', default='outputs/backtest', help='输出目录')
    args = parser.parse_args()
    params = load_params()
    run_directory(Path(args.input), Path(args.out), params)
