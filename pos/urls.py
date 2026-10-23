"""pos/urls.py"""

from django.urls import path
from . import views
from . import print_api

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
    path('customers/<int:pk>/',                 views.customer_detail,   name='customer_detail'),
    path('customers/<int:pk>/edit/',            views.customer_edit,     name='customer_edit'),
    path('customers/<int:pk>/delete/',          views.customer_delete,   name='customer_delete'),

    # ── Credit Sales ──────────────────────────────────────────────────────
    path('credits/',                            views.credit_sales_list,       name='credit_sales_list'),
    path('credits/customers/',                  views.customer_credit_summary, name='customer_credit_summary'),
    path('credits/<int:pk>/repay/',             views.record_repayment,        name='record_repayment'),

    # ── Internal API (AJAX, login-required) ──────────────────────────────
    path('api/credit-check/',                   views.credit_check,      name='credit_check'),

    # ── Print Agent API (token-auth, no session) ──────────────────────────
    path('api/print/heartbeat/',                print_api.heartbeat,      name='print_heartbeat'),
    path('api/print/jobs/',                     print_api.poll_jobs,      name='print_poll_jobs'),
    path('api/print/jobs/<int:job_id>/ack/',    print_api.job_ack,        name='print_job_ack'),
    path('api/print/jobs/<int:job_id>/done/',   print_api.job_done,       name='print_job_done'),
    path('api/print/jobs/<int:job_id>/fail/',   print_api.job_fail,       name='print_job_fail'),
    path('api/print/device/<int:device_id>/status/', print_api.device_status, name='print_device_status'),
]
