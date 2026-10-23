from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('platform_app', '0002_add_tenant_payment'),
    ]

    operations = [
        # Drop TenantPayment entirely
        migrations.DeleteModel(name='TenantPayment'),
        # Remove index that included tenant, then remove the field
        migrations.RemoveIndex(
            model_name='notification',
            name='platform_ap_tenant__eec55d_idx',
        ),
        migrations.RemoveField(model_name='notification', name='tenant'),
        # Add clean index without tenant
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'is_read'], name='notif_recipient_read_idx'),
        ),
    ]
