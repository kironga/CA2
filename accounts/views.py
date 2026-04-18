from functools import wraps
from collections import defaultdict
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.crypto import get_random_string
from datetime import timedelta

from accounts.forms import (
    BusinessAmendmentForm,
    BusinessOnboardingForm,
    CitizenSignUpForm,
    EmailAuthenticationForm,
    HRAccessRequestForm,
    InstitutionAmendmentForm,
    InstitutionAccessRequestForm,
    InstitutionOnboardingForm,
    PasswordResetRequestForm,
    PasswordResetVerifyForm,
)
from accounts.models import Business, HRProfile, User, PasswordResetRequest
from institutions.models import CertificateRecord, Institution
from verification.models import OTPRequest, VerificationAccessLog
from job_alerts.models import JobAlert


class EmailLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        portal = request.GET.get("portal", "").strip().lower()
        portal_to_role = {
            "gov": User.Role.GOVERNMENT_ADMIN,
            "institution": User.Role.INSTITUTION_ADMIN,
            "hr": User.Role.HR_MANAGER,
            "citizen": User.Role.CITIZEN,
        }
        expected_role = portal_to_role.get(portal)

        if request.user.is_authenticated and expected_role and request.user.role != expected_role:
            logout(request)
            messages.info(request, "You switched component portal. Please sign in again for the selected portal.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal = self.request.GET.get("portal", "").strip().lower()
        if portal not in {"gov", "institution", "hr", "citizen"}:
            portal = self._portal_from_next(self.request.GET.get("next", ""))
        context["portal"] = portal
        return context

    @staticmethod
    def _portal_from_next(next_url):
        next_url = (next_url or "").lower()
        if "/dashboard/admin/" in next_url:
            return "gov"
        if "/dashboard/institution/" in next_url:
            return "institution"
        if "/dashboard/hr/" in next_url:
            return "hr"
        if "/dashboard/citizen/" in next_url:
            return "citizen"
        return ""


def home(request):
    role_home = {
        User.Role.GOVERNMENT_ADMIN: {
            "label": "Government Oversight Workspace",
            "url_name": "dashboard_admin",
        },
        User.Role.INSTITUTION_ADMIN: {
            "label": "Institution Records Workspace",
            "url_name": "dashboard_institution",
        },
        User.Role.HR_MANAGER: {
            "label": "HR Verification Workspace",
            "url_name": "dashboard_hr",
        },
        User.Role.CITIZEN: {
            "label": "Citizen Profile Workspace",
            "url_name": "dashboard_citizen",
        },
    }
    current_workspace = role_home.get(request.user.role) if request.user.is_authenticated else None
    return render(request, "accounts/portal.html", {"current_workspace": current_workspace})


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                portal_lookup = {
                    User.Role.GOVERNMENT_ADMIN: "gov",
                    User.Role.INSTITUTION_ADMIN: "institution",
                    User.Role.HR_MANAGER: "hr",
                    User.Role.CITIZEN: "citizen",
                }
                expected_role = roles[0] if roles else ""
                portal = portal_lookup.get(expected_role, "")
                logout(request)
                messages.error(request, "You moved to a different component. Please sign in for that component.")
                login_url = f"{reverse('login')}?portal={portal}&next={request.path}"
                return redirect(login_url)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def citizen_register(request):
    if request.user.is_authenticated:
        return redirect("role_redirect")

    if request.method == "POST":
        form = CitizenSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully. Please log in.")
            return redirect("login")
    else:
        form = CitizenSignUpForm()
    return render(request, "accounts/citizen_register.html", {"form": form})


@login_required
def role_based_redirect(request):
    role_to_view = {
        User.Role.GOVERNMENT_ADMIN: "dashboard_admin",
        User.Role.INSTITUTION_ADMIN: "dashboard_institution",
        User.Role.HR_MANAGER: "dashboard_hr",
        User.Role.CITIZEN: "dashboard_citizen",
    }
    view_name = role_to_view.get(request.user.role)
    if not view_name:
        logout(request)
        messages.error(request, "Your account role is invalid. Contact administrator.")
        return redirect("login")
    return redirect(view_name)


@role_required(User.Role.GOVERNMENT_ADMIN)
def dashboard_admin(request):
    from citizens.models import CitizenProfile

    institutions_qs = Institution.objects.all()
    businesses_qs = Business.objects.all()
    otp_qs = OTPRequest.objects.all()
    context = {
        "institutions_count": institutions_qs.count(),
        "businesses_count": businesses_qs.count(),
        "institution_admins_count": User.objects.filter(role=User.Role.INSTITUTION_ADMIN, is_active=True).count(),
        "business_hr_count": HRProfile.objects.count(),
        "citizens_count": CitizenProfile.objects.count(),
        "records_count": CertificateRecord.objects.count(),
        "otp_requests_count": otp_qs.count(),
        "recent_institutions": institutions_qs.order_by("-created_at")[:5],
        "recent_businesses": businesses_qs.order_by("-created_at")[:5],
        "recent_otps": otp_qs.select_related("citizen", "requested_by").order_by("-created_at")[:5],
        "recent_access_logs": VerificationAccessLog.objects.select_related("citizen", "business", "hr_user")
        .order_by("-accessed_at")[:5],
    }
    return render(request, "accounts/dashboard_admin.html", context)


@role_required(User.Role.INSTITUTION_ADMIN)
def dashboard_institution(request):
    profile = getattr(request.user, "institution_profile", None)
    institution = profile.institution if profile else None
    records_qs = CertificateRecord.objects.filter(institution=institution) if institution else CertificateRecord.objects.none()
    context = {
        "institution": institution,
        "records_count": records_qs.count(),
        "graduates_count": records_qs.values("national_id").distinct().count(),
        "recent_records": records_qs.select_related("institution").order_by("-created_at")[:5],
        "recent_years": records_qs.values("graduation_year").order_by("-graduation_year")[:3],
    }
    return render(request, "accounts/dashboard_institution.html", context)


@role_required(User.Role.HR_MANAGER)
def dashboard_hr(request):
    otp_qs = OTPRequest.objects.filter(requested_by=request.user)
    now = timezone.now()
    context = {
        "active_otps": otp_qs.filter(is_used=False, expires_at__gt=now).count(),
        "used_otps": otp_qs.filter(is_used=True).count(),
        "total_requests": otp_qs.count(),
        "recent_otps": otp_qs.select_related("citizen", "citizen__user").order_by("-created_at")[:5],
        "recent_access_logs": VerificationAccessLog.objects.select_related("citizen", "business")
        .filter(hr_user=request.user)
        .order_by("-accessed_at")[:5],
        "now": now,
    }
    return render(request, "accounts/dashboard_hr.html", context)


@role_required(User.Role.CITIZEN)
def dashboard_citizen(request):
    return render(request, "accounts/dashboard_citizen.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect(reverse("login"))


def about_us(request):
    return render(request, "accounts/about_us.html")


def contact_us(request):
    return render(request, "accounts/contact_us.html")


def vacancies_and_opportunities(request):
    alerts = JobAlert.objects.select_related("created_by").all()[:40]
    opportunities = []
    for alert in alerts:
        try:
            business_name = alert.created_by.hr_profile.business.name
        except ObjectDoesNotExist:
            business_name = alert.organization
        opportunities.append({"alert": alert, "business_name": business_name})
    return render(request, "accounts/vacancies.html", {"opportunities": opportunities})


def institution_access_request(request):
    if request.method == "POST":
        form = InstitutionAccessRequestForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            subject = f"CA2 Institution Access Request: {cd['institution_name']}"
            body = (
                "A new institution access request was submitted.\n\n"
                f"Institution Name: {cd['institution_name']}\n"
                f"Institution Type: {cd['institution_type']}\n"
                f"Contact Person: {cd['contact_person']}\n"
                f"Official Email: {cd['official_email']}\n"
                f"Contact Phone: {cd.get('contact_phone') or '-'}\n"
                f"Message: {cd.get('message') or '-'}\n"
            )
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CA2_GOVERNMENT_REG_EMAIL],
                fail_silently=False,
            )
            messages.success(request, "Request submitted. Government admin will review and issue credentials.")
            return redirect(f"{reverse('login')}?portal=institution")
    else:
        form = InstitutionAccessRequestForm()
    return render(request, "accounts/request_institution_access.html", {"form": form})


