from django.urls import path
from . import views

app_name = 'myapp'
urlpatterns = [
    path('', views.overview, name='overview'),
    path('invest/', views.invest, name='invest'),
    path('stock-lookup/', views.stock_lookup, name='stock_lookup'),
    path('stock-info/', views.stock_info, name='stock_info'),
    path('stock-csv/', views.stock_csv, name='stock_csv'),
    path('record/', views.record, name='record'),
    path('overview/', views.overview, name='overview'),
]