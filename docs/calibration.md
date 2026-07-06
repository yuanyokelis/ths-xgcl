# 校准文档

本文件说明评分权重校准的目的、运行方式与如何应用推荐权重。

1. 目的
   - 根据历史回测结果寻找更优的评分权重组合，使策略在期望目标函数下表现更好（默认目标函数同时追求收益与夏普、抑制回撤）。

2. 运行方式（快速入门）
   - 准备数据：将多只股票日线 CSV 放入 data/stocks/，文件名为 {symbol}.csv
   - 运行校准（快速模式）：
     python python/tools/calibrator.py --input data/stocks --out outputs/calibrator --step 0.1 --quick
   - 输出：outputs/calibrator/trials.csv，config/parameters_calibrated.yaml

3. 结果解释与应用
   - config/parameters_calibrated.yaml 包含最佳权重与对应回测指标，建议人工审核后决定是否覆盖原始 config/parameters.yaml。
   - 若你选择自动覆盖，我可以在后续实现覆盖并备份原始文件的功能。

4. 严谨模式
   - 关闭 --quick 并将 step 调小（例如 0.05），可获得更细粒度的校准，但计算量显著上升。

5. 注意事项
   - 校准只根据所提供的数据与回测模型做出建议，结果依赖于数据质量、回测设定与目标函数定义。请在生产环境中谨慎应用并进行额外验证。
