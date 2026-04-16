"""pos/urls.py"""

from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('',                                    views.dashboard,         name='dashboard'),
    path('terminal/',                           views.pos_terminal,      name='terminal'),
    path('process/',                            views.process_sale,      name='process_sale'),
    path('receipt/<int:pk>/',                   views.receipt_view,      name='receipt'),
    path('sales/',                              views.sale_list,         name='sale_list'),
    path('sales/<int:pk>/',                     views.sale_detail,       name='sale_detail'),
    path('sales/<int:pk>/void/',               views.void_sale,         name='void_sale'),

    # ── Customer Management ───────────────────────────────────────────────
    path('customers/',                          views.customer_list,     name='customer_list'),
    path('customers/new/',                      views.customer_create,   name='customer_create'),
    path('customers/<int:pk>/edit/',            views.customer_edit,     name='customer_edit'),

    # ── Credit Sales ──────────────────────────────────────────────────────
    path('credits/',                            views.credit_sales_list, name='credit_sales_list'),
    path('credits/<int:pk>/paid/',              views.mark_credit_paid,  name='mark_credit_paid'),
]
