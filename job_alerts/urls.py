from django.urls import path

from job_alerts.views import citizen_job_alerts, job_alert_create, job_alert_list

urlpatterns = [
    path("", job_alert_list, name="job_alert_list"),
    path("new/", job_alert_create, name="job_alert_create"),
    path("citizen/", citizen_job_alerts, name="citizen_job_alerts"),
]
