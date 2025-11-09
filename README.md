运行网页方法：在myproject根目录运行`python manage.py migrate`与`python manage.py runserver`

创建新的html文件需要修改一下路径（根目录是myproject）：
- `myapp/urls.py`
- `myapp/views.py`


待开发功能：
1. 用户界面 user.html，可以包含修改用户名（和充值选项，充值选项直接关系到invest投资中的余额，余额也可以在数据库中和userid挂钩）
2. 登录界面/注册界面 login.html，可以创建新用户，也可以登录，创建新用户则需要再数据库生成新的用户名和userid
3. 将html与django做适配
4. 调用python脚本的动态更新。主要要更新的内容包括：
    - invert.html 界面的某只股票今日股价、较昨日变化、30天走势图
    - overview.html 界面，用户查看自己的股票情况
    股票的调用已经有一个本地的脚本`get_user_stocks.py`，修改为django可调用的版本即可
    用户查看自己情况的需要先开发5
5. 设计数据库，记录用户名和userid的直接对应关系，以及数据库记录每一个userid的股票持有情况（包括哪天买的，买了多少股，买入价多少），用来在overview界面统一查询
6. 投资概览界面 overview.html，主要显示的内容是用户已购买的所有股票在当天的 总投入 总盈亏 总市价

可选开发：
1. 买卖记录界面 record.html，主要展示用户在哪一天买了或卖了哪些股票


==目前开发优先级==
首先研究3，同时开发1 2
4 5 6可以后续一人一个分开做，都是要用django动态更新的，3不做好都做不了


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