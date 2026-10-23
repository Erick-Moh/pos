"""finance/migrations/0004_add_credit_repayments_received.py"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_remove_tenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailysummary',
            name='credit_repayments_received',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
    ]
