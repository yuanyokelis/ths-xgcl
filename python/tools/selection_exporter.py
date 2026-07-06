"""
选股导出工具：批量在本地对多只股票的日线数据进行评分并导出选股清单（CSV 和 Excel）
文件：python/tools/selection_exporter.py

依赖：pandas, openpyxl, PyYAML
Python 3.10+

说明：输入一个目录 data/stocks/{symbol}.csv（或单文件），对每只股票计算最新一日 total_score，并根据参数阈值导出选股清单
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import yaml
import argparse
import numpy as np
from python.engines.volume_engine import VolumeEngine
from python.engines.trend_engine import TrendEngine
from python.engines.chip_engine import ChipEngine
from python.engines.money_engine import MoneyEngine
from python.engines.breakout_engine import BreakoutEngine
from python.engines.risk_engine import RiskEngine
from python.engines.score_engine import ScoreEngine

CONFIG_PATH = Path('config/parameters.yaml')


def load_params(path=CONFIG_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_stock_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=['date'])
    df = df.sort_values('date')
    df.columns = [c.lower() for c in df.columns]
    return df


def score_single(df: pd.DataFrame, params: dict) -> float:
    # 计算各项子评分并以 ScoreEngine 汇总，返回最新一日的百分制得分
    vol = VolumeEngine(params=params).compute(df)['series']
    tre = TrendEngine(params=params).compute(df)['series']
    chip = ChipEngine(params=params).compute(df)['series']
    money = MoneyEngine(params=params).compute(df)['series']
    brk = BreakoutEngine(params=params).compute(df)['series']
    risk = RiskEngine(params=params).compute(df)['series']
    df2 = df.copy()
    df2['volume_score'] = vol
    df2['trend_score'] = tre
    df2['chip_score'] = chip
    df2['money_score'] = money
    df2['break_score'] = brk
    df2['risk_score'] = risk
    scorer = ScoreEngine(params=params)
    total_series = scorer.compute_from_series(df2)
    # 返回最后一日分数（百分制）
    if len(total_series)==0:
        return float('nan')
    return float(total_series.iloc[-1])


def run_directory(input_path: Path, out_dir: Path, params: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for f in input_path.glob('*.csv'):
        symbol = f.stem
        try:
            df = load_stock_csv(f)
            score = score_single(df, params)
            latest_close = df['close'].iloc[-1] if 'close' in df.columns and len(df)>0 else None
            results.append({'symbol': symbol, 'score': score, 'close': latest_close})
        except Exception as e:
            results.append({'symbol': symbol, 'score': float('nan'), 'close': None, 'error': str(e)})
    df_out = pd.DataFrame(results)
    # 按分数降序
    df_out = df_out.sort_values('score', ascending=False)
    csv_out = out_dir / 'selection_results.csv'
    xlsx_out = out_dir / 'selection_results.xlsx'
    df_out.to_csv(csv_out, index=False, encoding='utf-8-sig')
    df_out.to_excel(xlsx_out, index=False)
    print(f"选股结果已导出: {csv_out} 和 {xlsx_out}")
    return df_out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='输入目录或单个CSV文件，包含多只股票的日线CSV')
    parser.add_argument('--out', default='outputs/selection', help='输出目录')
    args = parser.parse_args()
    params = load_params()
    inp = Path(args.input)
    outp = Path(args.out)
    if inp.is_dir():
        run_directory(inp, outp, params)
    elif inp.is_file():
        # 单文件：按 symbol 列区分或仅处理单只
        df = load_stock_csv(inp)
        # 如果输入为多只合并文件，要求有 symbol 列
        if 'symbol' in df.columns:
            symbols = df['symbol'].unique()
            tmpdir = outp / 'tmp'
            tmpdir.mkdir(parents=True, exist_ok=True)
            for s in symbols:
                sub = df[df['symbol']==s]
                sub.to_csv(tmpdir / f"{s}.csv", index=False)
            run_directory(tmpdir, outp, params)
        else:
            # 单只股票
            symbol = inp.stem
            score = score_single(df, params)
            outp.mkdir(parents=True, exist_ok=True)
            pd.DataFrame([{'symbol':symbol,'score':score,'close':df['close'].iloc[-1] if 'close' in df.columns else None}]).to_csv(outp / 'selection_results.csv', index=False, encoding='utf-8-sig')
            print(f"单只选股结果已导出: {outp / 'selection_results.csv'}")
