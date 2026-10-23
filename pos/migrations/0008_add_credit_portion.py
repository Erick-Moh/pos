"""pos/migrations/0008_add_credit_portion.py"""

from django.db import migrations, models
import decimal


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0007_add_credit_repayment'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='credit_portion',
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal('0'),
                help_text='Amount deferred to credit (0 = no credit component on this sale).',
                max_digits=14,
            ),
        ),
    ]
