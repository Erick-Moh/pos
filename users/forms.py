"""
users/forms.py
Authentication and user management forms for GetCore ERP.

Two distinct login types:
  - Floor staff  (cashier / waiter)   → Username + 4-digit PIN
  - Back office  (admin  / manager)   → Username + Strong Password (min 8 chars,
                                        must contain letters AND numbers)
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

PIN_ROLES = ('cashier', 'waiter')
PASSWORD_ROLES = ('admin', 'manager')


class StaffPinLoginForm(forms.Form):
    """Floor staff login: Username + 4-digit numeric PIN."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Staff Username',
                'autofocus': True,
                'autocomplete': 'username',
            }
        ),
    )
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg text-center',
                'placeholder': '● ● ● ●',
                'maxlength': '4',
                'inputmode': 'numeric',
                'pattern': '[0-9]{4}',
                'autocomplete': 'off',
            }
        ),
        label='PIN',
    )

    def clean_pin(self):
        pin = self.cleaned_data.get('pin', '').strip()
        if not pin.isdigit():
            raise ValidationError('PIN must contain numbers only.')
        if not len(pin) == 4:
            raise ValidationError('PIN must be exactly 4 digits.')
        return pin


class AdminPasswordLoginForm(forms.Form):
    """Back-office login: Username + strong password."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Admin Username',
                'autofocus': True,
                'autocomplete': 'username',
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Password',
                'autocomplete': 'current-password',
            }
        ),
    )


class UserCreateForm(forms.ModelForm):    
    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'phone_number',
            'is_active',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_role'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class UserEditForm(forms.ModelForm):    
    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'phone_number',
            'is_active',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select select2', 'id': 'id_role'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    