"""platform/forms.py — Forms for the GetCore platform workspace."""

from django import forms
from django.contrib.auth import get_user_model
from tenants.models import Tenant

User = get_user_model()


class PlatformLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Staff username',
            'autofocus': True,
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        })
    )


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = [
            'name', 'slug', 'owner_name', 'owner_email', 'owner_phone',
            'plan', 'is_active', 'trial_ends_on',
        ]
        widgets = {
            'name':          forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kamau Agrovet Nakuru'}),
            'slug':          forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'kamau-agrovet-nakuru'}),
            'owner_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'owner_email':   forms.EmailInput(attrs={'class': 'form-control'}),
            'owner_phone':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254...'}),
            'plan':          forms.Select(attrs={'class': 'form-select select2'}),
            'is_active':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'trial_ends_on': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class PlatformUserForm(forms.ModelForm):
    """Create / edit a platform staff account."""
    password = forms.CharField(
        required=False,
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave blank to keep existing',
            'autocomplete': 'new-password',
        }),
        help_text='Min 8 characters. Leave blank when editing to keep current password.'
    )
    confirm_password = forms.CharField(
        required=False,
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password',
            'autocomplete': 'new-password',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_superuser']
        widgets = {
            'username':     forms.TextInput(attrs={'class': 'form-control'}),
            'first_name':   forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'email':        forms.EmailInput(attrs={'class': 'form-control'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        data = super().clean()
        pwd  = data.get('password', '')
        cpwd = data.get('confirm_password', '')
        if pwd:
            if len(pwd) < 8:
                self.add_error('password', 'Password must be at least 8 characters.')
            elif pwd != cpwd:
                self.add_error('confirm_password', 'Passwords do not match.')
        return data
