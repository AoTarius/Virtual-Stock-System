from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from pathlib import Path
import csv

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
    return render(request, 'html/overview.html')

def invest(request):
    return render(request, 'html/invest.html')

def record(request):
    return render(request, 'html/record.html')


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