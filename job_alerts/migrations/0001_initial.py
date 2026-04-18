import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('citizens', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='JobAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('organization', models.CharField(max_length=200)),
                ('location', models.CharField(blank=True, max_length=120)),
                ('application_deadline', models.DateField(blank=True, null=True)),
                ('description', models.TextField()),
                ('recipients_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_job_alerts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='JobAlertDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254)),
                ('status', models.CharField(default='sent', max_length=20)),
                ('error_message', models.CharField(blank=True, max_length=255)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('alert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='job_alerts.jobalert')),
                ('citizen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='job_alert_deliveries', to='citizens.citizenprofile')),
            ],
            options={
                'ordering': ('-sent_at',),
            },
        ),
    ]
