# 历史回测文档

本文件说明如何使用回测引擎执行历史回测、生成报告以及常见参数说明。

1. 运行单只回测
   - 准备同花顺导出的日线 CSV（含 Date/Open/High/Low/Close/Volume/Amount），放置为 data/sample.csv
   - 执行：
     python python/backtest/backtest_engine.py --csv data/sample.csv --out outputs/backtest
   - 输出：trades.csv、equity.csv、metrics.yaml

2. 批量回测
   - 将多只股票的 CSV 放到 data/stocks/，文件名为 {symbol}.csv
   - 执行：
     python python/tools/backtest_runner.py --input data/stocks --out outputs/backtest
   - 输出：每只股票子目录（包含 trades.csv、equity.csv）和 backtest_summary.csv

3. 参数说明（位于 config/parameters.yaml）
   - backtest.INITIAL_CAPITAL: 初始资金
   - backtest.POSITION_SIZE_PCT: 每笔开仓占初始资金比例
   - backtest.COMMISSION_PER_TRADE: 每笔交易手续费
   - backtest.SLIPPAGE_PCT: 交易滑点（百分比）
   - backtest.MIN_HOLD_DAYS: 最短持仓天数

4. 输出解释
   - trades.csv：包含 entry_date, entry_price, qty, exit_date, exit_price, pnl
   - equity.csv：每日权益曲线
   - backtest_summary.csv：批量回测汇总，包含 annual_return 等指标

5. 扩展
   - 支持更复杂的资金管理、逐日建仓/加仓、手续费与滑点的更细粒度模拟
   - 支持分钟级回测与实时回测框架（后续卷扩展）
