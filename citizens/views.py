from django.contrib import messages
from django.utils import timezone
from django.shortcuts import redirect, render

from accounts.models import User
from accounts.views import role_required
from citizens.forms import CitizenProfileForm
from citizens.models import CitizenProfile
from institutions.models import CertificateRecord
from verification.models import OTPRequest, VerificationAccessLog
from verification.services import get_citizen_otp_preview


@role_required(User.Role.CITIZEN)
def citizen_profile(request):
    try:
        profile = request.user.citizen_profile
    except CitizenProfile.DoesNotExist:
        messages.error(request, "Citizen profile not found. Contact system administrator.")
        return redirect("dashboard_citizen")

    if request.method == "POST":
        form = CitizenProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
    else:
        form = CitizenProfileForm(instance=profile, user=request.user)
    return render(request, "citizens/profile.html", {"form": form})


@role_required(User.Role.CITIZEN)
def citizen_education_details(request):
    try:
        profile = request.user.citizen_profile
    except CitizenProfile.DoesNotExist:
        messages.error(request, "Citizen profile not found. Contact system administrator.")
        return redirect("dashboard_citizen")

    records = CertificateRecord.objects.filter(national_id=profile.national_id).select_related("institution")
    return render(request, "citizens/education_details.html", {"profile": profile, "records": records})


@role_required(User.Role.CITIZEN)
def citizen_access_history(request):
    try:
        profile = request.user.citizen_profile
    except CitizenProfile.DoesNotExist:
        messages.error(request, "Citizen profile not found. Contact system administrator.")
        return redirect("dashboard_citizen")

    accesses = VerificationAccessLog.objects.filter(citizen=profile).select_related("business", "hr_user")
    return render(request, "citizens/access_history.html", {"profile": profile, "accesses": accesses})


@role_required(User.Role.CITIZEN)
def citizen_otp_center(request):
    try:
        profile = request.user.citizen_profile
    except CitizenProfile.DoesNotExist:
        messages.error(request, "Citizen profile not found. Contact system administrator.")
        return redirect("dashboard_citizen")

    active_request = (
        OTPRequest.objects.filter(citizen=profile, is_used=False, expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    preview = get_citizen_otp_preview(profile)
    return render(
        request,
        "citizens/otp_center.html",
        {"profile": profile, "active_request": active_request, "preview": preview},
    )
