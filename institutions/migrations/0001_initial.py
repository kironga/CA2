import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Institution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('code', models.CharField(max_length=30, unique=True)),
                ('is_exam_body', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='InstitutionProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admins', to='institutions.institution')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='institution_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CertificateRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('national_id', models.CharField(db_index=True, max_length=20)),
                ('full_name', models.CharField(max_length=255)),
                ('certificate_name', models.CharField(max_length=255)),
                ('award_level', models.CharField(max_length=120)),
                ('grade', models.CharField(blank=True, max_length=60)),
                ('graduation_year', models.PositiveIntegerField()),
                ('registration_number', models.CharField(blank=True, max_length=120)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_certificates', to=settings.AUTH_USER_MODEL)),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='records', to='institutions.institution')),
            ],
            options={
                'ordering': ('-graduation_year', '-created_at'),
                'unique_together': {('national_id', 'institution', 'certificate_name', 'graduation_year')},
            },
        ),
    ]
