import streamlit as st
import pandas as pd
from pathlib import Path
import yaml
import io
import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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
DATA_DIR = Path('data/stocks')

st.set_page_config(page_title='THS-XGCL 选股器', layout='wide')
st.title('THS-XGCL 选股器 (Streamlit)')

with st.sidebar:
    st.header('数据输入')
    mode = st.radio('输入方式', ['上传 CSV 文件', '本地目录', '通过 akshare 拉取', '按板块/指数拉取'])
    if mode == '本地目录':
        local_dir = st.text_input('本地日线 CSV 目录', value='data/stocks')
    if mode == '通过 akshare 拉取':
        symbols_text = st.text_input('请输入股票代码（逗号分隔），示例: 600519,000001')
        exchange = st.selectbox('交易所前缀', ['sh', 'sz'], index=0)
        start_date = st.date_input('开始日期', value=datetime.date(2020,1,1))
        end_date = st.date_input('结束日期', value=datetime.date.today())

    if mode == '按板块/指数拉取':
        # Universe selection options
        universe = st.selectbox('选择股票池', ['All A股', '沪市 (SH)', '深市 (SZ)', '创业板 (创业板/科创板 300/688 等)', '指定指数成分（输入指数代码）'])
        if universe == '指定指数成分（输入指数代码）':
            index_code = st.text_input('指数代码（示例：000300）', value='000300')
        max_workers = st.slider('并发线程数', min_value=1, max_value=20, value=6)
        force_refresh = st.checkbox('强制刷新已有本地缓存（会重新下载）', value=False)

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
    expected = ['date','open','high','low','close','volume','amount']
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f'CSV 缺失列: {missing}，请确保包含 {expected}')
    df['date'] = pd.to_datetime(df['date'])
    return df

# Functions to get code lists

def get_all_a_codes():
    if ak is None:
        raise RuntimeError('未安装 akshare')
    df = ak.stock_info_a_code_name()
    # try to find code column
    code_col = None
    for c in df.columns:
        if 'code' in c.lower() or '代码' in c:
            code_col = c
            break
    if code_col is None:
        # fallback: first column
        code_col = df.columns[0]
    codes = df[code_col].astype(str).tolist()
    codes = [c.zfill(6) for c in codes]
    return codes

def code_with_prefix(code: str) -> str:
    return ('sh' if code.startswith('6') else 'sz') + code

def get_index_constituents(index_code: str):
    """Try multiple akshare index constituent functions for compatibility."""
    if ak is None:
        raise RuntimeError('未安装 akshare')
    # common functions: ak.index_stock_cons, ak.index_stock_cons_em
    for fn in ('index_stock_cons', 'index_stock_cons_em', 'index_stock_cons_ths'):
        if hasattr(ak, fn):
            try:
                df = getattr(ak, fn)(index_code)
                # try locate code column
                for c in df.columns:
                    if 'code' in c.lower() or '代码' in c:
                        codes = df[c].astype(str).tolist()
                        return [x.zfill(6) for x in codes]
                # fallback: first column
                codes = df.iloc[:,0].astype(str).tolist()
                return [x.zfill(6) for x in codes]
            except Exception:
                continue
    raise RuntimeError('无法通过 akshare 获取指数成分，请确认 akshare 版本或手动输入指数成分')

# Downloader with caching and concurrency

def fetch_and_save_daily(code, prefix='sh', force_refresh=False, retries=2):
    symbol = f"{prefix}{code}"
    outp = DATA_DIR / f"{code}.csv"
    if outp.exists() and not force_refresh:
        try:
            df_exist = pd.read_csv(outp)
            last_date = pd.to_datetime(df_exist['date']).max()
            if (pd.Timestamp.today() - last_date).days < 4:
                return True, symbol, 'skipped'
        except Exception:
            # fallthrough to re-download
            pass
    last_err = None
    for attempt in range(retries + 1):
        try:
            df = ak.stock_zh_a_daily(symbol=symbol, adjust='qfq')
            if 'date' not in df.columns and df.index.name in (None, 'date'):
                df = df.reset_index()
            df.rename(columns={'turnover':'amount'}, inplace=True)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(outp, index=False, encoding='utf-8-sig')
            return True, symbol, 'ok'
        except Exception as e:
            last_err = e
            time.sleep(0.5 + attempt)
    return False, symbol, f'error: {last_err}'

