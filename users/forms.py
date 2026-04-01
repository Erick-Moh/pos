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
    """
    Admin form for creating a new user.

    The form dynamically validates credentials based on the selected role:
      - cashier / waiter  → raw_pin required (4 digits)
      - admin  / manager  → password + confirm_password required (strong)
    """

    raw_pin = forms.CharField(
        required=False,
        label='PIN',
        min_length=4,
        max_length=4,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Enter 4  digit PIN',
                'maxlength': '4',
                'inputmode': 'numeric',
                'pattern': '[0-9]{4}',
                'autocomplete': 'new-password',
                'id': 'id_raw_pin',
            }
        ),
        help_text='Numeric only, 4 digits. Used for fast floor login.',
    )
    confirm_pin = forms.CharField(
        required=False,
        label='Confirm PIN',
        max_length=4,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Repeat PIN',
                'maxlength': '4',
                'inputmode': 'numeric',
                'autocomplete': 'new-password',
                'id': 'id_confirm_pin',
            }
        ),
    )
    password = forms.CharField(
        required=False,
        label='Password',
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Minimum 8 characters',
                'autocomplete': 'new-password',
                'id': 'id_password',
            }
        ),
        help_text='Min 8 characters. Must include letters and at least one number.',
    )
    confirm_password = forms.CharField(
        required=False,
        label='Confirm Password',
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Repeat password',
                'autocomplete': 'new-password',
                'id': 'id_confirm_password',
            }
        ),
    )

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

    def clean_raw_pin(self):
        pin = self.cleaned_data.get('raw_pin', '').strip()
        if pin:
            if not pin.isdigit():
                raise ValidationError('PIN must contain numbers only.')
            if not (4 <= len(pin) <= 6):
                raise ValidationError('PIN must be between 4 and 6 digits.')
        return pin

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if password:
            if len(password) < 8:
                raise ValidationError('Password must be at least 8 characters.')
            if not any(c.isalpha() for c in password):
                raise ValidationError('Password must contain at least one letter.')
            if not any(c.isdigit() for c in password):
                raise ValidationError('Password must contain at least one number.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        raw_pin = cleaned_data.get('raw_pin', '').strip()
        confirm_pin = cleaned_data.get('confirm_pin', '').strip()
        password = cleaned_data.get('password', '')
        confirm_password = cleaned_data.get('confirm_password', '')

        if role in PIN_ROLES:
            if not raw_pin:
                self.add_error('raw_pin', 'PIN is required for cashier and waiter roles.')
            elif raw_pin != confirm_pin:
                self.add_error('confirm_pin', 'PINs do not match.')
        elif role in PASSWORD_ROLES:
            if not password:
                self.add_error('password', 'Password is required for admin and manager roles.')
            elif password != confirm_password:
                self.add_error('confirm_password', 'Passwords do not match.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        pin = self.cleaned_data.get('raw_pin', '').strip()
        pwd = self.cleaned_data.get('password', '')

        if role in PASSWORD_ROLES and pwd:
            user.set_password(pwd)
            if role == 'admin':
                user.is_staff = True
        elif role in PIN_ROLES and pin:
            user.set_unusable_password()
            user.set_pin(pin)

        user.must_change_credentials = True

        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """
    Admin form for editing an existing user.
    Credential fields are optional — leave blank to keep the current credential.
    """

    new_pin = forms.CharField(
        required=False,
        label='New PIN',
        max_length=4,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank to keep current PIN',
                'maxlength': '4',
                'inputmode': 'numeric',
                'autocomplete': 'new-password',
                'id': 'id_new_pin',
            }
        ),
        help_text='4 digits. Leave blank to keep the existing PIN.',
    )
    confirm_new_pin = forms.CharField(
        required=False,
        label='Confirm New PIN',
        max_length=4,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Repeat new PIN',
                'maxlength': '4',
                'inputmode': 'numeric',
                'autocomplete': 'new-password',
                'id': 'id_confirm_new_pin',
            }
        ),
    )
    new_password = forms.CharField(
        required=False,
        label='New Password',
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Leave blank to keep current password',
                'autocomplete': 'new-password',
                'id': 'id_new_password',
            }
        ),
        help_text='Min 8 characters with letters and numbers. Leave blank to keep existing.',
    )
    confirm_new_password = forms.CharField(
        required=False,
        label='Confirm New Password',
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Repeat new password',
                'autocomplete': 'new-password',
                'id': 'id_confirm_new_password',
            }
        ),
    )

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

    def clean_new_pin(self):
        pin = self.cleaned_data.get('new_pin', '').strip()
        if pin:
            if not pin.isdigit():
                raise ValidationError('PIN must contain numbers only.')
            if len(pin) != 4:
                raise ValidationError('PIN must be exactly 4 digits.')
        return pin

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password', '')
        if password:
            if len(password) < 8:
                raise ValidationError('Password must be at least 8 characters.')
            if not any(c.isalpha() for c in password):
                raise ValidationError('Password must contain at least one letter.')
            if not any(c.isdigit() for c in password):
                raise ValidationError('Password must contain at least one number.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        new_pin = cleaned_data.get('new_pin', '').strip()
        confirm_new_pin = cleaned_data.get('confirm_new_pin', '').strip()
        new_password = cleaned_data.get('new_password', '')
        confirm_new_password = cleaned_data.get('confirm_new_password', '')

        if role in PIN_ROLES:
            if new_pin and new_pin != confirm_new_pin:
                self.add_error('confirm_new_pin', 'PINs do not match.')
        elif role in PASSWORD_ROLES:
            if new_password and new_password != confirm_new_password:
                self.add_error('confirm_new_password', 'Passwords do not match.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        new_pin = self.cleaned_data.get('new_pin', '').strip()
        new_pwd = self.cleaned_data.get('new_password', '')
        
        if role in PASSWORD_ROLES:
            if new_pwd:
                user.set_password(new_pwd)
            user.is_staff = (role == 'admin')
        elif role in PIN_ROLES and new_pin:
            user.set_unusable_password()
            user.set_pin(new_pin)

        if commit:
            user.save()
        return user