def hr_access_request(request):
    if request.method == "POST":
        form = HRAccessRequestForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            subject = f"CA2 HR Access Request: {cd['business_name']}"
            body = (
                "A new HR access request was submitted.\n\n"
                f"Business Name: {cd['business_name']}\n"
                f"Contact Person: {cd['contact_person']}\n"
                f"Official Email: {cd['official_email']}\n"
                f"Contact Phone: {cd.get('contact_phone') or '-'}\n"
                f"Message: {cd.get('message') or '-'}\n"
            )
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CA2_GOVERNMENT_REG_EMAIL],
                fail_silently=False,
            )
            messages.success(request, "Request submitted. Government admin will review and issue credentials.")
            return redirect(f"{reverse('login')}?portal=hr")
    else:
        form = HRAccessRequestForm()
    return render(request, "accounts/request_hr_access.html", {"form": form})


@role_required(User.Role.GOVERNMENT_ADMIN)
def government_institutions(request):
    if request.method == "POST":
        form = InstitutionOnboardingForm(request.POST)
        if form.is_valid():
            institution, user = form.save()
            messages.success(
                request,
                f"Institution created: {institution.name}. Login issued to {user.email}.",
            )
            return redirect("government_institutions")
    else:
        form = InstitutionOnboardingForm()

    institutions = Institution.objects.prefetch_related("admins__user").all()
    return render(
        request,
        "accounts/government_institutions.html",
        {"form": form, "institutions": institutions},
    )


