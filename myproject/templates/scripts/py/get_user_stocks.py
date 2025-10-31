#!/usr/bin/env python3
"""
get_user_stocks.py

用途：从命令行或标准输入接收股票代码（和可选结束日期），使用 tushare 拉取指定结束日期往前 N 天（默认为 30 天）内的日线数据，
在终端打印表格（发送到 stderr），并将结构化 JSON输出到 stdout（便于被 HTML/外部进程读取）。

用法示例：
  # 通过命令行参数
  python get_user_stocks.py --code 600519 --end-date 20251028 --days 30 --token YOUR_TUSHARE_TOKEN

  # 或者通过 stdin 传入 JSON（适合被后端或前端子进程调用）
  echo '{"code":"600519","end_date":"2025-10-28","days":30}' | python get_user_stocks.py

注意：本文件已经内置 token。

使用实例：
在项目根或任意目录运行（示例查询 600519 最近 30 天）
python .\scripts\py\get_user_stocks.py --code 600519
指定结束日期和天数
python .\scripts\py\get_user_stocks.py --code 600519 --end-date 2025-10-28 --days 30
"""

from __future__ import annotations

import sys
import os
import argparse
import json
from datetime import datetime, timedelta
from typing import Optional

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def parse_args():
    parser = argparse.ArgumentParser(description='Fetch 30-day stock data via tushare and output JSON to stdout.')
    parser.add_argument('--code', '-c', help='股票代码，例如 600519 或 000001', required=False)
    parser.add_argument('--end-date', '-e', help='结束日期，格式 YYYYMMDD 或 YYYY-MM-DD（默认今天）', required=False)
    parser.add_argument('--days', '-n', type=int, default=30, help='向前查询天数，默认为 30')
    # 默认不在代码中硬编码 token，优先从参数或环境变量 TUSHARE_TOKEN 获取
    parser.add_argument('--token', '-t', default='fadb2289dc9b029eb4d43c567f11830de2ccddf28193dc4f8e9d864c', help='tushare token（可选，若未提供将尝试环境变量 TUSHARE_TOKEN）', required=False)
    return parser.parse_args()


def normalize_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    try:
        if '-' in s:
            dt = datetime.strptime(s, '%Y-%m-%d')
        else:
            dt = datetime.strptime(s, '%Y%m%d')
        return dt.strftime('%Y%m%d')
    except Exception:
        return None


def prepare_dates(end_date: Optional[str], days: int):
    if end_date:
        end_norm = normalize_date(end_date)
        if not end_norm:
            raise ValueError('end_date 格式错误，应为 YYYYMMDD 或 YYYY-MM-DD')
        end_dt = datetime.strptime(end_norm, '%Y%m%d')
    else:
        end_dt = datetime.today()
    start_dt = end_dt - timedelta(days=days)
    return start_dt.strftime('%Y%m%d'), end_dt.strftime('%Y%m%d')


def try_fetch_with_variants(pro, code: str, start_date: str, end_date: str):
    """尝试用若干 code 变体去拉取（原始、.SZ、.SH），返回 DataFrame 或 None"""
    try_codes = [code]
    # 如果仅是 6 位数字，尝试加入交易所后缀
    if code.isdigit() and len(code) == 6:
        try_codes.extend([code + '.SZ', code + '.SH'])

    for c in try_codes:
        try:
            df = pro.daily(ts_code=c, start_date=start_date, end_date=end_date)
            if df is not None and len(df) > 0:
                # 返回按日期升序排列
                return df.sort_values('trade_date')
        except Exception as ex:
            # 记录并继续尝试下一个变体
            eprint(f'尝试使用 ts_code={c} 失败: {ex}')
            continue
    return None


def main():
    args = parse_args()

    # 允许从 stdin 接收 JSON（优先）
    stdin_data = None
    if not sys.stdin.isatty():
        try:
            txt = sys.stdin.read().strip()
            if txt:
                stdin_data = json.loads(txt)
        except Exception:
            # 忽略解析错误，继续用 args
            stdin_data = None

    code = None
    end_date = None
    days = args.days
    token = args.token or os.environ.get('TUSHARE_TOKEN')

    if stdin_data:
        code = stdin_data.get('code') or stdin_data.get('ts_code')
        end_date = stdin_data.get('end_date') or stdin_data.get('date')
        days = int(stdin_data.get('days', days))

    # 命令行参数覆盖 stdin
    if args.code:
        code = args.code
    if args.end_date:
        end_date = args.end_date
    if args.token:
        token = args.token

    if not code:
        eprint('错误：未提供股票代码。请通过 --code 或 stdin JSON 提供 code。')
        sys.exit(2)

    if not token:
        eprint('错误：未提供 tushare token。请通过 --token 参数或环境变量 TUSHARE_TOKEN 填写。')
        sys.exit(3)

    # 计算日期范围
    try:
        start_date, end_date = prepare_dates(end_date, days)
    except ValueError as ve:
        eprint('日期参数错误：', ve)
        sys.exit(4)

    # 延迟导入 tushare 和 pandas，以便报错信息更清楚
    try:
        import tushare as ts
        import pandas as pd
    except Exception as ex:
        eprint('缺少依赖：请确保已安装 tushare 和 pandas（pip install tushare pandas）')
        eprint('Import error:', ex)
        sys.exit(5)

    # 初始化 pro api
    try:
        pro = ts.pro_api(token)
    except Exception as ex:
        eprint('初始化 tushare pro_api 失败：', ex)
        sys.exit(6)

    eprint(f'查询代码={code}，日期范围 {start_date} - {end_date}（近 {days} 天）')

    df = try_fetch_with_variants(pro, code, start_date, end_date)

    if df is None or df.empty:
        # 输出结构化 JSON（便于前端处理）
        out = {'status': 'not_found', 'code': code, 'start_date': start_date, 'end_date': end_date, 'data': []}
        print(json.dumps(out, ensure_ascii=False))
        eprint('未找到对应数据（尝试过常见后缀 .SZ /.SH）')
        sys.exit(0)

    # 保留常用列并格式化
    cols = ['trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']
    available = [c for c in cols if c in df.columns]
    df_out = df[available].copy()
    # 确保日期格式统一
    df_out['trade_date'] = df_out['trade_date'].astype(str)

    # 给终端用户友好显示（输出到 stderr）
    try:
        eprint('\n== 拉取到的数据（表格，最近几行） ==')
        eprint(df_out.tail(10).to_string(index=False))
    except Exception:
        eprint('无法以表格形式打印（pandas 可能不可用或数据格式异常）')

    # 构造 JSON 返回（stdout）
    records = df_out.to_dict(orient='records')
    out = {'status': 'ok', 'code': code, 'start_date': start_date, 'end_date': end_date, 'rows': records}
    # stdout 输出纯 JSON，方便 html/父进程读取
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
