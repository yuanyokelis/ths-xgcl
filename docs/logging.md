# 日志系统文档

本文件说明如何使用内置的日志系统（python/tools/logger.py）以及如何在各个工具中接入。

1. 简单使用
   from python.tools.logger import log_event
   log_event('SCORE', {'symbol':'000001','score':85.3}, txt='每日评分快照')

2. 支持的功能
   - 文本日志：logs/app.log（按天轮替，保留30天）
   - 结构化事件：logs/events.csv（记录 timestamp, event_type, level, text, data_json）
   - 导出为 Excel：python.tools.logger.export_events_to_excel()
   - 查询最近事件：python.tools.logger.list_recent_events(limit)
   - 日志清理：python.tools.logger.cleanup_logs(keep_days)

3. 接入建议
   - 在评分引擎（score_engine）、回测（backtest_engine）、优化器（optimizer）、校准器（calibrator）和告警监控（alert_monitor）等关键路径调用 log_event，记录参数版本与结果。
   - 示例：在回测完成后调用：
       log_event('BACKTEST', {'symbol': symbol, 'metrics': metrics}, txt='回测完成')

4. 扩展方向
   - 如果需要更强的查询能力，可将 events.csv 写入 SQLite 或 Elasticsearch；可在 logger.py 中增加 write_to_sqlite() 或 elasticsearch 推送函数。
