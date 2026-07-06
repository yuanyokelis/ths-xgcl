"""
回测引擎：支持基于评分的简单策略回测

主要功能：
- 根据评分引擎生成入场/出场信号
- 支持固定仓位百分比开仓、固定手续费与滑点
- 输出交易明细、权益曲线
- 计算主要绩效指标（收益、年化、最大回撤、夏普、胜率、盈亏比）

实现说明：
- 本回测为事件驱动日线回测，使用次日开盘价执行交易（若不可用则使用当日收盘价）
- 所有参数从 config/parameters.yaml 加载

作者：首席量化架构师
"""
from __future__ import annotations
from pathlib import Path
import sys
import os
import pandas as pd
import numpy as np
import yaml
from typing import Dict, Any, List

# 为兼容仓库中不同模块导入方式，确保根目录和 python 目录在 sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PY_DIR = ROOT / 'python'
if str(PY_DIR) not in sys.path:
    sys.path.insert(0, str(PY_DIR))

# 引入评分引擎
try:
    from engines.volume_engine import VolumeEngine
    from engines.trend_engine import TrendEngine
    from engines.chip_engine import ChipEngine
    from engines.money_engine import MoneyEngine
    from engines.breakout_engine import BreakoutEngine
    from engines.risk_engine import RiskEngine
    from engines.score_engine import ScoreEngine
except Exception:
    # 备用导入路径
    from python.engines.volume_engine import VolumeEngine
    from python.engines.trend_engine import TrendEngine
    from python.engines.chip_engine import ChipEngine
    from python.engines.money_engine import MoneyEngine
    from python.engines.breakout_engine import BreakoutEngine
    from python.engines.risk_engine import RiskEngine
    from python.engines.score_engine import ScoreEngine


