# 自动参数优化 文档

本文件说明如何使用自动参数优化工具（python/tools/optimizer.py）

1. 参数空间定义（示例）
   - 编辑 config/param_grid_example.yaml，定义需要优化的参数和取值范围/集合。
   - 支持类型：choice, int, float；支持步长 step。

2. 运行方式
   - Grid Search：python python/tools/optimizer.py --mode grid --param-space config/param_grid_example.yaml --input data/stocks --out outputs/optimizer --budget 20 --quick
   - Random Search：python python/tools/optimizer.py --mode random --param-space config/param_grid_example.yaml --input data/stocks --out outputs/optimizer --budget 50 --quick
   - Bayesian（需 optuna）：python python/tools/optimizer.py --mode bayes --param-space config/param_grid_example.yaml --input data/stocks --out outputs/optimizer --budget 50

3. 输出文件
   - outputs/optimizer/trials.csv：每次试验记录（id, params, objective, time, metrics）
   - outputs/optimizer/best_params.yaml：当前找到的最佳参数及指标

4. 说明
   - quick 模式会缩短回测历史并采样少量股票以节省时间，仅用于快速探索。严谨评估请关闭 quick 模式并扩大 budget。
   - 贝叶斯优化依赖 optuna 库，如未安装，脚本会自动降级到随机搜索。
