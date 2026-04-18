from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import Business, HRProfile, User
from citizens.models import CitizenProfile
from institutions.models import CertificateRecord, Institution
from verification.models import OTPRequest, VerificationAccessLog
from verification.services import create_otp_request


class CitizenProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="citizen@example.com",
            username="citizen",
            password="StrongPass!123",
            role=User.Role.CITIZEN,
        )
        CitizenProfile.objects.create(user=self.user, national_id="11122233", otp_email="citizen@example.com")

    def test_citizen_profile_page_accessible(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("citizen_profile"))
        self.assertEqual(response.status_code, 200)

    def test_citizen_can_view_education_details(self):
        institution = Institution.objects.create(name="Uni Test", code="UNITEST")
        CertificateRecord.objects.create(
            national_id="11122233",
            full_name="Citizen Test",
            institution=institution,
            certificate_name="BSc Computer Science",
            award_level="Degree",
            grade="First Class",
            graduation_year=2024,
            registration_number="R-22",
            created_by=self.user,
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("citizen_education_details"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BSc Computer Science")

    def test_citizen_can_view_access_history(self):
        business = Business.objects.create(name="Talent Co", code="TALENT")
        hr_user = User.objects.create_user(
            email="hrhist@example.com",
            username="hrhist",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
        )
        HRProfile.objects.create(user=hr_user, business=business)
        otp_request = OTPRequest.objects.create(
            national_id="11122233",
            citizen=self.user.citizen_profile,
            requested_by=hr_user,
            otp_hash="hashed",
            expires_at=timezone.now(),
        )
        VerificationAccessLog.objects.create(
            citizen=self.user.citizen_profile,
            hr_user=hr_user,
            business=business,
            otp_request=otp_request,
            national_id="11122233",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("citizen_access_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Talent Co")

    def test_citizen_can_view_active_otp_preview(self):
        hr_user = User.objects.create_user(
            email="hrotp@example.com",
            username="hr_otp",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
        )
        create_otp_request(self.user.citizen_profile, hr_user, "11122233")
        self.client.force_login(self.user)
        response = self.client.get(reverse("citizen_otp_center"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current OTP")

    def test_citizen_can_upload_passport_photo(self):
        self.client.force_login(self.user)
        upload = SimpleUploadedFile("passport.jpg", b"fake-image-bytes", content_type="image/jpeg")
        payload = {
            "first_name": "Citizen",
            "last_name": "User",
            "national_id": "11122233",
            "otp_email": "citizen@example.com",
            "passport_photo": upload,
        }
        response = self.client.post(reverse("citizen_profile"), payload)
        self.assertEqual(response.status_code, 200)
        profile = CitizenProfile.objects.get(user=self.user)
        self.assertTrue(bool(profile.passport_photo))
