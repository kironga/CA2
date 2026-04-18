from django.contrib import admin

from job_alerts.models import JobAlert, JobAlertDelivery


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "created_by", "recipients_count", "created_at")
    search_fields = ("title", "organization", "created_by__email")


@admin.register(JobAlertDelivery)
class JobAlertDeliveryAdmin(admin.ModelAdmin):
    list_display = ("alert", "citizen", "email", "status", "sent_at")
    search_fields = ("alert__title", "citizen__national_id", "email")
    list_filter = ("status", "sent_at")
