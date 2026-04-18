import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citizens', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='citizenprofile',
            name='passport_photo',
            field=models.FileField(blank=True, null=True, upload_to='passport_photos/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])]),
        ),
    ]
