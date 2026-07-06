# 主图文档

本文件说明如何在同花顺中加载主图公式、参数说明与 Python 离线验证说明。

1. 加载主图公式
   - 将 ths/main_chart_formula.ths 内容复制到同花顺自定义公式编辑器，保存并应用到 K 线图主图。

2. 参数说明
   - 所有参数集中管理于 config/parameters.yaml。若需要更改主图常量（如均线周期、阈值），请在该文件中修改并在 Python 层重新生成公式或手动同步到 THS 公式顶部参数区。

3. 兼容性
   - 主图公式避免调用同花顺专有函数（WINNER/COST/FINANCE），采用近似算法实现筹码与资金判断，确保免费版与至尊版均能运行。

4. 离线验证
   - 使用 python/tools/main_chart_validator.py 对同花顺导出的日线 CSV 进行离线验证：
     python python/tools/main_chart_validator.py --csv data/sample.csv --out outputs/main_chart

5. 注意事项
   - 同花顺公式与 Python 算法在数值细节上可能存在微差，主要用于逻辑一致性验证。
