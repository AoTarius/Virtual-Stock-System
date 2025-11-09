from django.shortcuts import render, redirect
from django.db import connection
import sqlite3
from django.contrib.auth.hashers import check_password
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse
from django.conf import settings


def loginview(request):
    if request.method == 'POST':
        # 获取表单数据（模板使用 name="username" 和 name="password"）
        _username = request.POST.get('username')
        _password = request.POST.get('password')

        # 直接使用 sqlite3 连接到 settings 中配置的数据库文件，绕过 Django cursor 格式化问题
        db_path = None
        try:
            db_path = settings.DATABASES['default']['NAME']
        except Exception:
            db_path = None

        user = None
        if db_path:
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT password FROM Users WHERE username = ?", (_username,))
                user = cur.fetchone()
            except Exception:
                user = None
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        else:
            # 回退到 Django 的 connection.cursor（极少数情况下）
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT password FROM Users WHERE username = ?", [_username])
                    user = cursor.fetchone()
            except Exception:
                user = None

        if user:
            # 从数据库中取出的可能是明文密码或哈希值，优先使用 Django 的 check_password 验证哈希
            stored = user[0]
            # 兼容可能的空白或类型问题
            if isinstance(stored, bytes):
                try:
                    stored = stored.decode('utf-8')
                except Exception:
                    stored = stored.decode('latin-1', errors='ignore')
            if isinstance(stored, str):
                stored = stored.strip()
            if isinstance(_password, str):
                _password = _password.strip()

            # 调试信息（仅在 DEBUG 模式打印），便于在控制台排查接收值与数据库值是否一致
            if getattr(settings, 'DEBUG', False):
                try:
                    print(f"[DEBUG] 登录尝试: username_repr={_username!r}, posted_password_len={len(_password) if _password is not None else 'None'}")
                    print(f"[DEBUG] 数据库中存储的 password repr={stored!r}")
                except Exception:
                    pass
            valid = False
            try:
                if check_password(_password, stored):
                    valid = True
            except Exception:
                # 如果 stored 不是合法哈希，check_password 可能抛出，忽略并回退到明文比较
                valid = False

            # 回退：如果表中存的是明文密码，允许直接比较（兼容历史数据，建议尽快改为哈希存储）
            if not valid and stored == _password:
                valid = True

            if valid:
                # 登录成功，重定向到 overview（使用 myapp 的命名路由）
                return redirect('myapp:overview')
            else:
                error_msg = "密码错误，请重试。"
        else:
            error_msg = "用户不存在，请检查账号是否正确。"

        return render(request, 'html/login.html', {'error_msg': error_msg})

    # 如果是GET请求，直接渲染登录页面
    return render(request, 'html/login.html')