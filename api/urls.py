from django.urls import path

from api.views import (
    hr_request_otp_api,
    hr_verify_otp_api,
    institution_certificate_create,
    institution_certificates_list,
)

urlpatterns = [
    path("institutions/certificates/", institution_certificates_list, name="api_institution_certificates_list"),
    path("institutions/certificates/create/", institution_certificate_create, name="api_institution_certificate_create"),
    path("hr/request-otp/", hr_request_otp_api, name="api_hr_request_otp"),
    path("hr/verify-otp/", hr_verify_otp_api, name="api_hr_verify_otp"),
]
