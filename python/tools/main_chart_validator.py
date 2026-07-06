"""
Python 验证脚本：用于在本地用 pandas 验证主图公式逻辑并生成信号 CSV/HTML 报告
文件：python/tools/main_chart_validator.py
要求：Python 3.10+, pandas
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
import yaml

# 读取参数
CONFIG_PATH = Path('config/parameters.yaml')


def load_params(path=CONFIG_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def ma(series: pd.Series, n: int):
    return series.rolling(n, min_periods=1).mean()


def ema(series: pd.Series, n: int):
    return series.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=1).mean()


def detect_breakout(df: pd.DataFrame, params):
    days = params['breakout']['BREAK_DAYS']
    mult = params['breakout']['BREAK_VOLUME_MULT']
    hh = df['high'].rolling(days, min_periods=1).max()
    ll = df['low'].rolling(days, min_periods=1).min()
    range_pct = (hh - ll) / ll * 100
    platform_thresh = 8
    is_platform = range_pct <= platform_thresh
    today_break = (df['close'] > hh.shift(1)) & (df['volume'] > df['volume'].shift(1) * mult)
    false_break = (df['close'] > hh.shift(1)) & (~(df['volume'] > df['volume'].shift(1) * mult))
    return today_break.fillna(False), false_break.fillna(False), is_platform.fillna(False)


def compute_scores(df: pd.DataFrame, params):
    p = params
    # moving averages
    df['ma_f'] = ma(df['close'], p['ma']['MA_FAST'])
    df['ma_m'] = ma(df['close'], p['ma']['MA_MID'])
    df['ma_s'] = ma(df['close'], p['ma']['MA_SLOW'])
    df['ma_l'] = ma(df['close'], p['ma']['MA_LONG'])
    df['atr'] = atr(df, p['atr']['ATR_PERIOD'])
    df['vol_ma_s'] = ma(df['volume'], p['volume']['VOL_MA_SHORT'])
    df['vol_ma_l'] = ma(df['volume'], p['volume']['VOL_MA_LONG'])
    df['vol_slope'] = df['volume'] - df['volume'].shift(1)

    # signals
    df['start'] = (df['ma_f'] > df['ma_f'].shift(1)) & (df['ma_f'].shift(1) <= df['ma_m'].shift(1)) & (df['volume'] > df['vol_ma_s'] * 0.8)
    df['small_vol_seq'] = (df['volume'] < df['vol_ma_s']).rolling(5, min_periods=1).sum() == 5
    df['accumulate'] = df['small_vol_seq'] & (df['close'] > df['ma_m'])
    df['shake'] = (df['low'] < df['low'].shift(1)) & (df['close'] > df['close'].shift(1)) & ((df['high'] - df['close']) / (df['high'] - df['low']) > 0.6) & (df['volume'] < df['vol_ma_s'])
    today_break, false_break, is_platform = detect_breakout(df, p)
    df['breakout'] = today_break
    df['false_break'] = false_break
    df['add'] = (df['close'] > df['ma_m']) & (df['volume'] > df['vol_ma_s'] * 1.2) & ((df['ma_f'] - df['ma_m']) / df['ma_m'] * 100 > 0.5)
    df['reduce'] = (df['close'] < df['ma_m']) & (df['volume'] > df['vol_ma_l'] * 1.5)
    df['stoploss'] = (df['ma_m'] > df['ma_f']) & (df['ma_f'].shift(1) <= df['ma_m'].shift(1))

    # approximate chip lock using turnover if available
    if 'turnover' in df.columns:
        df['turnover_rate'] = df['turnover'] / df['close'] * 100
        df['chip_lock_approx'] = df['turnover_rate'].rolling(p['chip']['CHIP_DAYS'], min_periods=1).apply(lambda x: (x>0.5).sum()) / p['chip']['CHIP_DAYS'] * 100
    else:
        df['turnover_rate'] = np.nan
        df['chip_lock_approx'] = 0

    # scoring (simple mapping to match THS formula banding)
    def vol_score(row):
        if row['volume'] > row['vol_ma_l']:
            return 15
        if row['volume'] > row['vol_ma_s']:
            return 10
        return 5

    def trend_score(row):
        angle = (row['ma_f'] - row['ma_m']) / row['ma_m'] * 100 if row['ma_m'] != 0 else 0
        if angle > 0.8:
            return 15
        if angle > 0.2:
            return 10
        return 5

    def chip_score(row):
        if row.get('chip_lock_approx', 0) > 50:
            return 12
        if row.get('chip_lock_approx', 0) > 30:
            return 8
        return 4

    def money_score(row):
        if 'amount' in df.columns:
            return 12 if row['amount'] > (row.get('amount', np.nan) if False else row['amount']) else 6
        return 6

    def breakout_score(row):
        if row['breakout']:
            return 10
        if row['false_break']:
            return 2
        return 5

    def risk_score(row):
        return 0 if row['stoploss'] else 15

    df['volume_score'] = df.apply(vol_score, axis=1)
    df['trend_score'] = df.apply(trend_score, axis=1)
    df['chip_score'] = df.apply(chip_score, axis=1)
    df['money_score'] = df.apply(money_score, axis=1)
    df['breakout_score'] = df.apply(breakout_score, axis=1)
    df['risk_score'] = df.apply(risk_score, axis=1)

    df['total_score'] = df['volume_score'] + df['trend_score'] + df['chip_score'] + df['money_score'] + df['breakout_score'] + df['risk_score']

    return df


def load_sample_csv(path: Path):
    df = pd.read_csv(path, parse_dates=['date'])
    df = df.sort_values('date')
    df = df.rename(columns={
        'Date': 'date', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume', 'Amount': 'amount'
    })
    # ensure lowercase columns
    df.columns = [c.lower() for c in df.columns]
    return df


def generate_report(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / 'signals.csv'
    df.to_csv(csv_out, index=False)
    # 简单 HTML 报告
    html = df[['date','close','total_score','start','accumulate','breakout','false_break','add','reduce','stoploss']].to_html(index=False, na_rep='')
    (out_dir / 'report.html').write_text(f"<h1>THS Quant V5.0 主图验证报告</h1>{html}", encoding='utf-8')
    print(f"报告已生成: {out_dir}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='验证主图公式逻辑并生成信号')
    parser.add_argument('--csv', type=str, required=True, help='同花顺导出的日线CSV路径')
    parser.add_argument('--out', type=str, default='outputs/main_chart', help='输出目录')
    args = parser.parse_args()

    params = load_params()
    df = load_sample_csv(Path(args.csv))
    df_processed = compute_scores(df, params)
    generate_report(df_processed, Path(args.out))
