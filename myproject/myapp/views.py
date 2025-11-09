from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from pathlib import Path
import csv
import importlib.util
import traceback

# 简单缓存：模块级字典，避免每次请求都读文件
_STOCK_MAP_BY_CODE = None
_STOCK_MAP_BY_NAME = None

def _ensure_stock_indexed():
    global _STOCK_MAP_BY_CODE, _STOCK_MAP_BY_NAME
    if _STOCK_MAP_BY_CODE is not None and _STOCK_MAP_BY_NAME is not None:
        return
    _STOCK_MAP_BY_CODE = {}
    _STOCK_MAP_BY_NAME = {}
    # 尝试在项目的 templates/db/ 下找到 CSV（仓库中此文件位于 templates/db/）
    base = Path(settings.BASE_DIR)
    csv_path = base / 'templates' / 'db' / 'stocks_20251028_125943.csv'
    if not csv_path.exists():
        # 退回到项目根的 db 目录（如果存在）
        alt = base / '..' / 'db' / 'stocks_20251028_125943.csv'
        if alt.exists():
            csv_path = alt
    try:
        with csv_path.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 兼容不同列名，优先使用 symbol/code/name
                code = (row.get('symbol') or row.get('code') or row.get('ts_code') or '').strip()
                name = (row.get('name') or row.get('fullname') or row.get('stock_name') or '').strip()
                if code:
                    _STOCK_MAP_BY_CODE[code.lower()] = {'code': code, 'name': name}
                if name:
                    _STOCK_MAP_BY_NAME[name.lower()] = {'code': code, 'name': name}
    except Exception:
        # 任何错误都不要抛出，保持字典为空以避免影响页面
        _STOCK_MAP_BY_CODE = _STOCK_MAP_BY_CODE or {}
        _STOCK_MAP_BY_NAME = _STOCK_MAP_BY_NAME or {}

def overview(request):
    # 将 session 中的用户信息传递给模板，便于页面显示当前用户
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    return render(request, 'html/overview.html', {'user_id': user_id, 'username': username})

def invest(request):
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    # 尝试动态加载 StockOperations.py 并获取用户财务数据（total_input, total_assets）
    total_input = None
    total_assets = None
    if user_id is not None:
        try:
            base = Path(settings.BASE_DIR)
            so_path = base / 'templates' / 'scripts' / 'py' / 'StockOperations.py'
            if so_path.exists():
                spec = importlib.util.spec_from_file_location('StockOperations', str(so_path))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                # 调用 get_user_financials，返回 (total_input, total_assets)
                try:
                    ti, ta = mod.get_user_financials(user_id)
                    total_input = ti if ti is not None else None
                    total_assets = ta if ta is not None else None
                except Exception:
                    # 保守处理：如果调用失败，保持 None
                    total_input = None
                    total_assets = None
        except Exception:
            # 任何加载/执行错误都不要抛出，继续渲染页面但不显示数值
            total_input = None
            total_assets = None

    # 回退方案：若上述方式未能获得数据，则直接访问本地 sqlite 数据库（更可靠，避免 StockOperations 中的相对路径问题）
    if (total_input is None or total_assets is None) and user_id is not None:
        try:
            import sqlite3
            base = Path(settings.BASE_DIR)
            # 常见位置：templates/db/user.db
            db_path = base / 'templates' / 'db' / 'user.db'
            if not db_path.exists():
                # 尝试上一级路径兼容性查找
                alt = base / '..' / 'templates' / 'db' / 'user.db'
                if alt.exists():
                    db_path = alt
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                try:
                    cur.execute('SELECT total_input, funds FROM Users WHERE user_id = ?', (int(user_id),))
                    row = cur.fetchone()
                    if row:
                        total_input = row[0]
                        total_assets = row[1]
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        except Exception:
            # 安全回退，不抛出错误
            total_input = total_input
            total_assets = total_assets
        except Exception:
            # 任何加载/执行错误都不要抛出，继续渲染页面但不显示数值
            total_input = None
            total_assets = None

    return render(request, 'html/invest.html', {
        'user_id': user_id,
        'username': username,
        'total_input': total_input,
        'total_assets': total_assets,
    })

