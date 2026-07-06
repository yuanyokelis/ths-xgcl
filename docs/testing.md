"""
测试系统文档

本文件说明如何在本地与 CI 环境运行测试、生成报告与查看覆盖率。

1. 本地运行
   - 安装开发依赖：pip install -r requirements-dev.txt
   - 运行测试并生成报告：
     python python/tools/test_runner.py
   - 生成的报告位于 outputs/tests/ 下，包含 report.html 与 coverage 报告目录

2. 集成测试
   - tests/test_integration.py 提供小样本的端到端集成测试，验证选股导出与回测运行基本流程。

3. CI 配置
   - 仓库包含 .github/workflows/ci.yml 在 GitHub Actions 上运行测试并上传报告为构件。

4. 覆盖率与质量
   - 使用 pytest-cov 生成 coverage，报告输出到 outputs/tests/coverage。
   - 如需额外静态分析（flake8, mypy），可在未来卷中加入 CI 检查。
"""
