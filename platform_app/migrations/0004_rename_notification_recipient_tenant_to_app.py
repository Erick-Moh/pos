"""
Rename the notification recipient value 'tenant' → 'app' in existing rows,
and update the CharField choices.
"""

from django.db import migrations, models


def rename_recipient(apps, schema_editor):
    Notification = apps.get_model('platform_app', 'Notification')
    Notification.objects.filter(recipient='tenant').update(recipient='app')


def reverse_rename_recipient(apps, schema_editor):
    Notification = apps.get_model('platform_app', 'Notification')
    Notification.objects.filter(recipient='app').update(recipient='tenant')


class Migration(migrations.Migration):

    dependencies = [
        ('platform_app', '0003_remove_tenant_payment_remove_notification_tenant'),
    ]

    operations = [
        migrations.RunPython(rename_recipient, reverse_code=reverse_rename_recipient),
        migrations.AlterField(
            model_name='notification',
            name='recipient',
            field=models.CharField(
                max_length=20,
                choices=[('app', 'Application'), ('platform', 'Platform Admin')],
                default='app',
            ),
        ),
    ]
