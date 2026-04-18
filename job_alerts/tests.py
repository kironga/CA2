from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from citizens.models import CitizenProfile
from job_alerts.models import JobAlert


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class JobAlertTests(TestCase):
    def setUp(self):
        self.hr_user = User.objects.create_user(
            email="hr@example.com",
            username="hr_user",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
        )
        self.citizen_user = User.objects.create_user(
            email="citizen@example.com",
            username="citizen_user",
            password="StrongPass!123",
            role=User.Role.CITIZEN,
        )
        CitizenProfile.objects.create(user=self.citizen_user, national_id="78945612", otp_email="citizen@example.com")

    def test_hr_can_create_and_send_job_alert(self):
        self.client.force_login(self.hr_user)
        payload = {
            "title": "Graduate Trainee Program",
            "organization": "Public Service Commission",
            "location": "Nairobi",
            "description": "Open to degree holders.",
            "more_info_url": "https://example.com/info",
            "application_url": "https://example.com/apply",
        }
        response = self.client.post(reverse("job_alert_create"), payload)
        self.assertRedirects(response, reverse("job_alert_list"))
        self.assertEqual(JobAlert.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        alert = JobAlert.objects.first()
        self.assertEqual(alert.more_info_url, "https://example.com/info")
        self.assertEqual(alert.application_url, "https://example.com/apply")

    def test_citizen_can_view_job_alerts(self):
        JobAlert.objects.create(
            title="Analyst Role",
            organization="KNEC",
            description="Entry-level role",
            more_info_url="https://example.com/role",
            application_url="https://example.com/apply-role",
            created_by=self.hr_user,
        )
        self.client.force_login(self.citizen_user)
        response = self.client.get(reverse("citizen_job_alerts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "More Info")
        self.assertContains(response, "Apply")
