from django.conf import settings
from django.db import models


class JobAlert(models.Model):
    title = models.CharField(max_length=200)
    organization = models.CharField(max_length=200)
    location = models.CharField(max_length=120, blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    description = models.TextField()
    more_info_url = models.URLField(blank=True)
    application_url = models.URLField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_job_alerts"
    )
    recipients_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.title} - {self.organization}"


class JobAlertDelivery(models.Model):
    alert = models.ForeignKey(JobAlert, on_delete=models.CASCADE, related_name="deliveries")
    citizen = models.ForeignKey("citizens.CitizenProfile", on_delete=models.CASCADE, related_name="job_alert_deliveries")
    email = models.EmailField()
    status = models.CharField(max_length=20, default="sent")
    error_message = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-sent_at",)
