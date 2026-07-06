# 预警模块文档

本文件说明预警公式与告警监控脚本的使用方法、告警类型与冷却策略。

1. 同花顺内预警公式
   - 将 ths/alert_formula.ths 的内容复制到同花顺条件公式编辑器或自定义公式，保存后在 K 线图内启用。公式会在图上绘制告警图标与文本，返回 1 表示触发告警。
   - 公式内部通过简单的近似逻辑判断突破/风险，高级用户可在至尊版启用 WINNER/COST/FINANCE 获取更精确的数据（后续卷将提供真实筹码版本）。

2. 离线/定时监控脚本
   - 使用 python/tools/alert_monitor.py 扫描本地数据目录（推荐每日收盘后运行一次）：
     python python/tools/alert_monitor.py --input data/stocks --out outputs/alerts --hooks hooks.yaml
   - 输出：outputs/alerts/alerts.csv（列: symbol,date,close,total_score,alerts）
   - 钩子（hooks.yaml）示例：
     email:
       smtp_server: smtp.example.com
       smtp_port: 587
       username: you@example.com
       password: secret
       to: [you@example.com]
     slack:
       webhook: https://hooks.slack.com/...

3. 冷却策略
   - 同花顺公式内通过近似 SUM(...) 判断过去 N 日是否已触发以避免短期重复告警；离线脚本可扩展为更严格的去重与冷却实现（例如基于持久化数据库记录每次告警时间）。

4. 扩展方向
   - 接入实时行情接口（分钟/秒级）用于更及时告警
   - 支持多种告警渠道（邮件、企业微信、钉钉、Slack、Webhook）
   - 将告警历史写入数据库并提供 Web Dashboard
