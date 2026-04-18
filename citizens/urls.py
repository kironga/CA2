from django.urls import path

from citizens.views import citizen_access_history, citizen_education_details, citizen_otp_center, citizen_profile

urlpatterns = [
    path("profile/", citizen_profile, name="citizen_profile"),
    path("education/", citizen_education_details, name="citizen_education_details"),
    path("access-history/", citizen_access_history, name="citizen_access_history"),
    path("otp-center/", citizen_otp_center, name="citizen_otp_center"),
]
