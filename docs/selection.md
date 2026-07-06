# 选股文档

本文件说明如何使用选股公式与 Python 导出工具。

1. 同花顺内选股
   - 将 ths/selection_formula.ths 的内容复制到同花顺条件选股公式编辑器，保存后在条件选股器中运行，公式会输出 1/0 标识符合条件的个股。
   - 公式基于主图与副图的近似评分规则，默认阈值为 config/parameters.yaml 中的 Score.DEFAULT_THRESHOLD（主公式顶部的 SCORE_THRESHOLD 也需同步）。

2. 离线批量选股
   - 将多只股票的日线 CSV 放入同一目录（例如 data/stocks/，文件名为 {symbol}.csv），然后运行：
     python python/tools/selection_exporter.py --input data/stocks --out outputs/selection
   - 输出：outputs/selection/selection_results.csv 与 selection_results.xlsx，包含 symbol, score, close 等列，按 score 降序。

3. 参数同步
   - 参数文件位于 config/parameters.yaml。若你调整权重或阈值，请将 SCORE_THRESHOLD 同步到 ths/selection_formula.ths 的顶部参数区，或使用脚本自动替换（后续卷将提供自动同步工具）。
