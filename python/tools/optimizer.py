"""
自动参数优化器（第七卷）

文件：python/tools/optimizer.py
功能：支持 grid、random、bayes（可选 optuna）三种搜索策略，通过调用回测引擎评估每组参数的回测表现，输出最佳参数和试验记录。

用法示例：
  python python/tools/optimizer.py --mode grid --param-space config/param_grid_example.yaml --input data/stocks --out outputs/optimizer --budget 20

说明：为了安全性与兼容性，贝叶斯优化仅在检测到 optuna 已安装时启用，否则自动降级为随机搜索。
"""
from __future__ import annotations
from pathlib import Path
import yaml
import argparse
import itertools
import random
import csv
import time
import json
import math
from typing import Dict, Any, List

# Ensure repo root and python/ on path
import sys
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PY_DIR = ROOT / 'python'
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))

try:
    from backtest.backtest_engine import BacktestEngine
except Exception:
    from python.backtest.backtest_engine import BacktestEngine

# Try to import optuna for bayesian optimization
try:
    import optuna
    HAS_OPTUNA = True
except Exception:
    HAS_OPTUNA = False


def load_params(path: Path) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def expand_grid(param_space: Dict[str, Any]) -> List[Dict[str, Any]]:
    # param_space is dict param-> {type: 'int'/'float'/'choice', values: [...] or range}
    keys = list(param_space.keys())
    lists = []
    for k in keys:
        spec = param_space[k]
        t = spec.get('type', 'choice')
        if t == 'choice':
            lists.append(spec.get('values', []))
        elif t in ('int', 'float'):
            start = spec['min']
            end = spec['max']
            step = spec.get('step', 1)
            if t == 'int':
                lists.append(list(range(int(start), int(end)+1, int(step))))
            else:
                vals = []
                v = float(start)
                while v <= float(end) + 1e-9:
                    vals.append(round(v, 8))
                    v += float(step)
                lists.append(vals)
        else:
            lists.append(spec.get('values', []))
    combos = []
    for prod in itertools.product(*lists):
        combos.append({k: v for k, v in zip(keys, prod)})
    return combos


def sample_random(param_space: Dict[str, Any], n: int) -> List[Dict[str, Any]]:
    keys = list(param_space.keys())
    samples = []
    for _ in range(n):
        sample = {}
        for k in keys:
            spec = param_space[k]
            t = spec.get('type', 'choice')
            if t == 'choice':
                sample[k] = random.choice(spec.get('values', []))
            elif t == 'int':
                sample[k] = random.randint(int(spec['min']), int(spec['max']))
            elif t == 'float':
                sample[k] = random.uniform(float(spec['min']), float(spec['max']))
                # apply step if provided
                step = spec.get('step')
                if step:
                    sample[k] = round(round(sample[k]/step)*step, 8)
            else:
                sample[k] = random.choice(spec.get('values', []))
        samples.append(sample)
    return samples


def objective_from_metrics(metrics: Dict[str, Any]) -> float:
    # 默认目标：优先最大化年化收益，并兼顾回撤（penalize by max_drawdown）
    # objective higher is better
    ann = metrics.get('annual_return', 0.0)
    max_dd = abs(metrics.get('max_drawdown', 0.0))
    sharpe = metrics.get('sharpe', 0.0)
    # composite score
    score = ann * 1.0 + sharpe * 0.5 - max_dd * 0.5
    return score