def record(request):
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    return render(request, 'html/record.html', {'user_id': user_id, 'username': username})


def stock_lookup(request):
    """简单的 GET API：
    - ?code=000001 返回 {found: true, code: '000001', name: '平安银行'}
    - ?name=平安银行 返回对应 code
    如果未找到返回 {found: false}
    """
    _ensure_stock_indexed()
    qcode = request.GET.get('code')
    qname = request.GET.get('name')
    if qcode:
        key = qcode.strip().lower()
        item = _STOCK_MAP_BY_CODE.get(key)
        if item:
            return JsonResponse({'found': True, 'code': item['code'], 'name': item.get('name', '')})
        else:
            return JsonResponse({'found': False})
    if qname:
        key = qname.strip().lower()
        item = _STOCK_MAP_BY_NAME.get(key)
        if item:
            return JsonResponse({'found': True, 'code': item.get('code',''), 'name': item['name']})
        else:
            # 尝试模糊匹配（包含）
            for n, v in _STOCK_MAP_BY_NAME.items():
                if key in n:
                    return JsonResponse({'found': True, 'code': v.get('code',''), 'name': v.get('name','')})
            return JsonResponse({'found': False})
    return JsonResponse({'found': False})


def stock_csv(request):
    """Serve the CSV file used by the front-end indexing logic.
    This avoids relative path 404s when the template is served from a different URL.
    """
    base = Path(settings.BASE_DIR)
    csv_path = base / 'templates' / 'db' / 'stocks_20251028_125943.csv'
    if not csv_path.exists():
        alt = base / '..' / 'db' / 'stocks_20251028_125943.csv'
        if alt.exists():
            csv_path = alt
    try:
        if not csv_path.exists():
            return HttpResponse('Not Found', status=404)
        content = csv_path.read_text(encoding='utf-8')
        return HttpResponse(content, content_type='text/csv; charset=utf-8')
    except Exception as e:
        return HttpResponse('Error reading CSV: %s' % e, status=500)


def stock_info(request):
    """API: GET ?date=YYYYMMDD&code=000001.SZ
    Calls StockOperations.get_stock1(date, code) and returns JSON {found: true, close: x, change: y}
    """
    date = request.GET.get('date')
    code = request.GET.get('code')
    if not date or not code:
        return JsonResponse({'found': False, 'error': 'missing parameters'})

    # load StockOperations.py dynamically from templates/scripts/py
    try:
        base = Path(settings.BASE_DIR)
        so_path = base / 'templates' / 'scripts' / 'py' / 'StockOperations.py'
        if not so_path.exists():
            return JsonResponse({'found': False, 'error': 'StockOperations.py not found'})
        spec = importlib.util.spec_from_file_location('StockOperations', str(so_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # call function
        df = mod.get_stock1(date, code)
        if df is None:
            return JsonResponse({'found': False})
        # dataframe-like check
        try:
            if hasattr(df, 'empty') and df.empty:
                return JsonResponse({'found': False})
            # try to get first row
            row = df.iloc[0]
            close = row['close'] if 'close' in row else (row.get('close') if hasattr(row, 'get') else None)
            change = row['change'] if 'change' in row else (row.get('change') if hasattr(row, 'get') else None)
            # convert to float if possible
            try:
                close_val = float(close)
            except Exception:
                close_val = None
            try:
                change_val = float(change)
            except Exception:
                change_val = None
            if close_val is None and change_val is None:
                return JsonResponse({'found': False})
            return JsonResponse({'found': True, 'close': close_val, 'change': change_val})
        except Exception:
            traceback.print_exc()
            return JsonResponse({'found': False, 'error': 'unable to parse data'})
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'found': False, 'error': str(e)})