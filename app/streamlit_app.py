import streamlit as st
import pandas as pd
from pathlib import Path
import yaml
import io
import datetime

# Try to import akshare and selection exporter
try:
    import akshare as ak
except Exception:
    ak = None

try:
    from python.tools.selection_exporter import score_single, run_directory
except Exception:
    score_single = None
    run_directory = None

CONFIG_PATH = Path('config/parameters.yaml')
THS_TEMPLATE_PATH = Path('ths/selection_formula.ths')

st.set_page_config(page_title='THS-XGCL 选股器', layout='wide')
st.title('THS-XGCL 选股器 (Streamlit)')

with st.sidebar:
    st.header('数据输入')
    mode = st.radio('输入方式', ['上传 CSV 文件', '本地目录', '通过 akshare 拉取'])
    if mode == '本地目录':
        local_dir = st.text_input('本地日线 CSV 目录', value='data/stocks')
    if mode == '通过 akshare 拉取':
        symbols_text = st.text_input('请输入股票代码（逗号分隔），示例: 600519,000001')
        exchange = st.selectbox('交易所前缀', ['sh', 'sz'], index=0)
        start_date = st.date_input('开始日期', value=datetime.date(2020,1,1))
        end_date = st.date_input('结束日期', value=datetime.date.today())

    st.header('参数')
    # Load params
    params = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                params = yaml.safe_load(f)
        except Exception as e:
            st.warning(f'读取参数文件失败: {e}')
    else:
        st.info('未找到 config/parameters.yaml，使用默认参数覆盖')

    # expose SCORE_THRESHOLD if present
    default_threshold = 80
    if isinstance(params, dict):
        # try nested key Score.DEFAULT_THRESHOLD or Score
        if 'Score' in params and isinstance(params['Score'], dict) and 'DEFAULT_THRESHOLD' in params['Score']:
            default_threshold = params['Score']['DEFAULT_THRESHOLD']
    threshold = st.slider('SCORE_THRESHOLD', min_value=0, max_value=100, value=int(default_threshold))
    topn = st.number_input('取前 N', min_value=1, max_value=1000, value=50)

    st.header('导出')
    export_ths = st.checkbox('启用导出同花顺公式 (.ths)')


st.write('---')

# Helper: normalize df columns

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    # ensure required columns exist
    expected = ['date','open','high','low','close','volume','amount']
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f'CSV 缺失列: {missing}，请确保包含 {expected}')
    # convert date
    df['date'] = pd.to_datetime(df['date'])
    return df


results_df = None

if st.button('运行选股'):
    st.info('开始运行...')
    # prepare params copy and override threshold
    params_local = {} if not params else dict(params)
    if 'Score' not in params_local or not isinstance(params_local['Score'], dict):
        params_local['Score'] = {'DEFAULT_THRESHOLD': threshold}
    else:
        params_local['Score']['DEFAULT_THRESHOLD'] = threshold

    if mode == '上传 CSV 文件':
        uploaded = st.file_uploader('上传CSV（可多选）', accept_multiple_files=True, type=['csv'])
        if not uploaded:
            st.warning('请先上传文件')
        else:
            rows = []
            for up in uploaded:
                try:
                    df = pd.read_csv(up)
                    df = normalize_df(df)
                    score = score_single(df, params_local) if score_single else float('nan')
                    rows.append({'symbol': Path(up.name).stem, 'score': score, 'close': df['close'].iloc[-1]})
                except Exception as e:
                    rows.append({'symbol': Path(up.name).stem, 'score': float('nan'), 'close': None, 'error': str(e)})
            results_df = pd.DataFrame(rows).sort_values('score', ascending=False)
    elif mode == '本地目录':
        p = Path(local_dir)
        if not p.exists() or not p.is_dir():
            st.warning('本地目录不存在或不可用')
        else:
            outp = Path('outputs/selection_streamlit')
            outp.mkdir(parents=True, exist_ok=True)
            try:
                results_df = run_directory(p, outp, params_local)
            except Exception as e:
                st.error(f'运行失败: {e}')
    elif mode == '通过 akshare 拉取':
        if ak is None:
            st.error('未安装 akshare，请先在环境中 pip install akshare')
        else:
            symbols = [s.strip() for s in symbols_text.split(',') if s.strip()]
            if not symbols:
                st.warning('请输入股票代码')
            else:
                rows = []
                for s in symbols:
                    code = f"{exchange}{s.zfill(6)}"
                    try:
                        # akshare returns DataFrame with date index or column
                        df = ak.stock_zh_a_daily(symbol=code, adjust='qfq')
                        # akshare returns columns: date, open, close, high, low, volume, turnover
                        if 'date' not in df.columns and df.index.name in [None, 'date']:
                            df = df.reset_index()
                        # normalize column names if different
                        df.rename(columns={'turnover':'amount'}, inplace=True)
                        df = normalize_df(df)
                        score = score_single(df, params_local) if score_single else float('nan')
                        rows.append({'symbol': s, 'score': score, 'close': df['close'].iloc[-1]})
                    except Exception as e:
                        rows.append({'symbol': s, 'score': float('nan'), 'close': None, 'error': str(e)})
                results_df = pd.DataFrame(rows).sort_values('score', ascending=False)

    if results_df is None:
        st.info('没有生成任何结果')
    else:
        st.success('选股完成')
        st.dataframe(results_df.head(int(topn)))
        csv_bytes = results_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
        st.download_button('下载选股结果 CSV', data=csv_bytes, file_name='selection_results.csv', mime='text/csv')

        if export_ths:
            # generate ths content by replacing SCORE_THRESHOLD in template if exists
            ths_content = None
            if THS_TEMPLATE_PATH.exists():
                try:
                    template = THS_TEMPLATE_PATH.read_text(encoding='utf-8')
                    # find SCORE_THRESHOLD line and replace
                    import re
                    new = re.sub(r"SCORE_THRESHOLD\s*:=\s*\d+;", f"SCORE_THRESHOLD:={threshold};", template)
                    ths_content = new
                except Exception as e:
                    st.error(f'读取或替换 ths 模板失败: {e}')
            else:
                # fallback: generate simple template
                ths_content = f"// 自动生成的同花顺公式\nSCORE_THRESHOLD:={threshold};\n// 请手动补充公式主体（源于 ths/selection_formula.ths）\n"
            if ths_content:
                st.download_button('下载同花顺公式 (.ths)', data=ths_content, file_name='selection_formula.ths', mime='text/plain')


st.write('---')
st.markdown('**说明**: 若要使用 akshare 拉取 A 股日线，请确保 akshare 已安装。akshare 的 symbol 需要带上交易所前缀，例如 `sh600519` 或 `sz000001`。')

st.sidebar.markdown('''
**注意**
- Streamlit 应用直接调用本仓库的 scoring 函数，请确保你的 Python 环境能 import 仓库路径（在仓库根运行）。
- 若对接 tushare 或其他接口，请在后端安全存储 token 并不要公开到仓库。
''')