@role_required(User.Role.GOVERNMENT_ADMIN)
def government_institution_delete(request, pk):
    if request.method != "POST":
        return redirect("government_institutions")

    institution = get_object_or_404(Institution.objects.prefetch_related("admins__user"), pk=pk)
    with transaction.atomic():
        records_deleted = CertificateRecord.objects.filter(institution=institution).delete()[0]
        disabled_users = 0
        for profile in institution.admins.select_related("user").all():
            user = profile.user
            if user.is_active:
                user.is_active = False
                user.set_unusable_password()
                user.save(update_fields=["is_active", "password"])
                disabled_users += 1
        institution_name = institution.name
        institution.delete()

    messages.success(
        request,
        f"{institution_name} deleted. Disabled {disabled_users} institution account(s) and removed {records_deleted} record(s).",
    )
    return redirect("government_institutions")


@role_required(User.Role.GOVERNMENT_ADMIN)
def government_institution_edit(request, pk):
    institution = get_object_or_404(Institution.objects.prefetch_related("admins__user"), pk=pk)
    admin_profile = institution.admins.select_related("user").first()
    admin_user = admin_profile.user if admin_profile else None

    if request.method == "POST":
        form = InstitutionAmendmentForm(request.POST, institution=institution, admin_user=admin_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"{institution.name} details updated successfully.")
            return redirect("government_institutions")
    else:
        form = InstitutionAmendmentForm(institution=institution, admin_user=admin_user)

    return render(
        request,
        "accounts/government_institution_edit.html",
        {"form": form, "institution": institution, "admin_user": admin_user},
    )


@role_required(User.Role.GOVERNMENT_ADMIN)
def government_businesses(request):
    if request.method == "POST":
        form = BusinessOnboardingForm(request.POST)
        if form.is_valid():
            business, user = form.save()
            messages.success(
                request,
                f"Business created: {business.name}. HR login issued to {user.email}.",
            )
            return redirect("government_businesses")
    else:
        form = BusinessOnboardingForm()

    businesses = Business.objects.prefetch_related("hr_managers__user").all()
    return render(
        request,
        "accounts/government_businesses.html",
        {"form": form, "businesses": businesses},
    )


