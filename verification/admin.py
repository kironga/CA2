from django.contrib import admin

from verification.models import OTPRequest, VerificationAccessLog


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ("national_id", "citizen", "requested_by", "request_ip", "expires_at", "is_used", "attempts")
    search_fields = ("national_id", "citizen__user__email", "requested_by__email")
    list_filter = ("is_used", "created_at")


@admin.register(VerificationAccessLog)
class VerificationAccessLogAdmin(admin.ModelAdmin):
    list_display = ("national_id", "citizen", "business", "hr_user", "source", "accessed_at")
    search_fields = ("national_id", "citizen__user__email", "business__name", "hr_user__email")
    list_filter = ("source", "accessed_at")
