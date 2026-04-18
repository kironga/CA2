import re
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from citizens.models import CitizenProfile
from verification.models import OTPRequest, VerificationAccessLog
from verification.services import (
    can_request_otp,
    create_otp_request,
    get_citizen_otp_preview,
    send_otp_email,
    validate_otp,
)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class OTPFlowTests(TestCase):
    def setUp(self):
        self.hr_user = User.objects.create_user(
            email="hr@example.com",
            username="hruser",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
        )
        self.citizen_user = User.objects.create_user(
            email="citizen@example.com",
            username="citizen",
            password="StrongPass!123",
            role=User.Role.CITIZEN,
        )
        self.citizen = CitizenProfile.objects.create(
            user=self.citizen_user,
            national_id="98765432",
            otp_email="citizen@example.com",
        )

    def test_generate_and_validate_otp(self):
        otp_request, otp = create_otp_request(self.citizen, self.hr_user, self.citizen.national_id)
        self.assertIsNotNone(get_citizen_otp_preview(self.citizen))
        is_valid, _ = validate_otp(otp_request, otp)
        self.assertTrue(is_valid)
        otp_request.refresh_from_db()
        self.assertTrue(otp_request.is_used)
        self.assertIsNone(get_citizen_otp_preview(self.citizen))

    def test_send_otp_email(self):
        _, otp = create_otp_request(self.citizen, self.hr_user, self.citizen.national_id)
        send_otp_email(self.citizen, otp, self.citizen.national_id)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("credential verification OTP", mail.outbox[0].subject)

    def test_hr_verification_http_flow(self):
        self.client.force_login(self.hr_user)
        response = self.client.post(reverse("request_otp"), {"national_id": self.citizen.national_id})
        self.assertRedirects(response, reverse("verify_otp"))
        self.assertTrue(OTPRequest.objects.exists())

        latest_email = mail.outbox[-1].body
        match = re.search(r"OTP\) is: (\d{6})", latest_email)
        self.assertIsNotNone(match)
        otp = match.group(1)
        response = self.client.post(reverse("verify_otp"), {"otp": otp})
        self.assertRedirects(response, reverse("verified_records"))
        self.assertEqual(VerificationAccessLog.objects.filter(citizen=self.citizen).count(), 1)

    def test_otp_request_cooldown(self):
        create_otp_request(self.citizen, self.hr_user, self.citizen.national_id)
        allowed, reason = can_request_otp(self.citizen, self.hr_user)
        self.assertFalse(allowed)
        self.assertIn("Wait one minute", reason)

    @patch("verification.views.send_otp_email", side_effect=Exception("SMTP unavailable"))
    def test_request_otp_send_failure_does_not_leave_stale_otp(self, _mock_send):
        self.client.force_login(self.hr_user)
        response = self.client.post(
            reverse("request_otp"),
            {"national_id": self.citizen.national_id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not send OTP email right now")
        self.assertEqual(OTPRequest.objects.count(), 0)
        self.assertIsNone(get_citizen_otp_preview(self.citizen))
