"""inventory/urls.py"""

from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('add/', views.product_create, name='product_create'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('adjust/', views.stock_adjustment, name='stock_adjustment'),
    path('adjust/<int:pk>/delete/', views.stock_adjustment_delete, name='stock_adjustment_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),
    path('load-default-categories/', views.load_default_categories, name='load_default_categories'),
    path('stock-movement/<int:pk>/delete/', views.stock_adjustment_delete, name='stock_adjustment_delete'),
    path('load-default-products/', views.load_default_products, name='load_default_products'),
]
