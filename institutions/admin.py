from django.contrib import admin

from institutions.models import CertificateRecord, Institution, InstitutionProfile


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_exam_body")
    search_fields = ("name", "code")


@admin.register(InstitutionProfile)
class InstitutionProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "institution")
    search_fields = ("user__email", "institution__name", "institution__code")


@admin.register(CertificateRecord)
class CertificateRecordAdmin(admin.ModelAdmin):
    list_display = ("national_id", "full_name", "certificate_name", "institution", "graduation_year")
    search_fields = ("national_id", "full_name", "certificate_name", "institution__name")
    list_filter = ("institution", "graduation_year")
