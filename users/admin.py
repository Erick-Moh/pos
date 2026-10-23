"""users/admin.py"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import GetCoreUser, UserProfile


@admin.register(GetCoreUser)
class GetCoreUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'is_active', 'last_login']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['username']

    fieldsets = UserAdmin.fieldsets + (
        ('GetCore Fields', {
            'fields': ('role', 'hashed_pin', 'phone_number', 'profile_picture', 'is_active_shift', 'must_change_credentials'),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'assigned_terminal']
