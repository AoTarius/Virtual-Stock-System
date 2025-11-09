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
                # 同时获取 user_id, password, username（如果有记录 username）
                cur.execute("SELECT user_id, password, username FROM Users WHERE username = ?", (_username,))
                user = cur.fetchone()
            except Exception:
                # 若表结构不同（没有 username 列），尝试退回到仅取 user_id,password
                try:
                    cur.execute("SELECT user_id, password FROM Users WHERE username = ?", (_username,))
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
                    cursor.execute("SELECT user_id, password, username FROM Users WHERE username = ?", [_username])
                    user = cursor.fetchone()
            except Exception:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT user_id, password FROM Users WHERE username = ?", [_username])
                        user = cursor.fetchone()
                except Exception:
                    user = None

        if user:
            # user 可能为 (user_id, password, username) 或 (user_id, password)
            if len(user) >= 2:
                user_id = user[0]
                stored = user[1]
                db_username = user[2] if len(user) >= 3 else _username
            else:
                # 意外格式，回退
                user_id = None
                stored = user[0]
                db_username = _username
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
                # 登录成功：把用户信息写入 session，便于后续页面识别当前用户
                try:
                    if user_id is not None:
                        request.session['user_id'] = int(user_id)
                    request.session['username'] = db_username
                except Exception:
                    pass
                return redirect('myapp:overview')
            else:
                error_msg = "密码错误，请重试。"
        else:
            error_msg = "用户不存在，请检查账号是否正确。"

        return render(request, 'html/login.html', {'error_msg': error_msg})

    # 如果是GET请求，直接渲染登录页面
    return render(request, 'html/login.html')

def registview(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if not username or not password:
            error_msg = "账号或密码不能为空。"
            return render(request, 'html/regist.html', {'error_msg': error_msg})
        db_path = settings.DATABASES['default']['NAME']

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM Users WHERE username = ?", (username,))
            if cur.fetchone()[0] > 0:
                error_msg = "该账号已存在，请使用其他账号。"
                return render(request, 'html/regist.html', {'error_msg': error_msg})

            cur.execute("SELECT MAX(user_id) FROM Users")
            max_user_id = cur.fetchone()[0]
            new_user_id = (max_user_id + 1) if max_user_id is not None else 1

            # 插入新用户数据
            cur.execute(
                '''
                INSERT INTO Users (user_id, username, password, funds)
                VALUES (?, ?, ?, 0)
                ''',
                (new_user_id, username, password)
            )
            conn.commit()
            conn.close()

            # 注册成功后跳转到登录页面
            return render(request, 'html/login.html', {'success_msg': "注册成功，请登录。"})

        except Exception as e:
            error_msg = f"注册失败，请稍后重试。错误信息：{str(e)}"
            return render(request, 'html/regist.html', {'error_msg': error_msg})

    # 如果是GET请求，直接渲染注册页面
    return render(request, 'html/regist.html')