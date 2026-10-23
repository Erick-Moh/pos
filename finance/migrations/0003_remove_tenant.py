from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(name='dailysummary', unique_together=set()),
        migrations.AlterUniqueTogether(name='monthlysummary', unique_together=set()),
        migrations.RemoveField(model_name='dailysummary', name='tenant'),
        migrations.RemoveField(model_name='monthlysummary', name='tenant'),
        migrations.AlterUniqueTogether(
            name='dailysummary',
            unique_together={('date',)},
        ),
        migrations.AlterUniqueTogether(
            name='monthlysummary',
            unique_together={('year', 'month')},
        ),
    ]
