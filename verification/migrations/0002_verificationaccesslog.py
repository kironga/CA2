import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_business_hrprofile'),
        ('citizens', '0001_initial'),
        ('verification', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VerificationAccessLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('national_id', models.CharField(db_index=True, max_length=20)),
                ('source', models.CharField(choices=[('WEB', 'Web'), ('API', 'API')], default='WEB', max_length=10)),
                ('accessed_at', models.DateTimeField(auto_now_add=True)),
                ('business', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verification_accesses', to='accounts.business')),
                ('citizen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='verification_accesses', to='citizens.citizenprofile')),
                ('hr_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verification_accesses', to=settings.AUTH_USER_MODEL)),
                ('otp_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='access_logs', to='verification.otprequest')),
            ],
            options={
                'ordering': ('-accessed_at',),
            },
        ),
    ]
