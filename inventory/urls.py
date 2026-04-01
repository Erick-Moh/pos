"""inventory/urls.py"""

from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('',                              views.product_list,        name='product_list'),
    path('add/',                          views.product_create,      name='product_create'),
    path('<int:pk>/',                     views.product_detail,      name='product_detail'),
    path('<int:pk>/edit/',                views.product_edit,        name='product_edit'),
    path('adjust/',                       views.stock_adjustment,    name='stock_adjustment'),
    path('categories/',                   views.category_list,       name='category_list'),
    path('categories/add/',               views.category_create,     name='category_create'),
    path('suppliers/',                    views.supplier_list,       name='supplier_list'),
    path('suppliers/add/',                views.supplier_create,     name='supplier_create'),
    path('suppliers/<int:pk>/edit/',      views.supplier_edit,       name='supplier_edit'),
    path('api/products/',                 views.product_search_api,  name='product_search_api'),
]
