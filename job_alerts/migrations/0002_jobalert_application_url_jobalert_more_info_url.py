from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job_alerts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobalert',
            name='application_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='jobalert',
            name='more_info_url',
            field=models.URLField(blank=True),
        ),
    ]