class BacktestEngine:
    """回测引擎类

    参数：
      params: 参数字典（从 config/parameters.yaml 加载）

    方法：
      run(df, symbol=None) -> returns dict with trades, equity_series, metrics
    """

    def __init__(self, params: Dict[str, Any]):
        self.params = params
        self.capital = float(params.get('backtest', {}).get('INITIAL_CAPITAL', 100000.0))
        self.position_pct = float(params.get('backtest', {}).get('POSITION_SIZE_PCT', 0.1))
        self.commission = float(params.get('backtest', {}).get('COMMISSION_PER_TRADE', 1.0))
        self.slippage = float(params.get('backtest', {}).get('SLIPPAGE_PCT', 0.001))
        self.min_hold = int(params.get('backtest', {}).get('MIN_HOLD_DAYS', 1))

        # 初始化评分引擎对象
        self.vol_engine = VolumeEngine(params=params)
        self.trend_engine = TrendEngine(params=params)
        self.chip_engine = ChipEngine(params=params)
        self.money_engine = MoneyEngine(params=params)
        self.brk_engine = BreakoutEngine(params=params)
        self.risk_engine = RiskEngine(params=params)
        self.score_engine = ScoreEngine(params=params)

    def prepare_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """为回测数据计算所有子评分和总评分，并返回带有评分列的 DataFrame"""
        data = df.copy().reset_index(drop=True)
        res_vol = self.vol_engine.compute(data)['series']
        res_tre = self.trend_engine.compute(data)['series']
        res_chip = self.chip_engine.compute(data)['series']
        res_money = self.money_engine.compute(data)['series']
        res_brk = self.brk_engine.compute(data)['series']
        res_risk = self.risk_engine.compute(data)['series']

        data['volume_score'] = res_vol.values
        data['trend_score'] = res_tre.values
        data['chip_score'] = res_chip.values
        data['money_score'] = res_money.values
        data['break_score'] = res_brk.values
        data['risk_score'] = res_risk.values

        # 计算总评分（百分制）
        data['total_score'] = self.score_engine.compute_from_series(data)
        return data

    def run(self, df: pd.DataFrame, symbol: str | None = None) -> Dict[str, Any]:
        """执行回测

        输入数据要求：包含 date/open/high/low/close/volume，且按日期升序排列
        执行逻辑：当日信号 -> 次日开盘（或当日收盘若无开盘价）执行
        """
        data = df.copy().reset_index(drop=True)
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
        else:
            data['date'] = pd.RangeIndex(len(data))

        scored = self.prepare_scores(data)

        initial_capital = self.capital
        cash = initial_capital
        position = 0.0  # 手数/份数（以股数计）
        position_cost = 0.0
        equity_series = []
        trades = []
        in_position = False
        entry_index = None

        threshold = float(self.params.get('score', {}).get('DEFAULT_THRESHOLD', 80))

        for i in range(len(scored)):
            row = scored.iloc[i]
            date = row['date']
            close = float(row.get('close', np.nan))
            openp = float(row.get('open', np.nan)) if not pd.isna(row.get('open', np.nan)) else close
            # 当日（i）信号为基于当日评分；实际交易使用下一日开盘价执行
            score = float(row['total_score'])

            # 判断买入信号：当日评分 >= threshold 且当前无持仓
            if (not in_position) and score >= threshold:
                # 计算买入金额
                buy_amount = initial_capital * self.position_pct
                # 以次日开盘价买入。若下日不存在（i==len-1），以当日收盘买入
                exec_price = None
                if i+1 < len(scored):
                    next_open = scored.iloc[i+1].get('open', np.nan)
                    exec_price = float(next_open) if not pd.isna(next_open) else close
                    exec_index = i+1
                else:
                    exec_price = close
                    exec_index = i
                # 应用滑点
                exec_price = exec_price * (1 + self.slippage)
                # 购买股数（整股）
                qty = buy_amount / exec_price
                # 扣除手续费
                cash -= qty * exec_price
                cash -= self.commission
                position = qty
                position_cost = exec_price
                in_position = True
                entry_index = exec_index
                trades.append({'symbol': symbol, 'entry_date': scored.iloc[exec_index]['date'], 'entry_price': exec_price, 'qty': qty, 'exit_date': None, 'exit_price': None, 'pnl': None})

            # 判断卖出信号：若持仓，若评分跌破阈值或风险事件触发或持有时间超过最小持仓天数允许卖出
            if in_position:
                # Determine exit conditions based on latest row (use today's row for exit decision)
                exit_cond = False
                # 若评分低于阈值的90%则退出
                if score < threshold * 0.9:
                    exit_cond = True
                # 若风险警示（risk_score 低）比较：risk_score 的尺度为0~15，若小于等于3视为高风险
                if float(row.get('risk_score', 15)) <= 3:
                    exit_cond = True
                # 最小持仓天数限制
                if entry_index is not None and (i - entry_index) < self.min_hold:
                    exit_cond = False

                if exit_cond:
                    # 以次日开盘价卖出（若存在），否则以当日收盘价
                    if i+1 < len(scored):
                        next_open = scored.iloc[i+1].get('open', np.nan)
                        exec_price = float(next_open) if not pd.isna(next_open) else close
                        exec_index = i+1
                    else:
                        exec_price = close
                        exec_index = i
                    # 滑点（卖出价格下移）
                    exec_price = exec_price * (1 - self.slippage)
                    qty = position
                    cash += qty * exec_price
                    cash -= self.commission
                    pnl = (exec_price - position_cost) * qty
                    # 更新最近一笔交易的出场信息
                    trades[-1].update({'exit_date': scored.iloc[exec_index]['date'], 'exit_price': exec_price, 'pnl': pnl})
                    position = 0.0
                    position_cost = 0.0
                    in_position = False
                    entry_index = None

            # 记录当日权益
            market_value = position * close
            total_equity = cash + market_value
            equity_series.append({'date': date, 'equity': total_equity})

        equity_df = pd.DataFrame(equity_series)
        metrics = self.calculate_metrics(equity_df)

        result = {
            'symbol': symbol,
            'trades': pd.DataFrame(trades),
            'equity': equity_df,
            'metrics': metrics,
            'scored': scored,
        }
        return result

    @staticmethod
    def calculate_metrics(equity_df: pd.DataFrame) -> Dict[str, Any]:
        """计算回测绩效指标
        输入：equity_df 包含 date 与 equity 列
        输出：字典包含收益、年化、最大回撤、夏普、胜率、盈亏比等
        """
        df = equity_df.copy()
        df = df.dropna().reset_index(drop=True)
        if df.empty:
            return {}
        df['equity'] = df['equity'].astype(float)
        df['returns'] = df['equity'].pct_change().fillna(0)
        total_return = df['equity'].iloc[-1] / df['equity'].iloc[0] - 1
        days = (pd.to_datetime(df['date'].iloc[-1]) - pd.to_datetime(df['date'].iloc[0])).days
        years = days / 365.25 if days>0 else 1/365.25
        annual_return = (1 + total_return) ** (1 / years) - 1 if years>0 else 0.0
        # 年化波动
        ann_vol = df['returns'].std() * np.sqrt(252) if df['returns'].std()>0 else 0.0
        sharpe = (df['returns'].mean() * 252) / ann_vol if ann_vol>0 else 0.0

        # 最大回撤
        roll_max = df['equity'].cummax()
        drawdown = (df['equity'] - roll_max) / roll_max
        max_dd = drawdown.min()

        metrics = {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'annual_volatility': float(ann_vol),
            'sharpe': float(sharpe),
            'max_drawdown': float(max_dd),
        }
        return metrics


if __name__ == '__main__':
    # 简单本地测试示例
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='输入日线CSV路径')
    parser.add_argument('--out', default='outputs/backtest', help='输出目录')
    args = parser.parse_args()
    params = yaml.safe_load(open(ROOT / 'config' / 'parameters.yaml', 'r', encoding='utf-8'))
    df = pd.read_csv(args.csv, parse_dates=['date'])
    engine = BacktestEngine(params=params)
    res = engine.run(df)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    res['trades'].to_csv(out_dir / 'trades.csv', index=False)
    res['equity'].to_csv(out_dir / 'equity.csv', index=False)
    # 输出 metrics
    with open(out_dir / 'metrics.yaml', 'w', encoding='utf-8') as f:
        yaml.safe_dump(res['metrics'], f, allow_unicode=True)
    print('回测完成，结果已写入', out_dir)
