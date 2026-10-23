"""users/urls.py"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('change-credentials/', views.change_credentials, name='change_credentials'),
    path('profile/',            views.profile_view,       name='profile'),
    path('manage/',             views.user_list,          name='user_list'),
    path('manage/create/',      views.user_create,        name='user_create'),
    path('manage/<int:pk>/edit/',   views.user_edit,          name='user_edit'),
    path('manage/<int:pk>/toggle/', views.user_toggle_active, name='user_toggle_active'),
]
