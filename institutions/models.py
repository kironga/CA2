from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator


class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=30, unique=True)
    is_exam_body = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class InstitutionProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="institution_profile")
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="admins")

    def __str__(self):
        return f"{self.user.email} -> {self.institution.code}"


class CertificateRecord(models.Model):
    national_id = models.CharField(max_length=20, db_index=True)
    full_name = models.CharField(max_length=255)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="records")
    certificate_name = models.CharField(max_length=255)
    award_level = models.CharField(max_length=120)
    grade = models.CharField(max_length=60, blank=True)
    graduation_year = models.PositiveIntegerField()
    registration_number = models.CharField(max_length=120, blank=True)
    certificate_file = models.FileField(
        upload_to="certificates/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["pdf"])],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_certificates"
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-graduation_year", "-created_at")
        unique_together = ("national_id", "institution", "certificate_name", "graduation_year")

    def __str__(self):
        return f"{self.national_id} - {self.certificate_name} ({self.graduation_year})"
