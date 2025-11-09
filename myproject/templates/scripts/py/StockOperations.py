# 此文件设计基本操作功能

import sqlite3
import tushare as ts
from pathlib import Path

# resolve db directory relative to this file so functions work when imported from Django
_TEMPLATES_DIR = Path(__file__).resolve().parents[2]  # points to .../myproject/templates
_DB_DIR = _TEMPLATES_DIR / 'db'

# 获取从 30 天前到 end_date 的股票数据
def get_stock30(end_date, code):
    token = 'fadb2289dc9b029eb4d43c567f11830de2ccddf28193dc4f8e9d864c'
    pro = ts.pro_api(token)
    try:
        df = pro.daily(ts_code=code, end_date=end_date, start_date=None, limit=30, fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount')
        print(df)
        return df
    except Exception as e:
        print(f"Error occurred: {e}")
    return None

# 获取目标日期的股票信息
def get_stock1(date, code):
    token = 'fadb2289dc9b029eb4d43c567f11830de2ccddf28193dc4f8e9d864c'
    pro = ts.pro_api(token)
    try:
        # Try several variants to improve hit-rate on tushare:
        # prefer exact code, then try trade_date param, then try adding common suffixes (.SZ/.SH),
        # and try upper/lower case variants.
        cand_codes = []
        c = str(code or '').strip()
        if not c:
            return None
        cand_codes.append(c)
        # if provided code includes dot-suffix, also try lower/upper variants and short code
        if '.' in c:
            parts = c.split('.')
            cand_codes.append(parts[0])
            cand_codes.append(parts[0] + '.' + parts[1].upper())
            cand_codes.append(parts[0] + '.' + parts[1].lower())
        else:
            # try common exchanges
            cand_codes.append(c + '.SZ')
            cand_codes.append(c + '.SH')

        # dedupe while preserving order
        seen = set(); codes = []
        for cc in cand_codes:
            key = cc.lower()
            if key not in seen:
                seen.add(key); codes.append(cc)

        last_exc = None
        for cc in codes:
            try:
                # first try: use trade_date param if supported
                try:
                    df = pro.daily(ts_code=cc, trade_date=date, fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount')
                except TypeError:
                    # older pro.daily signature may not accept trade_date keyword; fall back
                    df = None
                if df is None or (hasattr(df, 'empty') and df.empty):
                    # second try: use start_date/end_date
                    df = pro.daily(ts_code=cc, end_date=date, start_date=date, limit=1, fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount')
                if df is not None and not (hasattr(df, 'empty') and df.empty):
                    print(df)
                    return df
            except Exception as e:
                # record and continue to next candidate
                last_exc = e
                continue
        # if all attempts failed, raise last exception if any, else return empty dataframe
        if last_exc:
            print(f"get_stock1: all attempts failed, last error: {last_exc}")
        return None
    except Exception as e:
        print(f"Error occurred: {e}")
    return None


def buy_stock_on_date(user_id, stockID, date_yyyymmdd, piles):
    """
    在指定日期使用当日收盘价作为单价，替用户下单购买若干股。
    参数：
      user_id: int
      stockID: str (例如 '000001.SZ' 或 '000001')
      date_yyyymmdd: str, 格式 'YYYYMMDD'，用于从 tushare 获取当日收盘价
      piles: int
    返回：(success: bool, message: str, details: dict)
    details 可能包含 cost, unitPrice, remaining_funds 等
    """
    try:
        # 尝试获取当日收盘价
        df = get_stock1(date_yyyymmdd, stockID)
        if df is None or (hasattr(df, 'empty') and df.empty):
            return False, '无法获取当日股价', {}
        row = df.iloc[0]
        close = None
        try:
            close = float(row.get('close', row['close']))
        except Exception:
            try:
                close = float(row['close'])
            except Exception:
                close = None
        if close is None:
            return False, '当日收盘价不可用', {}

        unitPrice = close
        cost = float(piles) * float(unitPrice)

        # 规范化要写入数据库的 stockID：
        # 优先使用 tushare 返回的 ts_code（通常带后缀），否则如果传入的 stockID 没有后缀则默认补上 .SZ
        stored_stockID = stockID
        try:
            if df is not None and not (hasattr(df, 'empty') and df.empty):
                # tushare 的 daily 返回通常含有 ts_code 列（例如 '000001.SZ'）
                if 'ts_code' in df.columns:
                    ts_code_val = df.iloc[0].get('ts_code')
                    if ts_code_val:
                        stored_stockID = str(ts_code_val)
        except Exception:
            # ignore and fall back to heuristics below
            pass

        if '.' not in stored_stockID:
            # 若仍然没有后缀，默认添加 .SZ（这是常见的简易策略，若需要更精确可改为检测或传入完整代码）
            stored_stockID = f"{stored_stockID}.SZ"

        # 检查用户余额
        user_db_path = _DB_DIR / 'user.db'
        conn = sqlite3.connect(str(user_db_path))
        cur = conn.execute('SELECT funds FROM Users WHERE user_id = ?', (user_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return False, '用户不存在', {}
        funds = float(row[0])
        if funds < cost:
            return False, '余额不足', {'required': cost, 'funds': funds}

        # 将date_yyyymmdd转化为yyyy-mm-dd
        op_time = f"{date_yyyymmdd[0:4]}-{date_yyyymmdd[4:6]}-{date_yyyymmdd[6:8]} 15:00:00"

        # 扣款并更新 total_input and insert into UserStocks
        # 使用 existing helper deduct_funds (会更新 funds)
        deduct_funds(user_id, cost)

        stock_db_path = _DB_DIR / 'userStocks.db'
        sconn = sqlite3.connect(str(stock_db_path))
        sconn.execute('''
            INSERT OR IGNORE INTO UserStocks (user_id, stockID, time, operation, piles, unitPrice, cost)
            VALUES (?, ?, ?, '购买', ?, ?, ?)
        ''', (user_id, stored_stockID, op_time, piles, unitPrice, cost))
        sconn.commit()
        sconn.close()

        uconn = sqlite3.connect(str(user_db_path))
        uconn.execute('UPDATE Users SET total_input = total_input + ? WHERE user_id = ?', (cost, user_id))
        uconn.commit()
        # 查询剩余资金和总投入
        cur = uconn.execute('SELECT funds, total_input FROM Users WHERE user_id = ?', (user_id,))
        new_row = cur.fetchone()
        remaining = float(new_row[0]) if new_row else None
        new_total_input = float(new_row[1]) if new_row and new_row[1] is not None else None
        # round to 2 decimal places for frontend display
        if remaining is not None:
            remaining = round(remaining, 2)
        if new_total_input is not None:
            new_total_input = round(new_total_input, 2)
        uconn.close()

        return True, '购买成功', {'cost': cost, 'unitPrice': unitPrice, 'remaining_funds': remaining, 'total_input': new_total_input}
    except Exception as e:
        return False, str(e), {}

# 用户购买股票，返回bool值表示是否购买成功
def buy_stock(user_id, stockID, time, piles, unitPrice):
    """
    传入参数：
    user_id: 用户ID
    stockID: 股票代码
    time: 操作时间
    piles: 购买股数
    unitPrice: 单价
    """
    cost = float(piles) * float(unitPrice)

    user_db_path = _DB_DIR / 'user.db'
    user_conn = sqlite3.connect(str(user_db_path))
    # 检查用户余额是否足够
    cursor = user_conn.execute('''
        SELECT funds FROM Users WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    if row is None:
        print(f"用户：{user_id}不存在")
        user_conn.close()
        return
    current_funds = row[0]
    if current_funds < cost:
        print(f"用户：{user_id}余额不足，无法购买股票")
        user_conn.close()
        return False
    else:
        # 调用函数进行扣款（会更新 Users.funds）
        deduct_funds(user_id, cost)
        # 添加股票记录到 userStocks.db
        stock_db_path = _DB_DIR / 'userStocks.db'
        conn = sqlite3.connect(str(stock_db_path))
        conn.execute('''
            INSERT OR IGNORE INTO UserStocks (user_id, stockID, time, operation, piles, unitPrice, cost)
            VALUES (?, ?, ?, '购买', ?, ?, ?)
        ''', (user_id, stockID, time, piles, unitPrice, cost))

        conn.commit()
        conn.close()
        # 添加用户总投入金额
        user_db_path = _DB_DIR / 'user.db'
        conn = sqlite3.connect(str(user_db_path))
        conn.execute('''
            UPDATE Users
            SET total_input = total_input + ?
            WHERE user_id = ?
        ''', (cost, user_id))
        conn.commit()
        conn.close()

        print(f"用户：{user_id}股票购买完成")
        return True

# 用户充值
def deposit_funds(user_id, amount):
    """
    传入参数：
    user_id: 用户ID
    amount: 充值金额
    """
    db_path = _DB_DIR / 'user.db'
    conn = sqlite3.connect(str(db_path))
    conn.execute('''
        UPDATE Users
        SET funds = funds + ?
        WHERE user_id = ?
    ''', (amount, user_id))
    conn.commit()
    conn.close()
    print(f"用户：{user_id}充值完成")

# 用户扣款
def deduct_funds(user_id, amount):
    """
    传入参数：
    user_id: 用户ID
    amount: 扣款金额
    """
    db_path = _DB_DIR / 'user.db'
    conn = sqlite3.connect(str(db_path))
    conn.execute('''
        UPDATE Users
        SET funds = funds - ?
        WHERE user_id = ?
    ''', (amount, user_id))
    conn.commit()
    conn.close()
    print(f"用户：{user_id}扣款完成")

# 获取用户的总投入和总资产，在invest视图中使用
def get_user_financials(user_id):
    """
    传入参数：
    user_id: 用户ID
    返回值：
    (total_input, total_assets)
    """
    db_path = _DB_DIR / 'user.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute('''
        SELECT total_input, funds FROM Users WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        total_input, total_assets = row
        print(f"用户：{user_id}的总投入为：{total_input}，总资产为：{total_assets}")
        return total_input, total_assets
    else:
        print(f"用户：{user_id}不存在")
        return None, None

# 获取某一天的用户持有的所有股票的总市值，在overview视图中使用
def get_user_total_stock_value(user_id, date):
    """
    传入参数：
    user_id: 用户ID
    date: 日期，格式YYYYMMDD
    返回值：
    total_stock_value: 用户持有的所有股票的总市值
    """
    db_path = _DB_DIR / 'user.db'
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute('''
        SELECT total_input, funds FROM Users WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        total_input, total_assets = row
        print(f"用户：{user_id}的总投入为：{total_input}，总资产为：{total_assets}")
    else:
        print(f"用户：{user_id}不存在")
    
    stock_db_path = _DB_DIR / 'userStocks.db'
    conn = sqlite3.connect(str(stock_db_path))
    cursor = conn.execute('''
        SELECT stockID, SUM(piles) FROM UserStocks
        WHERE user_id = ? AND operation = '购买'
        GROUP BY stockID
    ''', (user_id,))
    stocks = cursor.fetchall()
    conn.close()

    total_stock_value = 0.0
    if not stocks:
        print(f"用户：{user_id}没有持有任何股票")
        return False, total_input, total_stock_value
    for stock in stocks:
        stockID, total_piles = stock
        df = get_stock1(date, stockID)
        if df is not None and not df.empty:
            closing_price = df.iloc[0]['close']
            total_stock_value += closing_price * total_piles

    print(f"用户：{user_id}在{date}的总股票市值为：{total_stock_value}")
    return True, total_input, total_stock_value


def get_user_holdings(user_id, date):
    """
    返回用户在指定日期的持仓明细列表。
    每个元素为 dict: {
        'stockID': str,
        'name': str,
        'close': float or None,
        'piles': int,
        'cost': float,  # 累计成本（unitPrice * piles 之和）
        'profit': float or None  # (close - avg_unitPrice) * piles
    }
    """
    # 先从 userStocks 聚合得到每只股票的总股数与总成本
    stock_db_path = _DB_DIR / 'userStocks.db'
    conn = sqlite3.connect(str(stock_db_path))
    cursor = conn.execute('''
        SELECT stockID, SUM(piles) as piles_sum, SUM(cost) as cost_sum, MAX(time) as last_purchase_time
        FROM UserStocks
        WHERE user_id = ? AND operation = '购买'
        GROUP BY stockID
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    # 读取 CSV 索引以获得股票名称（若存在）
    csv_path = _DB_DIR / 'stocks_20251028_125943.csv'
    code_to_name = {}
    try:
        import csv as _csv
        if csv_path.exists():
            # use utf-8-sig to strip BOM if present (some CSVs have a BOM)
            with csv_path.open('r', encoding='utf-8-sig') as f:
                rdr = _csv.DictReader(f)
                for r in rdr:
                    symbol = (r.get('symbol') or r.get('code') or r.get('ts_code') or '').strip()
                    market = (r.get('market') or r.get('exchange') or '').strip()
                    name = (r.get('name') or r.get('fullname') or r.get('stock_name') or '').strip()
                    if not symbol:
                        continue
                    # 生成多种可能的 key 以提高匹配命中率：
                    # - 原始 symbol（例如 000001）
                    # - 带 market 的形式（例如 000001.SZ 或 000001.sz）
                    # - 如果 symbol 本身已经包含后缀（000001.SZ），也一并处理
                    sym = symbol
                    mkt = market
                    variants = set()
                    sym_clean = sym.strip()
                    variants.add(sym_clean.lower())
                    if mkt:
                        variants.add(f"{sym_clean}.{mkt}".lower())
                        variants.add(f"{sym_clean}.{mkt.lower()}".lower())
                        variants.add(f"{sym_clean}.{mkt.upper()}".lower())
                    if '.' in sym_clean:
                        variants.add(sym_clean.lower())
                        variants.add(sym_clean.split('.')[0].lower())
                    # 把 name 写到所有变体上（优先保留第一个遇到的 name）
                    for k in variants:
                        if k and k not in code_to_name:
                            code_to_name[k] = name
    except Exception:
        code_to_name = {}

    holdings = []
    for stockID, piles_sum, cost_sum, last_purchase_time in rows:
        try:
            piles_sum = int(piles_sum) if piles_sum is not None else 0
        except Exception:
            piles_sum = 0
        try:
            cost_sum = float(cost_sum) if cost_sum is not None else 0.0
        except Exception:
            cost_sum = 0.0

        # fetch close price for date
        close_val = None
        try:
            df = get_stock1(date, stockID)
            if df is not None and not df.empty:
                close_val = float(df.iloc[0].get('close', df.iloc[0]['close']))
        except Exception:
            close_val = None

        avg_unit = (cost_sum / piles_sum) if piles_sum else None
        profit = None
        if close_val is not None and avg_unit is not None:
            profit = (close_val - avg_unit) * piles_sum

        # 尝试多种规范化匹配：优先用原始 stockID（小写、去空格），其次尝试去后缀，
        # 并兼容常见后缀 .sz / .sh
        name = ''
        try:
            key = str(stockID).strip().lower()
            if key:
                name = code_to_name.get(key, '')
                if not name and '.' in key:
                    name = code_to_name.get(key.split('.')[0], '')
                # 再尝试常见交易所后缀
                if not name:
                    for sfx in ('.sz', '.sh'):
                        maybe = key if key.endswith(sfx) else (key + sfx)
                        name = code_to_name.get(maybe, '')
                        if name:
                            break
        except Exception:
            name = ''

        holdings.append({
            'stockID': stockID,
            'name': name,
            'close': close_val,
            'piles': piles_sum,
            'cost': cost_sum,
            'profit': profit,
            'purchase_time': last_purchase_time,
        })

    return holdings

if __name__ == "__main__":
    # 示例操作
    import datetime
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    deposit_funds(1, 1000)  # 用户1充值1000
    # buy_stock(1, '000002.SZ', current_time, 15, 5.7)  # 用户1购买股票
    # get_stock30('20240620', '000001.SZ')  # 获取股票000001.SZ在2024-06-20的30天数据
    # get_stock1('20240620', '000001.SZ')  # 获取股票000001.SZ在2024-06-20的当天数据
    # total_input, total_assets = get_user_financials(1)
    # get_user_total_stock_value(1, '20240620')