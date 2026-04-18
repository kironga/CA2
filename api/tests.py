import json
import re

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from citizens.models import CitizenProfile
from institutions.models import Institution, InstitutionProfile
from verification.models import VerificationAccessLog


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class APITests(TestCase):
    def setUp(self):
        self.hr_user = User.objects.create_user(
            email="hr@example.com",
            username="hr",
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
            national_id="22233344",
            otp_email="citizen@example.com",
        )
        self.inst = Institution.objects.create(name="Tech University", code="TU01")
        self.inst_user = User.objects.create_user(
            email="inst@example.com",
            username="inst",
            password="StrongPass!123",
            role=User.Role.INSTITUTION_ADMIN,
        )
        InstitutionProfile.objects.create(user=self.inst_user, institution=self.inst)

    def test_institution_can_create_certificate_via_api(self):
        self.client.force_login(self.inst_user)
        payload = {
            "national_id": "22233344",
            "full_name": "Jane Doe",
            "certificate_name": "BSc IT",
            "award_level": "Degree",
            "grade": "First Class",
            "graduation_year": 2025,
            "registration_number": "R001",
        }
        response = self.client.post(
            reverse("api_institution_certificate_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_hr_otp_verify_api_returns_records(self):
        self.client.force_login(self.inst_user)
        cert_payload = {
            "national_id": self.citizen.national_id,
            "full_name": "Citizen User",
            "certificate_name": "Diploma in Stats",
            "award_level": "Diploma",
            "grade": "Credit",
            "graduation_year": 2024,
            "registration_number": "REG100",
        }
        self.client.post(
            reverse("api_institution_certificate_create"),
            data=json.dumps(cert_payload),
            content_type="application/json",
        )

        self.client.force_login(self.hr_user)
        response = self.client.post(
            reverse("api_hr_request_otp"),
            data=json.dumps({"national_id": self.citizen.national_id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        otp_request_id = response.json()["otp_request_id"]

        body = mail.outbox[-1].body
        otp = re.search(r"OTP\) is: (\d{6})", body).group(1)
        verify_response = self.client.post(
            reverse("api_hr_verify_otp"),
            data=json.dumps({"otp_request_id": otp_request_id, "otp": otp}),
            content_type="application/json",
        )
        self.assertEqual(verify_response.status_code, 200)
        self.assertEqual(len(verify_response.json()["records"]), 1)
        self.assertEqual(
            VerificationAccessLog.objects.filter(citizen=self.citizen, source=VerificationAccessLog.Source.API).count(),
            1,
        )
