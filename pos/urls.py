"""pos/urls.py"""

from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('',                          views.dashboard,    name='dashboard'),
    path('terminal/',                 views.pos_terminal, name='terminal'),
    path('process/',                  views.process_sale, name='process_sale'),
    path('receipt/<int:pk>/',         views.receipt_view, name='receipt'),
    path('sales/',                    views.sale_list,    name='sale_list'),
    path('sales/<int:pk>/',           views.sale_detail,  name='sale_detail'),
    path('sales/<int:pk>/void/',      views.void_sale,    name='void_sale'),
]
