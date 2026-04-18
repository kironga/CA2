from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password

from accounts.models import Business, HRProfile, User
from citizens.models import CitizenProfile
from institutions.models import Institution, InstitutionProfile


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")


class CitizenSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    national_id = forms.CharField(max_length=20, required=True)
    otp_email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "national_id", "otp_email")

    def clean_national_id(self):
        national_id = self.cleaned_data["national_id"].strip()
        if CitizenProfile.objects.filter(national_id=national_id).exists():
            raise forms.ValidationError("National ID is already registered.")
        return national_id

    def clean_otp_email(self):
        email = self.cleaned_data["otp_email"].strip().lower()
        if CitizenProfile.objects.filter(otp_email=email).exists():
            raise forms.ValidationError("Email is already linked to another National ID.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"].strip().lower()
        user.email = email
        user.username = self._generate_username(email)
        user.role = User.Role.CITIZEN
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        if commit:
            user.save()
            CitizenProfile.objects.create(
                user=user,
                national_id=self.cleaned_data["national_id"],
                otp_email=self.cleaned_data["otp_email"],
            )
        return user

    @staticmethod
    def _generate_username(email):
        base = email.split("@")[0][:140] or "citizen"
        candidate = base
        idx = 1
        while User.objects.filter(username=candidate).exists():
            candidate = f"{base}{idx}"
            idx += 1
        return candidate


def generate_unique_username(email, fallback):
    base = (email.split("@")[0][:140] or fallback).strip() or fallback
    candidate = base
    idx = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base}{idx}"
        idx += 1
    return candidate


class InstitutionOnboardingForm(forms.Form):
    institution_name = forms.CharField(max_length=255, required=True)
    institution_code = forms.CharField(max_length=30, required=True)
    is_exam_body = forms.BooleanField(required=False)
    admin_first_name = forms.CharField(max_length=150, required=True)
    admin_last_name = forms.CharField(max_length=150, required=True)
    admin_email = forms.EmailField(required=True)
    admin_password1 = forms.CharField(widget=forms.PasswordInput, required=True)
    admin_password2 = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_institution_name(self):
        value = self.cleaned_data["institution_name"].strip()
        if Institution.objects.filter(name__iexact=value).exists():
            raise forms.ValidationError("Institution with this name already exists.")
        return value

    def clean_institution_code(self):
        value = self.cleaned_data["institution_code"].strip().upper()
        if Institution.objects.filter(code__iexact=value).exists():
            raise forms.ValidationError("Institution with this code already exists.")
        return value

    def clean_admin_email(self):
        value = self.cleaned_data["admin_email"].strip().lower()
        if User.objects.filter(email=value).exists():
            raise forms.ValidationError("This email is already in use.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("admin_password1") != cleaned_data.get("admin_password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self):
        institution = Institution.objects.create(
            name=self.cleaned_data["institution_name"],
            code=self.cleaned_data["institution_code"],
            is_exam_body=self.cleaned_data.get("is_exam_body", False),
        )
        email = self.cleaned_data["admin_email"]
        user = User.objects.create_user(
            email=email,
            username=generate_unique_username(email, "inst_admin"),
            password=self.cleaned_data["admin_password1"],
            role=User.Role.INSTITUTION_ADMIN,
            first_name=self.cleaned_data["admin_first_name"].strip(),
            last_name=self.cleaned_data["admin_last_name"].strip(),
        )
        InstitutionProfile.objects.create(user=user, institution=institution)
        return institution, user


