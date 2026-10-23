from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('settings_app', '0002_alter_systemsetting_business_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='systemsetting',
            name='tenant',
        ),
    ]
