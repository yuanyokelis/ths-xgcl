"""
通用日志系统模块
文件：python/tools/logger.py
说明：提供统一的日志接口，用于记录事件（评分、信号、选股、回测、优化、校准等），支持：
- 文本日志（按级别写入 logs/app.log）
- 结构化事件 CSV（logs/events.csv）
- 导出为 Excel（logs/events.xlsx）
- 简单的历史清理（按天数保留）

设计原则：
- 轻量、易集成：工具/引擎可在任意位置调用 log_event() 来记录结构化事件
- 默认不依赖数据库，便于在本地或 CI 环境下运行；可扩展为写入 SQLite 或外部系统（Webhook/ELK）

作者：首席量化架构师
"""
from __future__ import annotations
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import csv
import threading
import datetime
from typing import Dict, Any, Optional, List
import pandas as pd

LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 默认事件 CSV 文件
EVENTS_CSV = LOG_DIR / 'events.csv'
# 默认日志文本文件
APP_LOG = LOG_DIR / 'app.log'

_lock = threading.Lock()

# 初始化基础文本 logger
def init_app_logger(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger('ths_xgcl')
    logger.setLevel(level)
    if not logger.handlers:
        handler = TimedRotatingFileHandler(APP_LOG, when='midnight', backupCount=30, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # 也输出到控制台
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
    return logger

# 记录结构化事件到 CSV
def log_event(event_type: str, data: Dict[str, Any], level: str = 'INFO', txt: Optional[str] = None) -> None:
    """写入结构化事件。

    event_type: 事件类别，例如 'SCORE', 'SIGNAL', 'BACKTEST', 'ALERT', 'OPTIMIZER'
    data: 任意键值对（会被序列化为JSON字符串或扁平列）
    level: 日志级别文本
    txt: 可选的短文本描述
    """
    logger = init_app_logger()
    ts = datetime.datetime.utcnow().isoformat()
    # 文本日志
    msg = f"[{event_type}] {txt if txt else ''} {data}"
    if level.upper() == 'DEBUG':
        logger.debug(msg)
    elif level.upper() == 'WARN' or level.upper() == 'WARNING':
        logger.warning(msg)
    elif level.upper() == 'ERROR':
        logger.error(msg)
    else:
        logger.info(msg)

    # 结构化事件写入 CSV（线程安全）
    with _lock:
        is_new = not EVENTS_CSV.exists()
        with open(EVENTS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if is_new:
                # header
                writer.writerow(['timestamp', 'event_type', 'level', 'text', 'data_json'])
            writer.writerow([ts, event_type, level.upper(), txt if txt else '', json_safe(data)])


def json_safe(obj: Any) -> str:
    try:
        import json
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def export_events_to_excel(out_path: Optional[str] = None) -> Path:
    """将 events.csv 导出为 Excel 文件，返回生成的路径"""
    out_path = out_path or (LOG_DIR / 'events.xlsx')
    out_path = Path(out_path)
    if not EVENTS_CSV.exists():
        raise FileNotFoundError(f"事件文件不存在: {EVENTS_CSV}")
    df = pd.read_csv(EVENTS_CSV)
    df.to_excel(out_path, index=False)
    return out_path


def list_recent_events(limit: int = 100) -> List[Dict[str, Any]]:
    """读取最近的若干事件（最新在后）"""
    if not EVENTS_CSV.exists():
        return []
    df = pd.read_csv(EVENTS_CSV)
    df = df.tail(limit)
    return df.fillna('').to_dict(orient='records')


def cleanup_logs(keep_days: int = 180) -> None:
    """清理超过保留期的日志文件（按文件修改时间）"""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=keep_days)
    for p in LOG_DIR.iterdir():
        try:
            mtime = datetime.datetime.utcfromtimestamp(p.stat().st_mtime)
            if mtime < cutoff:
                p.unlink()
        except Exception:
            continue


# 简单示例和自测入口
if __name__ == '__main__':
    logger = init_app_logger()
    logger.info('Logger initialized')
    # 示例事件
    log_event('TEST', {'value': 123, 'ok': True}, txt='示例事件')
    print('最近事件：', list_recent_events(5))
    # 导出 Excel
    try:
        p = export_events_to_excel()
        print('导出到', p)
    except FileNotFoundError:
        print('暂无事件文件可导出')