class BusinessOnboardingForm(forms.Form):
    business_name = forms.CharField(max_length=255, required=True)
    business_code = forms.CharField(max_length=40, required=True)
    hr_first_name = forms.CharField(max_length=150, required=True)
    hr_last_name = forms.CharField(max_length=150, required=True)
    hr_email = forms.EmailField(required=True)
    hr_password1 = forms.CharField(widget=forms.PasswordInput, required=True)
    hr_password2 = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_business_name(self):
        value = self.cleaned_data["business_name"].strip()
        if Business.objects.filter(name__iexact=value).exists():
            raise forms.ValidationError("Business with this name already exists.")
        return value

    def clean_business_code(self):
        value = self.cleaned_data["business_code"].strip().upper()
        if Business.objects.filter(code__iexact=value).exists():
            raise forms.ValidationError("Business with this code already exists.")
        return value

    def clean_hr_email(self):
        value = self.cleaned_data["hr_email"].strip().lower()
        if User.objects.filter(email=value).exists():
            raise forms.ValidationError("This email is already in use.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("hr_password1") != cleaned_data.get("hr_password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self):
        business = Business.objects.create(
            name=self.cleaned_data["business_name"],
            code=self.cleaned_data["business_code"],
        )
        email = self.cleaned_data["hr_email"]
        user = User.objects.create_user(
            email=email,
            username=generate_unique_username(email, "hr_manager"),
            password=self.cleaned_data["hr_password1"],
            role=User.Role.HR_MANAGER,
            first_name=self.cleaned_data["hr_first_name"].strip(),
            last_name=self.cleaned_data["hr_last_name"].strip(),
        )
        HRProfile.objects.create(user=user, business=business)
        return business, user


class InstitutionAccessRequestForm(forms.Form):
    institution_name = forms.CharField(max_length=255, required=True)
    institution_type = forms.ChoiceField(
        choices=(
            ("LEARNING", "Learning Institution"),
            ("EXAM_BODY", "Examination Body"),
        ),
        required=True,
    )
    contact_person = forms.CharField(max_length=150, required=True)
    official_email = forms.EmailField(required=True)
    contact_phone = forms.CharField(max_length=30, required=False)
    message = forms.CharField(widget=forms.Textarea, required=False)


class HRAccessRequestForm(forms.Form):
    business_name = forms.CharField(max_length=255, required=True)
    contact_person = forms.CharField(max_length=150, required=True)
    official_email = forms.EmailField(required=True)
    contact_phone = forms.CharField(max_length=30, required=False)
    message = forms.CharField(widget=forms.Textarea, required=False)


class InstitutionAmendmentForm(forms.Form):
    institution_name = forms.CharField(max_length=255, required=True)
    institution_code = forms.CharField(max_length=30, required=True)
    is_exam_body = forms.BooleanField(required=False)
    admin_first_name = forms.CharField(max_length=150, required=False)
    admin_last_name = forms.CharField(max_length=150, required=False)
    admin_email = forms.EmailField(required=False)
    admin_is_active = forms.BooleanField(required=False)

    def __init__(self, *args, institution, admin_user=None, **kwargs):
        self.institution = institution
        self.admin_user = admin_user
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial.update(
                {
                    "institution_name": institution.name,
                    "institution_code": institution.code,
                    "is_exam_body": institution.is_exam_body,
                    "admin_first_name": admin_user.first_name if admin_user else "",
                    "admin_last_name": admin_user.last_name if admin_user else "",
                    "admin_email": admin_user.email if admin_user else "",
                    "admin_is_active": admin_user.is_active if admin_user else False,
                }
            )
        if not admin_user:
            self.fields["admin_first_name"].disabled = True
            self.fields["admin_last_name"].disabled = True
            self.fields["admin_email"].disabled = True
            self.fields["admin_is_active"].disabled = True

    def clean_institution_name(self):
        value = self.cleaned_data["institution_name"].strip()
        if Institution.objects.filter(name__iexact=value).exclude(pk=self.institution.pk).exists():
            raise forms.ValidationError("Institution with this name already exists.")
        return value

    def clean_institution_code(self):
        value = self.cleaned_data["institution_code"].strip().upper()
        if Institution.objects.filter(code__iexact=value).exclude(pk=self.institution.pk).exists():
            raise forms.ValidationError("Institution with this code already exists.")
        return value

    def clean_admin_email(self):
        email = (self.cleaned_data.get("admin_email") or "").strip().lower()
        if not self.admin_user:
            return email
        if User.objects.filter(email=email).exclude(pk=self.admin_user.pk).exists():
            raise forms.ValidationError("This admin email is already used by another account.")
        return email

    def save(self):
        self.institution.name = self.cleaned_data["institution_name"]
        self.institution.code = self.cleaned_data["institution_code"]
        self.institution.is_exam_body = self.cleaned_data.get("is_exam_body", False)
        self.institution.save(update_fields=["name", "code", "is_exam_body"])

        if self.admin_user:
            self.admin_user.first_name = (self.cleaned_data.get("admin_first_name") or "").strip()
            self.admin_user.last_name = (self.cleaned_data.get("admin_last_name") or "").strip()
            self.admin_user.email = self.cleaned_data["admin_email"]
            self.admin_user.is_active = self.cleaned_data.get("admin_is_active", False)
            self.admin_user.save(update_fields=["first_name", "last_name", "email", "is_active"])

        return self.institution


