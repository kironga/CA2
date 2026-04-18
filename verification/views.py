import logging

from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.models import User
from accounts.views import role_required
from citizens.models import CitizenProfile
from institutions.models import CertificateRecord
from verification.forms import OTPRequestForm, OTPVerifyForm
from verification.models import OTPRequest
from verification.services import (
    can_request_otp,
    create_otp_request,
    log_verification_access,
    revoke_otp_request,
    send_otp_email,
    validate_otp,
)


logger = logging.getLogger(__name__)


@role_required(User.Role.HR_MANAGER)
def request_otp(request):
    if request.method == "POST":
        form = OTPRequestForm(request.POST)
        if form.is_valid():
            national_id = form.cleaned_data["national_id"]
            try:
                citizen = CitizenProfile.objects.select_related("user").get(national_id=national_id)
            except CitizenProfile.DoesNotExist:
                messages.error(request, "No citizen found with that National ID.")
                return render(request, "verification/request_otp.html", {"form": form})

            allowed, reason = can_request_otp(citizen, request.user)
            if not allowed:
                messages.error(request, reason)
                return render(request, "verification/request_otp.html", {"form": form})

            otp_request, otp = create_otp_request(
                citizen,
                request.user,
                national_id,
                request_ip=request.META.get("REMOTE_ADDR", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            try:
                send_otp_email(citizen, otp, national_id)
            except Exception:
                revoke_otp_request(otp_request)
                logger.exception(
                    "Failed to deliver OTP email to %s for National ID %s",
                    citizen.otp_email,
                    national_id,
                )
                messages.error(
                    request,
                    "Could not send OTP email right now. Confirm SMTP settings and try again.",
                )
                return render(request, "verification/request_otp.html", {"form": form})

            request.session["otp_request_id"] = otp_request.id
            request.session["otp_national_id"] = national_id
            request.session.pop("verified_national_id", None)
            request.session.pop("access_log_otp_request_id", None)
            messages.success(request, "OTP sent to citizen's registered email.")
            return redirect("verify_otp")
    else:
        form = OTPRequestForm()
    return render(request, "verification/request_otp.html", {"form": form})


@role_required(User.Role.HR_MANAGER)
def verify_otp_view(request):
    otp_request_id = request.session.get("otp_request_id")
    if not otp_request_id:
        messages.error(request, "Start by requesting an OTP.")
        return redirect("request_otp")

    try:
        otp_request = OTPRequest.objects.select_related("citizen", "citizen__user").get(
            id=otp_request_id,
            requested_by=request.user,
            national_id=request.session.get("otp_national_id"),
        )
    except OTPRequest.DoesNotExist:
        messages.error(request, "OTP request no longer exists. Request a new OTP.")
        return redirect("request_otp")

    if request.method == "POST":
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            is_valid, message = validate_otp(otp_request, form.cleaned_data["otp"])
            if is_valid:
                request.session["verified_national_id"] = otp_request.national_id
                messages.success(request, message)
                return redirect("verified_records")
            messages.error(request, message)
    else:
        form = OTPVerifyForm()
    return render(
        request,
        "verification/verify_otp.html",
        {"form": form, "national_id": otp_request.national_id, "expires_at": otp_request.expires_at},
    )


@role_required(User.Role.HR_MANAGER)
def verified_records(request):
    national_id = request.session.get("verified_national_id")
    if not national_id:
        messages.error(request, "You must complete OTP verification first.")
        return redirect("request_otp")

    otp_request_id = request.session.get("otp_request_id")
    citizen = CitizenProfile.objects.select_related("user").filter(national_id=national_id).first()
    records = CertificateRecord.objects.filter(national_id=national_id).select_related("institution")
    if citizen and otp_request_id and request.session.get("access_log_otp_request_id") != otp_request_id:
        otp_request = OTPRequest.objects.filter(id=otp_request_id, requested_by=request.user).first()
        log_verification_access(citizen, hr_user=request.user, otp_request=otp_request)
        request.session["access_log_otp_request_id"] = otp_request_id
    return render(
        request,
        "verification/records.html",
        {
            "citizen": citizen,
            "records": records,
            "national_id": national_id,
        },
    )
