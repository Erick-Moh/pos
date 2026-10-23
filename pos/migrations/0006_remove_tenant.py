from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0005_add_print_device_job'),
    ]

    operations = [
        migrations.RemoveField(model_name='customer', name='tenant'),
        migrations.RemoveField(model_name='sale', name='tenant'),
        migrations.RemoveField(model_name='printdevice', name='tenant'),
        migrations.AlterModelOptions(
            name='printdevice',
            options={'ordering': ['name'], 'verbose_name': 'Print Device', 'verbose_name_plural': 'Print Devices'},
        ),
    ]
