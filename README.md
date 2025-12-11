运行网页方法：在myproject根目录运行`python manage.py migrate`与`python manage.py runserver`
输出配置、标准库以及第三方库的信息:`python manage.py envstat`

创建新的html文件需要修改一下路径（根目录是myproject）：
- `myapp/urls.py`
- `myapp/views.py`


待开发功能：
1. `user.html`，包括充值功能。充值可以使用StockOperations中的`deposit_funds`进行充值

可选开发：
1. 买卖记录界面 record.html，主要展示用户在哪一天买了或卖了哪些股票


django开发：
1. 创建django环境。在项目文件夹根目录下使用`django-admin startproject <项目名称>`，创建新项目
2. 同样在项目的根目录下，运行`python manage.py startapp <功能名称>`，创建新功能
3. 在项目的根目录下，运行`python manage.py runserver`，使用manager.py启动服务器，对应的url会在终端给出

创建`django`文件之后，首先会有若干预制文件：
- `settings.py`：全局声明文件
- `urls.py`：负责链接各个功能的连接器
```python
from django.contrib import admin
from django.urls import path
from django.urls import include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', include('login.urls')), # 新创建的方法需要写方法的路径
]

```
同样的，在使用了`python manage.py startapp <方法名>`创建方法之后，也会得到若干的预支文件，其中最重要的几个如下：
- `urls.py`：需要复制`django`主文件里面的同名文件过来，然后将需要使用的视图路径修改好。
- `views.py`：负责提供各种功能与方法，称为视图
```python
# urls.py
from django.urls import path
from django.urls import include
from . import views

urlpatterns = [
    path('login_view/',views.login_view), # 方法内部调用具体的视图
]


# views.py
from django.shortcuts import render

from django.http import HttpResponse
def login_view(request):
    return HttpResponse("This is the login view.")  
```

测试用充值功能：cmd运行`python manage.py runserver`后，
直接在浏览器输入：'http://127.0.0.1:8000/myapp/dev/set_funds/?username=yourusername&amount=任何数字'
快速测试：http://127.0.0.1:8000/myapp/invest/