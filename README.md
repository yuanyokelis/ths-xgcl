# THS Quant V5.0 Enterprise

本仓库：同花顺企业级量化智能评分选股系统（THS Quant V5.0 Enterprise）。

当前提交为第 一 卷：系统架构（Volume 1 - System Architecture）。

本卷包括：

* 总体模块划分与职责说明
* 模块接口定义（输入/输出/参数）
* 参数集中管理示例（config/parameters.yaml）
* 文件/目录树草案
* Python 项目骨架（core/ 模块入口）
* 初始单元测试占位（tests/）
* 文档（docs/architecture.md）

后续我将继续分卷交付其余各卷的完整源码、THS 公式、回测工具、自动优化、单元测试与文档。

请参考 docs/architecture.md 以获取系统架构与模块关系图。

\## Streamlit 交互式选股界面（本地运行与部署）



本项目包含一个交互式的 Streamlit 应用，用于：

\- 在页面中输入/选择股票池（上传 CSV、本地目录、通过 akshare 拉取或按板块/指数拉取）

\- 设置选股参数（如 SCORE\_THRESHOLD）并一键运行选股

\- 支持下载选股结果 CSV，并导出同花顺公式（.ths）

\- 支持并发下载、进度条与本地缓存（data/stocks/）



\### 本地运行（推荐）

1\. 进入仓库根目录：

&#x20;  cd F:\\github\\ths-xgcl



2\. 创建并激活 Python 虚拟环境（PowerShell）：

&#x20;  python -m venv .venv

&#x20;  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force

&#x20;  . .venv\\Scripts\\Activate.ps1



&#x20;  或在 cmd:

&#x20;  .venv\\Scripts\\activate.bat



3\. 安装依赖：

&#x20;  python -m pip install --upgrade pip

&#x20;  # 推荐依赖（至少包含下面这些）

&#x20;  pip install streamlit pandas pyyaml openpyxl

&#x20;  # 若使用 akshare 拉取 A 股数据

&#x20;  pip install akshare



&#x20;  如果你有 requirements-dev.txt，也可以：

&#x20;  pip install -r requirements-dev.txt



4\. 运行 Streamlit 应用：

&#x20;  streamlit run app/streamlit\_app.py



5\. 在浏览器打开： http://localhost:8501 ，在侧边栏选择数据源和参数，点击“运行选股”。



\### 部署到 Streamlit Cloud（快速）

1\. 在 GitHub 上 fork 或将仓库推到你的账号下并确认包含 app/streamlit\_app.py。

2\. 登录 https://streamlit.io/cloud ，创建新应用，选择你的仓库和对应分支（main 或 feature 分支）。

3\. 在部署设置中，指定启动命令（通常不需要，Streamlit 会自动检测）：

&#x20;  streamlit run app/streamlit\_app.py

4\. 在 “Advanced settings” 中设置任何需要的环境变量（如果集成需要外部 tokens，切勿放到公开 repo）。

5\. 部署后你会获得一个公开 URL，可在团队/设备上访问。



\### 部署建议与注意事项

\- 全 A 股或大型指数拉取会非常耗时，建议：

&#x20; - 首次运行时在夜间或低峰时段执行；

&#x20; - 使用较小的并发数（例如 4-8），遇到频繁失败再降低；

&#x20; - 使用本地缓存（data/stocks/），后续只更新增量。

\- 若使用第三方 API（如 tushare），请把 token 放到部署平台的环境变量中。

\- 若公开部署在公网，建议加入访问控制（基本认证或 IP 白名单），避免滥用拉取接口。



