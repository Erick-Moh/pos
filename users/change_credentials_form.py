"""
Additional form for first-login credential change.
Added to users/forms.py via import — kept separate for clarity.
"""

from django import forms
from django.core.exceptions import ValidationError


class ChangeCredentialsForm(forms.Form):
    """
    Shown on first login. Lets the user set a new PIN (staff) or
    new password (admin/manager). Fields shown depend on role (handled in template/view).
    """

    # ── PIN fields (for cashier / waiter) ─────────────────────────────────
    new_pin = forms.CharField(
        required=False,
        min_length=4,
        max_length=4,
        label='New PIN',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new 4 digit PIN',
            'inputmode': 'numeric',
            'maxlength': '4',
            'autocomplete': 'new-password',
            'id': 'id_new_pin',
        }),
        help_text='4 digits, numbers only.'
    )
    confirm_pin = forms.CharField(
        required=False,
        max_length=4,
        label='Confirm PIN',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat new PIN',
            'inputmode': 'numeric',
            'maxlength': '4',
            'autocomplete': 'new-password',
            'id': 'id_confirm_pin',
        }),
    )

    # ── Password fields (for admin / manager) ──────────────────────────────
    new_password = forms.CharField(
        required=False,
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min 8 characters with letters and numbers',
            'autocomplete': 'new-password',
            'id': 'id_new_password',
        }),
        help_text='At least 8 characters with letters and numbers.'
    )
    confirm_password = forms.CharField(
        required=False,
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat new password',
            'autocomplete': 'new-password',
            'id': 'id_confirm_password',
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        if not self.user:
            return cleaned_data

        role            = self.user.role
        new_pin         = cleaned_data.get('new_pin', '').strip()
        confirm_pin     = cleaned_data.get('confirm_pin', '').strip()
        new_password    = cleaned_data.get('new_password', '')
        confirm_pwd     = cleaned_data.get('confirm_password', '')

        if role in ('cashier', 'waiter'):
            if not new_pin:
                self.add_error('new_pin', 'Please enter a new PIN.')
            elif not new_pin.isdigit():
                self.add_error('new_pin', 'PIN must be numbers only.')
            elif len(new_pin) != 4:
                self.add_error('new_pin', 'PIN must be exactly 4 digits.')
            elif new_pin != confirm_pin:
                self.add_error('confirm_pin', 'PINs do not match.')

        elif role in ('admin', 'manager'):
            if not new_password:
                self.add_error('new_password', 'Please enter a new password.')
            elif len(new_password) < 8:
                self.add_error('new_password', 'Password must be at least 8 characters.')
            elif not any(c.isalpha() for c in new_password):
                self.add_error('new_password', 'Password must contain at least one letter.')
            elif not any(c.isdigit() for c in new_password):
                self.add_error('new_password', 'Password must contain at least one number.')
            elif new_password != confirm_pwd:
                self.add_error('confirm_password', 'Passwords do not match.')

        return cleaned_data

    def save(self):
        """Apply the new credentials and clear the must_change_credentials flag."""
        role        = self.user.role
        new_pin     = self.cleaned_data.get('new_pin', '').strip()
        new_password= self.cleaned_data.get('new_password', '')

        if role in ('cashier', 'waiter') and new_pin:
            self.user.set_unusable_password()
            self.user.set_pin(new_pin)
        elif role in ('admin', 'manager') and new_password:
            self.user.set_password(new_password)

        self.user.must_change_credentials = False
        self.user.save()
        return self.user
