import sqlite3
from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]  # myproject
DB_DIR = BASE / 'templates' / 'db'
USERSTOCKS = DB_DIR / 'userStocks.db'
CSV = DB_DIR / 'stocks_20251028_125943.csv'

print('DB paths:')
print(' userStocks:', USERSTOCKS)
print(' csv:', CSV)

conn = sqlite3.connect(str(USERSTOCKS))
cur = conn.cursor()
cur.execute("SELECT DISTINCT stockID FROM UserStocks LIMIT 30")
rows = cur.fetchall()
conn.close()

sample_ids = [r[0] for r in rows]
print('\nSample stockIDs from UserStocks (up to 30):')
for sid in sample_ids:
    print(' -', repr(sid))

# build csv map similar to StockOperations
code_to_name = {}
if CSV.exists():
    # use utf-8-sig to handle possible BOM in header
    with CSV.open('r', encoding='utf-8-sig') as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            sym = (r.get('symbol') or r.get('code') or r.get('ts_code') or '').strip()
            mkt = (r.get('market') or r.get('exchange') or '').strip()
            name = (r.get('name') or r.get('fullname') or '').strip()
            if not sym:
                continue
            variants = set()
            sc = sym
            variants.add(sc.lower())
            if mkt:
                variants.add(f"{sc}.{mkt}".lower())
                variants.add(f"{sc}.{mkt.lower()}".lower())
                variants.add(f"{sc}.{mkt.upper()}".lower())
            if '.' in sc:
                variants.add(sc.lower())
                variants.add(sc.split('.')[0].lower())
            for k in variants:
                if k and k not in code_to_name:
                    code_to_name[k] = name
else:
    print('CSV file not found')

print('\nTesting sample stockIDs against CSV index:')
for sid in sample_ids:
    key = (str(sid).strip().lower() if sid is not None else '')
    matched = None
    if key:
        matched = code_to_name.get(key)
        if not matched and '.' in key:
            matched = code_to_name.get(key.split('.')[0])
        if not matched:
            for sfx in ('.sz', '.sh'):
                maybe = key if key.endswith(sfx) else (key + sfx)
                matched = code_to_name.get(maybe)
                if matched:
                    break
    print(f"{repr(sid):30} -> {matched!r}")

print('\nTotal CSV keys loaded:', len(code_to_name))

# Also print a handful of CSV entries for visual check
print('\nFirst 10 CSV rows:')
if CSV.exists():
    with CSV.open('r', encoding='utf-8-sig') as f:
        rdr = csv.reader(f)
        for i, row in enumerate(rdr):
            print(row)
            if i >= 9:
                break
