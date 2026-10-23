"""settings_app/forms.py"""

import re

from django import forms
from django.core.exceptions import ValidationError

from .models import SystemSetting

TEMPLATE_MARKER_RE = re.compile(r'({{|{%|}}|%})')


def clean_plain_text(value):
    if value is None:
        return value
    value = value.strip()
    if not value:
        return value
    if '<' in value or '>' in value:
        raise ValidationError('Text fields may not contain HTML or markup characters.')
    if TEMPLATE_MARKER_RE.search(value):
        raise ValidationError('Text fields may not contain template markers.')
    return value


class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        exclude = ['updated_at']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'physical_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'county': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'kra_pin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'P0000000000A'}),
            'vat_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'enable_etims': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'dark_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'currency_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'KES'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'KSh'}),
            'receipt_footer_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'show_vat_on_receipt': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_contact_phone(self):
        phone = self.cleaned_data.get('contact_phone', '') or ''
        phone = phone.strip()
        if not phone:
            return phone
        normalized = phone.lstrip('+').strip()
        if not normalized.isdigit():
            raise ValidationError('Phone number must contain digits only, with an optional leading +.')
        return normalized

    def clean_business_name(self):
        return clean_plain_text(self.cleaned_data.get('business_name'))

    def clean_business_tagline(self):
        return clean_plain_text(self.cleaned_data.get('business_tagline'))

    def clean_physical_address(self):
        return clean_plain_text(self.cleaned_data.get('physical_address'))

    def clean_county(self):
        return clean_plain_text(self.cleaned_data.get('county'))

    def clean_country(self):
        return clean_plain_text(self.cleaned_data.get('country'))

    def clean_currency_code(self):
        return clean_plain_text(self.cleaned_data.get('currency_code'))

    def clean_currency_symbol(self):
        return clean_plain_text(self.cleaned_data.get('currency_symbol'))

    def clean_receipt_footer_text(self):
        return clean_plain_text(self.cleaned_data.get('receipt_footer_text'))