class Optimizer:
    def __init__(self, params: Dict[str, Any], param_space: Dict[str, Any], input_path: Path, out_dir: Path, mode: str = 'grid', budget: int = 50, workers: int = 1, quick: bool = True):
        self.params = params
        self.param_space = param_space
        self.input_path = input_path
        self.out_dir = out_dir
        self.mode = mode
        self.budget = budget
        self.workers = workers
        self.quick = quick
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.trials_file = out_dir / 'trials.csv'
        self.best_file = out_dir / 'best_params.yaml'

    def evaluate_params(self, trial_params: Dict[str, Any]) -> Dict[str, Any]:
        # Merge trial_params into base params
        trial_conf = yaml.safe_load(yaml.safe_dump(self.params))
        # set nested keys if dot notation used
        for k, v in trial_params.items():
            parts = k.split('.')
            cur = trial_conf
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            cur[parts[-1]] = v

        # For speed in quick mode, we may sample subset of files or shorten history
        symbols = []
        if self.input_path.is_dir():
            files = list(self.input_path.glob('*.csv'))
            if self.quick:
                files = files[:min(len(files), 5)]
        else:
            files = [self.input_path]

        engine = BacktestEngine(params=trial_conf)
        all_metrics = []
        for f in files:
            try:
                df = pd.read_csv(f, parse_dates=['date']).sort_values('date')
                if self.quick and len(df) > 200:
                    df = df.iloc[-200:]
                res = engine.run(df, symbol=f.stem)
                metrics = res['metrics']
                metrics['symbol'] = f.stem
                all_metrics.append(metrics)
            except Exception as e:
                # log and skip
                all_metrics.append({'symbol': f.stem if f is not None else None, 'annual_return': -9999, 'max_drawdown': 9999, 'sharpe': 0.0})
        # aggregate metrics: use mean annual_return, mean sharpe, mean max_dd
        if not all_metrics:
            agg = {'annual_return': -9999, 'max_drawdown': 9999, 'sharpe': 0.0}
        else:
            ann = sum(m.get('annual_return', 0.0) for m in all_metrics)/len(all_metrics)
            dd = sum(m.get('max_drawdown', 0.0) for m in all_metrics)/len(all_metrics)
            sr = sum(m.get('sharpe', 0.0) for m in all_metrics)/len(all_metrics)
            agg = {'annual_return': ann, 'max_drawdown': dd, 'sharpe': sr}
        return agg

    def run_grid(self):
        combos = expand_grid(self.param_space)
        if self.budget and self.budget < len(combos):
            combos = combos[:self.budget]
        best = None
        trials = []
        for i, combo in enumerate(combos):
            start = time.time()
            metrics = self.evaluate_params(combo)
            obj = objective_from_metrics(metrics)
            elapsed = time.time() - start
            record = {'id': i, 'params': combo, 'metrics': metrics, 'objective': obj, 'time': elapsed}
            trials.append(record)
            self._append_trial(record)
            if best is None or obj > best['objective']:
                best = record
                self._save_best(best)
        return best, trials

    def run_random(self):
        samples = sample_random(self.param_space, self.budget)
        best = None
        trials = []
        for i, s in enumerate(samples):
            start = time.time()
            metrics = self.evaluate_params(s)
            obj = objective_from_metrics(metrics)
            elapsed = time.time() - start
            record = {'id': i, 'params': s, 'metrics': metrics, 'objective': obj, 'time': elapsed}
            trials.append(record)
            self._append_trial(record)
            if best is None or obj > best['objective']:
                best = record
                self._save_best(best)
        return best, trials

    def run_bayes(self):
        if not HAS_OPTUNA:
            print('optuna not available, falling back to random search')
            return self.run_random()

        def objective(trial):
            trial_params = {}
            for k, spec in self.param_space.items():
                t = spec.get('type', 'choice')
                if t == 'choice':
                    trial_params[k] = trial.suggest_categorical(k, spec.get('values', []))
                elif t == 'int':
                    trial_params[k] = trial.suggest_int(k, int(spec['min']), int(spec['max']), step=int(spec.get('step', 1)))
                elif t == 'float':
                    trial_params[k] = trial.suggest_float(k, float(spec['min']), float(spec['max']), step=spec.get('step'))
                else:
                    trial_params[k] = trial.suggest_categorical(k, spec.get('values', []))
            metrics = self.evaluate_params(trial_params)
            obj = objective_from_metrics(metrics)
            # save trial
            record = {'id': trial.number, 'params': trial_params, 'metrics': metrics, 'objective': obj, 'time': 0}
            self._append_trial(record)
            return obj

        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=self.budget)
        # construct best record
        best_params = study.best_params
        best_metrics = self.evaluate_params(best_params)
        best_record = {'id': study.best_trial.number, 'params': best_params, 'metrics': best_metrics, 'objective': study.best_value, 'time': 0}
        self._save_best(best_record)
        return best_record, study.trials

    def _append_trial(self, record: Dict[str, Any]):
        # ensure trials.csv header exists
        hdr = ['id','params','objective','time','metrics']
        mode = 'a' if self.trials_file.exists() else 'w'
        with open(self.trials_file, mode, newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if mode == 'w':
                writer.writerow(hdr)
            writer.writerow([record['id'], json.dumps(record['params'], ensure_ascii=False), record['objective'], record['time'], json.dumps(record['metrics'], ensure_ascii=False)])

    def _save_best(self, record: Dict[str, Any]):
        with open(self.best_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump({'id': record['id'], 'params': record['params'], 'metrics': record['metrics'], 'objective': record['objective']}, f, allow_unicode=True)

    def run(self):
        if self.mode == 'grid':
            return self.run_grid()
        if self.mode == 'random':
            return self.run_random()
        if self.mode == 'bayes':
            return self.run_bayes()
        raise ValueError('unknown mode')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['grid','random','bayes'], default='grid')
    parser.add_argument('--param-space', required=True, help='参数空间 YAML 文件')
    parser.add_argument('--input', required=True, help='输入目录或单个CSV文件')
    parser.add_argument('--out', default='outputs/optimizer', help='输出目录')
    parser.add_argument('--budget', type=int, default=20, help='预算（试验次数）')
    parser.add_argument('--workers', type=int, default=1, help='并行 worker 数量（保留）')
    parser.add_argument('--quick', action='store_true', help='快速模式：缩短回测历史与样本数以加快优化')
    args = parser.parse_args()

    param_space = yaml.safe_load(open(args.param_space, 'r', encoding='utf-8'))
    params = yaml.safe_load(open(ROOT / 'config' / 'parameters.yaml', 'r', encoding='utf-8'))
    opt = Optimizer(params=params, param_space=param_space, input_path=Path(args.input), out_dir=Path(args.out), mode=args.mode, budget=args.budget, workers=args.workers, quick=args.quick)
    best, trials = opt.run()
    print('Best:', best)


if __name__ == '__main__':
    main()
