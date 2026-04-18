from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator


class CitizenProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="citizen_profile")
    national_id = models.CharField(max_length=20, unique=True)
    otp_email = models.EmailField(unique=True)
    passport_photo = models.FileField(
        upload_to="passport_photos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.national_id} - {self.user.get_full_name() or self.user.email}"
