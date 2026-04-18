from django.contrib import admin

from citizens.models import CitizenProfile


@admin.register(CitizenProfile)
class CitizenProfileAdmin(admin.ModelAdmin):
    list_display = ("national_id", "otp_email", "user", "updated_at")
    search_fields = ("national_id", "otp_email", "user__email")
