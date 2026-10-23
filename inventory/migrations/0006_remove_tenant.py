from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_product_buying_price_optional_product_track_stock'),
    ]

    operations = [
        # Remove unique_together that includes tenant before removing the field
        migrations.AlterUniqueTogether(
            name='category',
            unique_together=set(),
        ),
        migrations.RemoveField(model_name='category', name='tenant'),
        migrations.RemoveField(model_name='supplier', name='tenant'),
        migrations.RemoveField(model_name='product', name='tenant'),
        migrations.RemoveField(model_name='stockmovement', name='tenant'),
        # Restore unique_together without tenant
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('name',)},
        ),
    ]
