#!/usr/bin/env python3
"""
一键更新看板数据：先从根目录 PDF 抽取，再清洗/建模写入 data/processed/。
用法：在项目根目录执行  python3 scripts/update_data.py
"""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def main():
    os.chdir(PROJECT_ROOT)
    steps = [
        ("抽取 PDF", [sys.executable, str(SCRIPT_DIR / "extract_pdf_data.py")]),
        ("清洗与建模", [sys.executable, str(SCRIPT_DIR / "clean_and_model.py")]),
    ]
    for name, cmd in steps:
        print(f"\n--- {name} ---")
        ret = subprocess.run(cmd)
        if ret.returncode != 0:
            print(f"错误：{name} 执行失败，退出码 {ret.returncode}", file=sys.stderr)
            sys.exit(ret.returncode)
    print("\n数据已更新至 data/processed/，可刷新看板或推送后 Reboot Streamlit Cloud 应用。")


if __name__ == "__main__":
    main()