@role_required(User.Role.GOVERNMENT_ADMIN)
def government_business_delete(request, pk):
    if request.method != "POST":
        return redirect("government_businesses")

    business = get_object_or_404(Business.objects.prefetch_related("hr_managers__user"), pk=pk)
    with transaction.atomic():
        disabled_users = 0
        for profile in business.hr_managers.select_related("user").all():
            user = profile.user
            if user.is_active:
                user.is_active = False
                user.set_unusable_password()
                user.save(update_fields=["is_active", "password"])
                disabled_users += 1
        business_name = business.name
        business.delete()

    messages.success(
        request,
        f"{business_name} deleted. Disabled {disabled_users} HR account(s).",
    )
    return redirect("government_businesses")


@role_required(User.Role.GOVERNMENT_ADMIN)
def government_business_edit(request, pk):
    business = get_object_or_404(Business.objects.prefetch_related("hr_managers__user"), pk=pk)
    hr_profile = business.hr_managers.select_related("user").first()
    hr_user = hr_profile.user if hr_profile else None

    if request.method == "POST":
        form = BusinessAmendmentForm(request.POST, business=business, hr_user=hr_user)
        if form.is_valid():
            form.save()
            messages.success(request, f"{business.name} details updated successfully.")
            return redirect("government_businesses")
    else:
        form = BusinessAmendmentForm(business=business, hr_user=hr_user)

    return render(
        request,
        "accounts/government_business_edit.html",
        {"form": form, "business": business, "hr_user": hr_user},
    )


def forgot_password_request(request):
    """
    Step 1: collect email and send a 6-digit code.
    """
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            code = get_random_string(length=6, allowed_chars="0123456789")
            PasswordResetRequest.objects.create(
                user=user,
                code_hash=make_password(code),
                expires_at=timezone.now() + timedelta(minutes=10),
                request_ip=request.META.get("REMOTE_ADDR"),
                user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:255],
            )
            send_mail(
                subject="CA² password reset code",
                message=(
                    f"Hi {user.first_name or ''},\n\n"
                    f"Use this code to reset your CA² password: {code}\n"
                    "It expires in 10 minutes. If you did not request this, you can ignore this email.\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,  
            )
        messages.success(request, "If the email is registered, a reset code has been sent.")
        return redirect("forgot_password_verify")

    return render(request, "accounts/forgot_password_request.html", {"form": form})


def forgot_password_verify(request):
    """
    Step 2: confirm code and let the user set a new password.
    """
    form = PasswordResetVerifyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        code = form.cleaned_data["code"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            messages.error(request, "Invalid code or email. Request a new reset code.")
            return redirect("forgot_password_request")

        reset = (
            PasswordResetRequest.objects.filter(
                user=user, is_used=False, expires_at__gt=timezone.now()
            )
            .order_by("-created_at")
            .first()
        )

        if not reset:
            messages.error(request, "No active reset code found. Request a new one.")
            return redirect("forgot_password_request")

        if reset.attempts >= 5:
            messages.error(request, "Too many attempts. Request a new reset code.")
            return redirect("forgot_password_request")

        if not check_password(code, reset.code_hash):
            reset.attempts += 1
            reset.save(update_fields=["attempts"])
            messages.error(request, "Invalid code. Please try again.")
            return redirect("forgot_password_verify")

        user.set_password(form.cleaned_data["new_password1"])
        user.save(update_fields=["password"])
        reset.is_used = True
        reset.save(update_fields=["is_used"])
        messages.success(request, "Password updated. You can now sign in.")
        return redirect("login")

    return render(request, "accounts/forgot_password_verify.html", {"form": form})


@role_required(User.Role.GOVERNMENT_ADMIN)
def government_citizens(request):
    from citizens.models import CitizenProfile

    citizens = CitizenProfile.objects.select_related("user").order_by(
        "user__first_name", "user__last_name", "national_id"
    )
    records_by_national_id = defaultdict(list)
    for record in CertificateRecord.objects.select_related("institution").all():
        records_by_national_id[record.national_id].append(record)

    citizen_rows = [
        {
            "profile": profile,
            "records": records_by_national_id.get(profile.national_id, []),
        }
        for profile in citizens
    ]

    return render(request, "accounts/government_citizens.html", {"citizen_rows": citizen_rows})
