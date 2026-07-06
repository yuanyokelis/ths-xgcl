"""
测试运行器：运行 pytest，生成 HTML 报告与 coverage 报告
文件：python/tools/test_runner.py
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / 'outputs' / 'tests'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run_tests():
    # 安装 dev 依赖（可选，CI 环境通常已安装）
    # subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT / 'requirements-dev.txt')])
    # 运行 pytest，生成 junitxml, html 报告与 coverage
    html_report = OUT_DIR / 'report.html'
    junit = OUT_DIR / 'junit.xml'
    cov_dir = OUT_DIR / 'coverage'
    cov_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, '-m', 'pytest', str(ROOT / 'tests'), f'--junitxml={junit}', f'--html={html_report}', '--self-contained-html', '--cov=python', f'--cov-report=html:{cov_dir}']
    print('Running:', ' '.join(cmd))
    subprocess.check_call(cmd)
    print('测试完成，报告输出到', OUT_DIR)

if __name__ == '__main__':
    run_tests()
