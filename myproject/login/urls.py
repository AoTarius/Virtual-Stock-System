from django.urls import path
from . import views

app_name = 'login'

urlpatterns = [
    path('loginview/', views.loginview, name='loginview'),
]