def download_codes(codes, max_workers=6, force_refresh=False, progress_callback=None):
    results = []
    total = len(codes)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fetch_and_save_daily, code, ('sh' if code.startswith('6') else 'sz'), force_refresh): code for code in codes}
        done = 0
        for fut in as_completed(futures):
            ok, symbol, status = fut.result()
            done += 1
            results.append({'symbol': symbol, 'ok': ok, 'status': status})
            if progress_callback:
                progress_callback(done, total, symbol, status)
    return results

results_df = None

if st.button('运行选股'):
    st.info('开始运行...')
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
                    code = s.zfill(6)
                    code_pref = ('sh' if code.startswith('6') else 'sz')
                    try:
                        df = ak.stock_zh_a_daily(symbol=f"{code_pref}{code}", adjust='qfq')
                        if 'date' not in df.columns and df.index.name in [None, 'date']:
                            df = df.reset_index()
                        df.rename(columns={'turnover':'amount'}, inplace=True)
                        df = normalize_df(df)
                        score = score_single(df, params_local) if score_single else float('nan')
                        rows.append({'symbol': s, 'score': score, 'close': df['close'].iloc[-1]})
                    except Exception as e:
                        rows.append({'symbol': s, 'score': float('nan'), 'close': None, 'error': str(e)})
                results_df = pd.DataFrame(rows).sort_values('score', ascending=False)
    elif mode == '按板块/指数拉取':
        if ak is None:
            st.error('未安装 akshare，请先在环境中 pip install akshare')
        else:
            st.info('开始准备股票池代码列表...')
            try:
                if universe == 'All A股':
                    codes = get_all_a_codes()
                elif universe == '沪市 (SH)':
                    codes = [c for c in get_all_a_codes() if c.startswith('6')]
                elif universe == '深市 (SZ)':
                    codes = [c for c in get_all_a_codes() if not c.startswith('6')]
                elif universe.startswith('创业板'):
                    # 简单 use prefix '3' and '688' for 科创板
                    all_codes = get_all_a_codes()
                    codes = [c for c in all_codes if c.startswith('3') or c.startswith('688') or c.startswith('301')]
                else:
                    # 指定指数成分
                    codes = get_index_constituents(index_code)

                st.info(f'股票池大小: {len(codes)}')
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_cb(done, total, symbol, status):
                    progress_bar.progress(done / total)
                    status_text.text(f"{done}/{total}  当前: {symbol}  状态: {status}")

                res = download_codes(codes, max_workers=max_workers, force_refresh=force_refresh, progress_callback=progress_cb)
                st.write('下载完成，开始使用本地缓存运行选股')
                outp = Path('outputs/selection_streamlit')
                outp.mkdir(parents=True, exist_ok=True)
                results_df = run_directory(DATA_DIR, outp, params_local)
            except Exception as e:
                st.error(f'准备股票池或下载失败: {e}')

    if results_df is None:
        st.info('没有生成任何结果')
    else:
        st.success('选股完成')
        st.dataframe(results_df.head(int(topn)))
        csv_bytes = results_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
        st.download_button('下载选股结果 CSV', data=csv_bytes, file_name='selection_results.csv', mime='text/csv')

        if export_ths:
            ths_content = None
            if THS_TEMPLATE_PATH.exists():
                try:
                    template = THS_TEMPLATE_PATH.read_text(encoding='utf-8')
                    import re
                    new = re.sub(r"SCORE_THRESHOLD\s*:=\s*\d+;", f"SCORE_THRESHOLD:={threshold};", template)
                    ths_content = new
                except Exception as e:
                    st.error(f'读取或替换 ths 模板失败: {e}')
            else:
                ths_content = f"// 自动生成的同花顺公式\nSCORE_THRESHOLD:={threshold};\n// 请手动补充公式主体（源于 ths/selection_formula.ths）\n"
            if ths_content:
                st.download_button('下载同花顺公式 (.ths)', data=ths_content, file_name='selection_formula.ths', mime='text/plain')

st.write('---')
st.markdown('**说明**: 若要使用 akshare 拉取 A 股日线，请确保 akshare 已安装。akshare 的 symbol 需要带上交易所前缀，例如 `sh600519` 或 `sz000001`。')

st.sidebar.markdown('''
**注意**
- Streamlit 应用直接调用本仓库的 scoring 函数，请确保你的 Python 环境能 import 仓库路径（在仓库根运行）。
- 若对接 tushare 或其他接口，请在后端安全存储 token 并不要公开到仓库。
- All A股 或较大指数拉取会非常耗时，请耐心等待或优先选择指数/板块子集。
''')