# 副图文档

本文件说明副图的设计、颜色与如何在同花顺中加载副图公式，以及如何使用 Python 工具生成副图所需 CSV 与 HTML 报告。

1. 加载副图公式
   - 将 ths/sub_chart_formula.ths 的内容复制到同花顺副图公式编辑器并保存，或在主图公式中引用。

2. Python 工具
   - 使用 python/tools/sub_chart_validator.py 对同花顺导出的日线CSV生成子评分：
     python python/tools/sub_chart_validator.py --csv data/sample.csv --out outputs/sub_chart

3. 输出说明
   - outputs/sub_chart/sub_chart_scores.csv 包含每一日的子评分列：volume_score, trend_score, chip_score, money_score, break_score, risk_score, total_score

