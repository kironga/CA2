from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Business, HRProfile, User
from citizens.models import CitizenProfile
from institutions.models import CertificateRecord, Institution, InstitutionProfile


class AuthAndRoleTests(TestCase):
    def test_citizen_registration_creates_profile(self):
        payload = {
            "email": "citizen1@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "national_id": "12345678",
            "otp_email": "citizen1@example.com",
            "password1": "StrongPass!123",
            "password2": "StrongPass!123",
        }
        response = self.client.post(reverse("citizen_register"), payload)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="citizen1@example.com")
        self.assertEqual(user.role, User.Role.CITIZEN)
        self.assertTrue(CitizenProfile.objects.filter(user=user, national_id="12345678").exists())

    def test_role_redirect_for_hr_manager(self):
        user = User.objects.create_user(
            email="hr@example.com",
            username="hruser",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("role_redirect"))
        self.assertRedirects(response, reverse("dashboard_hr"))


class GovernmentControlTests(TestCase):
    def setUp(self):
        self.gov_user = User.objects.create_user(
            email="gov@example.com",
            username="gov",
            password="StrongPass!123",
            role=User.Role.GOVERNMENT_ADMIN,
            is_staff=True,
        )
        self.hr_user = User.objects.create_user(
            email="otherhr@example.com",
            username="otherhr",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
        )

    def test_government_can_add_institution_with_admin_credentials(self):
        self.client.force_login(self.gov_user)
        payload = {
            "institution_name": "University Z",
            "institution_code": "UNI-Z",
            "is_exam_body": "",
            "admin_first_name": "Inst",
            "admin_last_name": "Admin",
            "admin_email": "instz@example.com",
            "admin_password1": "StrongPass!123",
            "admin_password2": "StrongPass!123",
        }
        response = self.client.post(reverse("government_institutions"), payload)
        self.assertRedirects(response, reverse("government_institutions"))
        institution = Institution.objects.get(code="UNI-Z")
        inst_admin = User.objects.get(email="instz@example.com")
        self.assertEqual(inst_admin.role, User.Role.INSTITUTION_ADMIN)
        self.assertTrue(InstitutionProfile.objects.filter(user=inst_admin, institution=institution).exists())

    def test_government_can_delete_business_and_disable_hr_accounts(self):
        business = Business.objects.create(name="Acme Corp", code="ACME")
        hr = User.objects.create_user(
            email="acmehr@example.com",
            username="acmehr",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
        )
        HRProfile.objects.create(user=hr, business=business)
        self.client.force_login(self.gov_user)
        response = self.client.post(reverse("government_business_delete", kwargs={"pk": business.pk}))
        self.assertRedirects(response, reverse("government_businesses"))
        hr.refresh_from_db()
        self.assertFalse(hr.is_active)
        self.assertFalse(Business.objects.filter(pk=business.pk).exists())

    def test_government_can_edit_institution_details(self):
        institution = Institution.objects.create(name="Original University", code="ORIG-U")
        inst_admin = User.objects.create_user(
            email="originst@example.com",
            username="originst",
            password="StrongPass!123",
            role=User.Role.INSTITUTION_ADMIN,
            first_name="Orig",
            last_name="Admin",
        )
        InstitutionProfile.objects.create(user=inst_admin, institution=institution)
        self.client.force_login(self.gov_user)
        payload = {
            "institution_name": "Updated University",
            "institution_code": "UPD-U",
            "is_exam_body": "on",
            "admin_first_name": "Updated",
            "admin_last_name": "Manager",
            "admin_email": "updatedinst@example.com",
            "admin_is_active": "on",
        }
        response = self.client.post(reverse("government_institution_edit", kwargs={"pk": institution.pk}), payload)
        self.assertRedirects(response, reverse("government_institutions"))
        institution.refresh_from_db()
        inst_admin.refresh_from_db()
        self.assertEqual(institution.name, "Updated University")
        self.assertEqual(institution.code, "UPD-U")
        self.assertTrue(institution.is_exam_body)
        self.assertEqual(inst_admin.email, "updatedinst@example.com")
        self.assertEqual(inst_admin.first_name, "Updated")

    def test_government_can_edit_business_details(self):
        business = Business.objects.create(name="Original Biz", code="OBIZ")
        hr = User.objects.create_user(
            email="orighr@example.com",
            username="orighr",
            password="StrongPass!123",
            role=User.Role.HR_MANAGER,
            first_name="Orig",
            last_name="HR",
        )
        HRProfile.objects.create(user=hr, business=business)
        self.client.force_login(self.gov_user)
        payload = {
            "business_name": "Updated Biz",
            "business_code": "UBIZ",
            "hr_first_name": "Updated",
            "hr_last_name": "Officer",
            "hr_email": "updatedhr@example.com",
            "hr_is_active": "on",
        }
        response = self.client.post(reverse("government_business_edit", kwargs={"pk": business.pk}), payload)
        self.assertRedirects(response, reverse("government_businesses"))
        business.refresh_from_db()
        hr.refresh_from_db()
        self.assertEqual(business.name, "Updated Biz")
        self.assertEqual(business.code, "UBIZ")
        self.assertEqual(hr.email, "updatedhr@example.com")
        self.assertEqual(hr.first_name, "Updated")

    def test_government_can_view_citizens_and_credentials(self):
        citizen_user = User.objects.create_user(
            email="citgov@example.com",
            username="citgov",
            password="StrongPass!123",
            role=User.Role.CITIZEN,
            first_name="Citizen",
            last_name="One",
        )
        citizen_profile = CitizenProfile.objects.create(
            user=citizen_user, national_id="99887766", otp_email="citgov@example.com"
        )
        institution = Institution.objects.create(name="Gov Test University", code="GTU")
        CertificateRecord.objects.create(
            national_id=citizen_profile.national_id,
            full_name="Citizen One",
            institution=institution,
            certificate_name="Bachelor of Law",
            award_level="Degree",
            grade="Second Class",
            graduation_year=2023,
            registration_number="GTU-1",
            created_by=self.gov_user,
        )

        self.client.force_login(self.gov_user)
        response = self.client.get(reverse("government_citizens"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Citizen One")
        self.assertContains(response, "citgov@example.com")
        self.assertContains(response, "Bachelor of Law")

    def test_non_government_user_cannot_access_government_controls(self):
        self.client.force_login(self.hr_user)
        response = self.client.get(reverse("government_institutions"))
        self.assertRedirects(
            response, f"{reverse('login')}?portal=gov&next={reverse('government_institutions')}"
        )
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccessRequestAndLoginHintsTests(TestCase):
    def test_login_page_shows_government_warning_for_gov_portal(self):
        response = self.client.get(reverse("login"), {"portal": "gov"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "authorized CA² Government Admin")

    def test_institution_access_request_sends_email(self):
        payload = {
            "institution_name": "New Institute",
            "institution_type": "LEARNING",
            "contact_person": "Registrar One",
            "official_email": "registrar@example.com",
            "contact_phone": "0712345678",
            "message": "Please onboard our institution.",
        }
        response = self.client.post(reverse("institution_access_request"), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Institution Access Request", mail.outbox[0].subject)

    def test_hr_access_request_sends_email(self):
        payload = {
            "business_name": "Talent Works Ltd",
            "contact_person": "HR Lead",
            "official_email": "hrlead@example.com",
            "contact_phone": "0722334455",
            "message": "Need HR verification access.",
        }
        response = self.client.post(reverse("hr_access_request"), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("HR Access Request", mail.outbox[0].subject)

    def test_public_tabs_pages_are_accessible(self):
        self.assertEqual(self.client.get(reverse("about_us")).status_code, 200)
        self.assertEqual(self.client.get(reverse("contact_us")).status_code, 200)
        self.assertEqual(self.client.get(reverse("vacancies_opportunities")).status_code, 200)

    def test_switching_login_portal_logs_out_current_user(self):
        citizen = User.objects.create_user(
            email="cit-switch@example.com",
            username="cit_switch",
            password="StrongPass!123",
            role=User.Role.CITIZEN,
        )
        self.client.force_login(citizen)
        response = self.client.get(reverse("login"), {"portal": "hr"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
