from django.urls import path

from verification.views import request_otp, verified_records, verify_otp_view

urlpatterns = [
    path("request-otp/", request_otp, name="request_otp"),
    path("verify-otp/", verify_otp_view, name="verify_otp"),
    path("records/", verified_records, name="verified_records"),
]
