from django.urls import path

from institutions.views import (
    certificate_create,
    certificate_list,
    certificate_update,
    citizen_lookup,
    certificate_file_hr,
    certificate_file_citizen,
)

urlpatterns = [
    path("certificates/", certificate_list, name="institution_certificates"),
    path("certificates/add/", certificate_create, name="institution_certificate_add"),
    path("certificates/<int:pk>/edit/", certificate_update, name="institution_certificate_edit"),
    path("certificates/<int:pk>/file/hr/", certificate_file_hr, name="certificate_file_hr"),
    path("certificates/<int:pk>/file/citizen/", certificate_file_citizen, name="certificate_file_citizen"),
    path("citizens/lookup/", citizen_lookup, name="institution_citizen_lookup"),
]
