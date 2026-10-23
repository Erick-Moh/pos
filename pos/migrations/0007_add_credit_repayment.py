"""pos/migrations/0007_add_credit_repayment.py"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0006_remove_tenant'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CreditRepayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('payment_method', models.CharField(
                    choices=[('cash', 'Cash'), ('mpesa', 'M-Pesa'), ('card', 'Credit / Debit Card')],
                    default='cash', max_length=20,
                )),
                ('reference', models.CharField(blank=True, max_length=100, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('recorded_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='credit_repayments_recorded',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('sale', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='repayments',
                    to='pos.sale',
                )),
            ],
            options={
                'verbose_name': 'Credit Repayment',
                'verbose_name_plural': 'Credit Repayments',
                'ordering': ['recorded_at'],
            },
        ),
    ]
