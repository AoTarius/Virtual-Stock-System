from django.shortcuts import render
from django.db import connection
from django.contrib.auth.hashers import check_password
from django.http import HttpResponse

def loginview(request):
    if request.method == 'POST':
        # 获取表单数据
        _username = request.POST.get('username')
        _password = request.POST.get('password')

        # 使用原生 SQL 查询用户
        with connection.cursor() as cursor:
            cursor.execute("SELECT password FROM Users WHERE username = %s", [_username])
            user = cursor.fetchone()

        if user:
            # 验证密码
            hashed_password = user[0]
            if check_password(_password, hashed_password):
                return HttpResponse('登录成功！')
            #这里加个转跳
                return redirect('/main/ordinarymainview')
            else:
                error_msg = "密码错误，请重试。"
        else:
            error_msg = "用户不存在，请检查账号是否正确。"

        return render(request, 'html/login.html', {'error_msg': error_msg})

    # 如果是GET请求，直接渲染登录页面
    return render(request, 'html/login.html')