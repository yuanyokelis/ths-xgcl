"""
副图验证脚本：使用各评分引擎计算子评分并输出副图所需的 CSV
文件：python/tools/sub_chart_validator.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import yaml
import numpy as np
from core.engine import ParameterEngine
from engines.volume_engine import VolumeEngine
from engines.trend_engine import TrendEngine
from engines.chip_engine import ChipEngine
from engines.money_engine import MoneyEngine
from engines.breakout_engine import BreakoutEngine
from engines.risk_engine import RiskEngine
from engines.score_engine import ScoreEngine

CONFIG_PATH = Path('config/parameters.yaml')


def load_params(path=CONFIG_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_csv(path: Path):
    df = pd.read_csv(path, parse_dates=['date'])
    df = df.sort_values('date')
    df.columns = [c.lower() for c in df.columns]
    # ensure required columns
    for col in ['open','high','low','close','volume']:
        if col not in df.columns:
            df[col] = np.nan
    return df


def run_all(csv_path: Path, out_dir: Path):
    params = load_params()
    df = load_csv(csv_path)

    # 初始化引擎
    vol = VolumeEngine(params=params)
    tre = TrendEngine(params=params)
    chip = ChipEngine(params=params)
    money = MoneyEngine(params=params)
    brk = BreakoutEngine(params=params)
    risk = RiskEngine(params=params)
    scorer = ScoreEngine(params=params)

    # 计算
    res_vol = vol.compute(df)
    res_tre = tre.compute(df)
    res_chip = chip.compute(df)
    res_money = money.compute(df)
    res_brk = brk.compute(df)
    res_risk = risk.compute(df)

    # 将结果合并到 DataFrame
    out = df.copy()
    out['volume_score'] = res_vol['series']
    out['trend_score'] = res_tre['series']
    out['chip_score'] = res_chip['series']
    out['money_score'] = res_money['series']
    out['break_score'] = res_brk['series']
    out['risk_score'] = res_risk['series']

    out['total_score'] = scorer.compute_from_series(out)

    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_dir / 'sub_chart_scores.csv', index=False)
    (out_dir / 'sub_chart_report.html').write_text(out[['date','close','volume_score','trend_score','chip_score','money_score','break_score','risk_score','total_score']].to_html(index=False), encoding='utf-8')
    print(f"副图评分已生成: {out_dir / 'sub_chart_scores.csv'}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--out', default='outputs/sub_chart')
    args = parser.parse_args()
    run_all(Path(args.csv), Path(args.out))
