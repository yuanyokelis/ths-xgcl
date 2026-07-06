"""
告警监控脚本：离线或定时扫描多只股票数据并生成告警日志/CSV
文件：python/tools/alert_monitor.py

功能：
- 支持目录批量扫描（data/stocks/*.csv）或单文件扫描
- 使用已有评分引擎计算子评分与总评分
- 识别告警事件（高分、突破确认、假突破、风险事件）并输出 alerts.csv
- 支持可选的告警传输钩子：send_email, send_slack（占位实现，用户自行配置）
- 日志记录到 logs/alerts.log

注意：该脚本不依赖实时 L2 数据，基于日线推断告警；若需要分钟级实时告警，请在后续卷中扩展对接行情接口。
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import yaml
import logging
from datetime import datetime

from python.engines.volume_engine import VolumeEngine
from python.engines.trend_engine import TrendEngine
from python.engines.chip_engine import ChipEngine
from python.engines.money_engine import MoneyEngine
from python.engines.breakout_engine import BreakoutEngine
from python.engines.risk_engine import RiskEngine
from python.engines.score_engine import ScoreEngine

# 日志配置
LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_DIR / 'alerts.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

CONFIG_PATH = Path('config/parameters.yaml')


def load_params(path=CONFIG_PATH):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def detect_alerts_for_df(df: pd.DataFrame, params: dict):
    # 计算子评分
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
    total = scorer.compute_from_series(df2)
    df2['total_score'] = total

    # 计算告警条件（与 THS 公式保持一致）
    latest = df2.iloc[-1]
    max_total = 25+20+15+15+10+15
    pct = latest['total_score']
    score_threshold = params.get('score', {}).get('DEFAULT_THRESHOLD', 80)
    # 突破检测：过去 BREAK_DAYS 最大高点
    days = params.get('breakout', {}).get('BREAK_DAYS', 30)
    hh = df['high'].rolling(days, min_periods=1).max().iloc[-1]
    today_vol = df['volume'].iloc[-1]
    prev_vol = df['volume'].shift(1).iloc[-1]
    breakout_confirm = (latest['close'] > hh) and (today_vol > prev_vol * params.get('breakout', {}).get('BREAK_VOLUME_MULT', 2.0))
    false_break = (latest['close'] > hh) and not (today_vol > prev_vol * params.get('breakout', {}).get('BREAK_VOLUME_MULT', 2.0))
    upper_shadow = (latest['high'] - max(latest['close'], latest.get('open', latest['close']))) / max((latest['high'] - latest['low']), 1e-9)
    high_vol_top = (today_vol > df['volume'].rolling(20, min_periods=1).mean().iloc[-1] * 2) and (latest['close'] / df['close'].shift(20).iloc[-1] > 1.3 if len(df)>=21 else False)
    risk_alert = upper_shadow > 0.6 or high_vol_top
    high_score_alert = pct >= score_threshold

    alerts = []
    if high_score_alert:
        alerts.append('HIGH_SCORE')
    if breakout_confirm:
        alerts.append('BREAKOUT_CONFIRM')
    if false_break:
        alerts.append('FALSE_BREAK')
    if risk_alert:
        alerts.append('RISK')

    return {
        'symbol': latest.name if 'symbol' in df.columns else None,
        'date': latest['date'] if 'date' in df.columns else None,
        'close': latest['close'],
        'total_score': float(latest['total_score']),
        'alerts': alerts,
        'detail': {
            'volume_score': float(latest.get('volume_score', 0)),
            'trend_score': float(latest.get('trend_score', 0)),
            'chip_score': float(latest.get('chip_score', 0)),
            'money_score': float(latest.get('money_score', 0)),
            'break_score': float(latest.get('break_score', 0)),
            'risk_score': float(latest.get('risk_score', 0)),
        }
    }


def send_email(subject: str, body: str, config: dict):
    # 占位实现：用户可在此处实现 SMTP 发送（或使用第三方服务）
    logging.info(f"[send_email] subject={subject}")


def send_slack(message: str, config: dict):
    # 占位实现：用户可在此处实现 Slack/钉钉 webhook 发送
    logging.info(f"[send_slack] message={message}")


def monitor_path(input_path: Path, out_dir: Path, params: dict, alert_hooks: dict | None = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    alerts_list = []
    for f in input_path.glob('*.csv'):
        try:
            df = pd.read_csv(f, parse_dates=['date'])
            df = df.sort_values('date').reset_index(drop=True)
            res = detect_alerts_for_df(df, params)
            res['symbol'] = f.stem
            if res['alerts']:
                alerts_list.append(res)
                msg = f"{res['symbol']} {res['date']} alerts: {','.join(res['alerts'])} score={res['total_score']:.1f}"
                logging.info(msg)
                if alert_hooks:
                    if 'email' in alert_hooks:
                        send_email(subject=f"THS Alert {res['symbol']}", body=msg, config=alert_hooks.get('email'))
                    if 'slack' in alert_hooks:
                        send_slack(message=msg, config=alert_hooks.get('slack'))
        except Exception as e:
            logging.exception(f"Error processing {f}: {e}")

    df_alerts = pd.DataFrame([{
        'symbol': a['symbol'], 'date': a['date'], 'close': a['close'], 'total_score': a['total_score'], 'alerts': ';'.join(a['alerts'])
    } for a in alerts_list])
    csv_out = out_dir / 'alerts.csv'
    df_alerts.to_csv(csv_out, index=False, encoding='utf-8-sig')
    return df_alerts


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='输入目录或单文件')
    parser.add_argument('--out', default='outputs/alerts', help='输出目录')
    parser.add_argument('--hooks', default=None, help='告警钩子配置 YAML 文件（包含 email/slack 配置）')
    args = parser.parse_args()
    params = load_params()
    hooks = None
    if args.hooks:
        hooks = yaml.safe_load(open(args.hooks, 'r', encoding='utf-8'))
    inp = Path(args.input)
    outp = Path(args.out)
    if inp.is_dir():
        res = monitor_path(inp, outp, params, alert_hooks=hooks)
        print(f"告警扫描完成，结果写入 {outp / 'alerts.csv'}")
    else:
        print('目前仅支持目录批量扫描，请传入目录')
