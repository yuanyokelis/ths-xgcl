"""
评分校准器（第八卷）

文件：python/tools/calibrator.py
功能：基于回测引擎与历史回测输出，自动生成一组推荐的评分权重（VOLUME/TREND/CHIP/MONEY/BREAKOUT/RISK）。

默认策略（按用户要求的“默认”）：
- 不直接覆盖 config/parameters.yaml，而是生成 config/parameters_calibrated.yaml
- 使用启发式网格搜索（权重步长 0.05，权重和为 1）在 quick 模式下对候选权重进行评估
- 目标函数与优化器一致：objective = annual_return + 0.5*sharpe - 0.5*abs(max_drawdown)
- 输出：outputs/calibrator/trials.csv, config/parameters_calibrated.yaml（最佳权重及元数据）

注意：该脚本在 quick 模式下会对每只股票使用最近 200 日数据并只选取前 5 支股票以加速评估；严谨模式会用全部样本与全部历史
"""
from __future__ import annotations
from pathlib import Path
import yaml
import argparse
import itertools
import csv
import json
import time
from typing import Dict, Any, List
import sys

# Ensure repo root and python/ on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PY_DIR = ROOT / 'python'
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))

try:
    from backtest.backtest_engine import BacktestEngine
except Exception:
    from python.backtest.backtest_engine import BacktestEngine


def load_params(path: Path) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(path: Path, obj: Dict[str, Any]):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(obj, f, allow_unicode=True)


def generate_weight_combinations(step: float = 0.1) -> List[Dict[str, float]]:
    # Generate combinations for 6 weights that sum to 1 using discrete step
    parts = [i for i in range(int(1/step)+1)]
    combos = []
    n = 6
    for indices in itertools.product(parts, repeat=n):
        if sum(indices) == int(1/step):
            weights = [round(i*step, 8) for i in indices]
            combos.append({
                'VOLUME': weights[0],
                'TREND': weights[1],
                'CHIP': weights[2],
                'MONEY': weights[3],
                'BREAKOUT': weights[4],
                'RISK': weights[5],
            })
    return combos


def objective_from_metrics(metrics: Dict[str, Any]) -> float:
    ann = metrics.get('annual_return', 0.0)
    max_dd = abs(metrics.get('max_drawdown', 0.0))
    sharpe = metrics.get('sharpe', 0.0)
    score = ann + 0.5 * sharpe - 0.5 * max_dd
    return score


class Calibrator:
    def __init__(self, base_params: Dict[str, Any], input_path: Path, out_dir: Path, step: float = 0.1, quick: bool = True):
        self.base_params = base_params
        self.input_path = input_path
        self.out_dir = out_dir
        self.step = step
        self.quick = quick
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.trials_file = out_dir / 'trials.csv'
        self.best_file = ROOT / 'config' / 'parameters_calibrated.yaml'

    def evaluate_weights(self, weights: Dict[str, float]) -> Dict[str, Any]:
        # prepare params copy with new weights
        params = yaml.safe_load(yaml.safe_dump(self.base_params))
        params.setdefault('score', {})
        params['score']['WEIGHTS'] = weights

        engine = BacktestEngine(params=params)
        # collect files
        if self.input_path.is_dir():
            files = list(self.input_path.glob('*.csv'))
            if self.quick:
                files = files[:min(len(files), 5)]
        else:
            files = [self.input_path]

        metrics_list = []
        for f in files:
            try:
                df = __import__('pandas').read_csv(f, parse_dates=['date']).sort_values('date')
                if self.quick and len(df) > 200:
                    df = df.iloc[-200:]
                res = engine.run(df, symbol=f.stem)
                metrics_list.append(res['metrics'])
            except Exception as e:
                metrics_list.append({'annual_return': -9999, 'max_drawdown': 9999, 'sharpe': 0.0})
        if not metrics_list:
            agg = {'annual_return': -9999, 'max_drawdown': 9999, 'sharpe': 0.0}
        else:
            ann = sum(m.get('annual_return', 0.0) for m in metrics_list) / len(metrics_list)
            dd = sum(m.get('max_drawdown', 0.0) for m in metrics_list) / len(metrics_list)
            sr = sum(m.get('sharpe', 0.0) for m in metrics_list) / len(metrics_list)
            agg = {'annual_return': ann, 'max_drawdown': dd, 'sharpe': sr}
        return agg

    def _append_trial(self, record: Dict[str, Any]):
        hdr = ['id', 'weights', 'objective', 'metrics', 'time']
        mode = 'a' if self.trials_file.exists() else 'w'
        with open(self.trials_file, mode, newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if mode == 'w':
                writer.writerow(hdr)
            writer.writerow([record['id'], json.dumps(record['weights'], ensure_ascii=False), record['objective'], json.dumps(record['metrics'], ensure_ascii=False), record['time']])

    def run(self):
        combos = generate_weight_combinations(step=self.step)
        if not combos:
            raise ValueError('no weight combinations generated, try larger step')
        best = None
        for i, w in enumerate(combos):
            start = time.time()
            metrics = self.evaluate_weights(w)
            obj = objective_from_metrics(metrics)
            elapsed = time.time() - start
            record = {'id': i, 'weights': w, 'metrics': metrics, 'objective': obj, 'time': elapsed}
            self._append_trial(record)
            if best is None or obj > best['objective']:
                best = record
                # save best to YAML (recommended, not overriding original)
                save_yaml(self.best_file, {'best': best, 'note': '自动生成的校准权重，未覆盖原始 parameters.yaml'})
        return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='输入目录或单个CSV文件')
    parser.add_argument('--out', default='outputs/calibrator', help='输出目录')
    parser.add_argument('--step', type=float, default=0.1, help='权重离散步长，例如0.1或0.05')
    parser.add_argument('--quick', action='store_true', help='快速模式：截取最近历史并仅选取前若干样本')
    args = parser.parse_args()

    base_params = load_params(ROOT / 'config' / 'parameters.yaml')
    cal = Calibrator(base_params=base_params, input_path=Path(args.input), out_dir=Path(args.out), step=args.step, quick=args.quick)
    best = cal.run()
    print('Calibration best:', best)


if __name__ == '__main__':
    main()
