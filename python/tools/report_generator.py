"""
回测报告生成器：将回测结果（trades/equity）整理成 HTML 报告并保存为 outputs/backtest/report.html
文件：python/tools/report_generator.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64


def equity_chart_base64(equity_df: pd.DataFrame):
    plt.figure(figsize=(10,4))
    plt.plot(equity_df['date'], equity_df['equity'])
    plt.title('Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Equity')
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_b64


def generate_report(backtest_dir: Path, out_html: Path):
    # 查找每个子目录下的 equity.csv 与 trades.csv
    rows = []
    for sym_dir in sorted(backtest_dir.iterdir()):
        if not sym_dir.is_dir():
            continue
        equity_file = sym_dir / 'equity.csv'
        trades_file = sym_dir / 'trades.csv'
        if equity_file.exists():
            equity = pd.read_csv(equity_file, parse_dates=['date'])
            metrics = {}
            metrics['symbol'] = sym_dir.name
            metrics['start_equity'] = equity['equity'].iloc[0]
            metrics['end_equity'] = equity['equity'].iloc[-1]
            metrics['total_return'] = equity['equity'].iloc[-1]/equity['equity'].iloc[0]-1
            rows.append(metrics)
    df = pd.DataFrame(rows)
    # 简单HTML
    html = '<html><head><meta charset="utf-8"><title>回测报告</title></head><body>'
    html += '<h1>回测汇总</h1>'
    html += df.to_html(index=False)
    html += '</body></html>'
    out_html.write_text(html, encoding='utf-8')
    print('生成回测报告:', out_html)