class BusinessAmendmentForm(forms.Form):
    business_name = forms.CharField(max_length=255, required=True)
    business_code = forms.CharField(max_length=40, required=True)
    hr_first_name = forms.CharField(max_length=150, required=False)
    hr_last_name = forms.CharField(max_length=150, required=False)
    hr_email = forms.EmailField(required=False)
    hr_is_active = forms.BooleanField(required=False)

    def __init__(self, *args, business, hr_user=None, **kwargs):
        self.business = business
        self.hr_user = hr_user
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial.update(
                {
                    "business_name": business.name,
                    "business_code": business.code,
                    "hr_first_name": hr_user.first_name if hr_user else "",
                    "hr_last_name": hr_user.last_name if hr_user else "",
                    "hr_email": hr_user.email if hr_user else "",
                    "hr_is_active": hr_user.is_active if hr_user else False,
                }
            )
        if not hr_user:
            self.fields["hr_first_name"].disabled = True
            self.fields["hr_last_name"].disabled = True
            self.fields["hr_email"].disabled = True
            self.fields["hr_is_active"].disabled = True

    def clean_business_name(self):
        value = self.cleaned_data["business_name"].strip()
        if Business.objects.filter(name__iexact=value).exclude(pk=self.business.pk).exists():
            raise forms.ValidationError("Business with this name already exists.")
        return value

    def clean_business_code(self):
        value = self.cleaned_data["business_code"].strip().upper()
        if Business.objects.filter(code__iexact=value).exclude(pk=self.business.pk).exists():
            raise forms.ValidationError("Business with this code already exists.")
        return value

    def clean_hr_email(self):
        email = (self.cleaned_data.get("hr_email") or "").strip().lower()
        if not self.hr_user:
            return email
        if User.objects.filter(email=email).exclude(pk=self.hr_user.pk).exists():
            raise forms.ValidationError("This HR email is already used by another account.")
        return email

    def save(self):
        self.business.name = self.cleaned_data["business_name"]
        self.business.code = self.cleaned_data["business_code"]
        self.business.save(update_fields=["name", "code"])

        if self.hr_user:
            self.hr_user.first_name = (self.cleaned_data.get("hr_first_name") or "").strip()
            self.hr_user.last_name = (self.cleaned_data.get("hr_last_name") or "").strip()
            self.hr_user.email = self.cleaned_data["hr_email"]
            self.hr_user.is_active = self.cleaned_data.get("hr_is_active", False)
            self.hr_user.save(update_fields=["first_name", "last_name", "email", "is_active"])

        return self.business


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(required=True)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class PasswordResetVerifyForm(forms.Form):
    email = forms.EmailField(required=True)
    code = forms.CharField(max_length=6, min_length=6, required=True)
    new_password1 = forms.CharField(widget=forms.PasswordInput, required=True, label="New password")
    new_password2 = forms.CharField(widget=forms.PasswordInput, required=True, label="Confirm new password")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1:
            validate_password(p1)
        return cleaned
