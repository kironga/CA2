from django.conf import settings
from django.db import models
from django.utils import timezone


class OTPRequest(models.Model):
    national_id = models.CharField(max_length=20, db_index=True)
    citizen = models.ForeignKey("citizens.CitizenProfile", on_delete=models.CASCADE, related_name="otp_requests")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="otp_requests"
    )
    otp_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP for {self.national_id} ({self.created_at:%Y-%m-%d %H:%M})"


class VerificationAccessLog(models.Model):
    class Source(models.TextChoices):
        WEB = "WEB", "Web"
        API = "API", "API"

    citizen = models.ForeignKey("citizens.CitizenProfile", on_delete=models.CASCADE, related_name="verification_accesses")
    hr_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verification_accesses"
    )
    business = models.ForeignKey(
        "accounts.Business",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verification_accesses",
    )
    otp_request = models.ForeignKey(
        "verification.OTPRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
    )
    national_id = models.CharField(max_length=20, db_index=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.WEB)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-accessed_at",)

    def __str__(self):
        return f"{self.national_id} viewed at {self.accessed_at:%Y-%m-%d %H:%M}"
