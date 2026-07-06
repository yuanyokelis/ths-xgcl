"""
日志系统单元测试：tests/test_logger.py
验证日志模块的基本功能：写入事件、读取最近事件、导出 Excel
"""
from pathlib import Path
import shutil
from python.tools.logger import init_app_logger, log_event, list_recent_events, export_events_to_excel, EVENTS_CSV


def test_logger_basic(tmp_path):
    # 使用临时目录替换 logs 目录
    import os
    orig_logs = Path('logs')
    backup = None
    if orig_logs.exists():
        backup = tmp_path / 'logs_backup'
        shutil.move(str(orig_logs), str(backup))
    try:
        os.makedirs('logs', exist_ok=True)
        init_app_logger()
        log_event('TEST', {'a':1}, txt='unit test')
        events = list_recent_events(10)
        assert len(events) >= 1
        # 导出到 Excel
        p = export_events_to_excel(out_path='logs/test_events.xlsx')
        assert Path(p).exists()
    finally:
        # cleanup: 先移除并关闭 logger handlers，避免 Windows 文件锁导致 rmtree 失败
        import logging
        logger = logging.getLogger('ths_xgcl')
        for h in list(logger.handlers):
            try:
                logger.removeHandler(h)
                h.close()
            except Exception:
                pass
        # 然后删除目录并恢复备份
        shutil.rmtree('logs')
        if backup:
            shutil.move(str(backup), 'logs')
