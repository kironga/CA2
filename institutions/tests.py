from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from institutions.models import CertificateRecord, Institution, InstitutionProfile


class InstitutionModuleTests(TestCase):
    def setUp(self):
        self.institution = Institution.objects.create(name="University A", code="UNI-A")
        self.inst_user = User.objects.create_user(
            email="inst@example.com",
            username="instadmin",
            password="StrongPass!123",
            role=User.Role.INSTITUTION_ADMIN,
        )
        InstitutionProfile.objects.create(user=self.inst_user, institution=self.institution)

        self.other_user = User.objects.create_user(
            email="hr@example.com",
            username="hruser",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
        )

    def test_institution_admin_can_create_certificate(self):
        self.client.force_login(self.inst_user)
        payload = {
            "national_id": "12345678",
            "full_name": "Jane Doe",
            "certificate_name": "Bachelor of Science",
            "award_level": "Degree",
            "grade": "Second Class Upper",
            "graduation_year": "2024",
            "registration_number": "REG123",
        }
        response = self.client.post(reverse("institution_certificate_add"), payload)
        self.assertRedirects(response, reverse("institution_certificates"))
        self.assertEqual(CertificateRecord.objects.count(), 1)

    def test_non_institution_user_blocked(self):
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("institution_certificates"))
        self.assertRedirects(
            response, f"{reverse('login')}?portal=institution&next={reverse('institution_certificates')}"
        )
        self.assertNotIn("_auth_user_id", self.client.session)
