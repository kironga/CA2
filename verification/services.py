import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.utils import timezone

from verification.models import OTPRequest, VerificationAccessLog


OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_COOLDOWN_SECONDS = 60
OTP_MAX_PER_DAY_BY_CITIZEN = 10
OTP_MAX_PER_DAY_BY_HR = 40


def generate_numeric_otp(length=6):
    return "".join(secrets.choice("0123456789") for _ in range(length))


def can_request_otp(citizen, hr_user):
    now = timezone.now()
    recent_cutoff = now - timedelta(seconds=OTP_COOLDOWN_SECONDS)
    day_cutoff = now - timedelta(days=1)

    recent_exists = OTPRequest.objects.filter(citizen=citizen, created_at__gte=recent_cutoff).exists()
    if recent_exists:
        return False, "OTP recently requested. Wait one minute before requesting again."

    citizen_count = OTPRequest.objects.filter(citizen=citizen, created_at__gte=day_cutoff).count()
    if citizen_count >= OTP_MAX_PER_DAY_BY_CITIZEN:
        return False, "Daily OTP request limit reached for this National ID."

    hr_count = OTPRequest.objects.filter(requested_by=hr_user, created_at__gte=day_cutoff).count()
    if hr_count >= OTP_MAX_PER_DAY_BY_HR:
        return False, "You have reached your OTP request limit for today."

    return True, ""


def _otp_preview_key_for_request(otp_request_id):
    return f"otp_preview:req:{otp_request_id}"


def _otp_preview_pointer_key_for_citizen(citizen_id):
    return f"otp_preview:citizen:{citizen_id}"


def _set_otp_preview(citizen, otp_request, otp):
    ttl = OTP_EXPIRY_MINUTES * 60
    preview = {"otp": otp, "expires_at": otp_request.expires_at.isoformat(), "otp_request_id": otp_request.id}
    cache.set(_otp_preview_key_for_request(otp_request.id), preview, timeout=ttl)
    cache.set(_otp_preview_pointer_key_for_citizen(citizen.id), otp_request.id, timeout=ttl)


def get_citizen_otp_preview(citizen):
    otp_request_id = cache.get(_otp_preview_pointer_key_for_citizen(citizen.id))
    if not otp_request_id:
        return None
    return cache.get(_otp_preview_key_for_request(otp_request_id))


def _clear_otp_preview(citizen, otp_request):
    cache.delete(_otp_preview_key_for_request(otp_request.id))
    pointer_key = _otp_preview_pointer_key_for_citizen(citizen.id)
    pointed_id = cache.get(pointer_key)
    if pointed_id == otp_request.id:
        cache.delete(pointer_key)


def create_otp_request(citizen, hr_user, national_id, request_ip="", user_agent=""):
    otp = generate_numeric_otp()
    otp_request = OTPRequest.objects.create(
        national_id=national_id,
        citizen=citizen,
        requested_by=hr_user,
        otp_hash=make_password(otp),
        expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        request_ip=request_ip or None,
        user_agent=(user_agent or "")[:255],
    )
    _set_otp_preview(citizen, otp_request, otp)
    return otp_request, otp


def revoke_otp_request(otp_request):
    _clear_otp_preview(otp_request.citizen, otp_request)
    otp_request.delete()


def send_otp_email(citizen, otp, national_id):
    subject = "CA² credential verification OTP"
    message = (
        f"Dear {citizen.user.get_full_name() or 'Citizen'},\n\n"
        f"A credential verification request was initiated for National ID {national_id}.\n"
        f"Your one-time password (OTP) is: {otp}\n"
        f"This OTP expires in {OTP_EXPIRY_MINUTES} minutes.\n\n"
        "If you did not expect this request, contact support immediately."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[citizen.otp_email],
        fail_silently=False,
    )


def validate_otp(otp_request, otp):
    if otp_request.is_used:
        return False, "This OTP has already been used."
    if otp_request.is_expired():
        return False, "OTP has expired. Request a new one."
    if otp_request.attempts >= OTP_MAX_ATTEMPTS:
        return False, "Maximum verification attempts reached."

    otp_request.attempts += 1
    otp_request.save(update_fields=["attempts"])

    if not check_password(otp, otp_request.otp_hash):
        return False, "Invalid OTP."

    otp_request.is_used = True
    otp_request.save(update_fields=["is_used"])
    _clear_otp_preview(otp_request.citizen, otp_request)
    return True, "OTP verified successfully."


def log_verification_access(citizen, hr_user=None, otp_request=None, source=VerificationAccessLog.Source.WEB):
    business = None
    if hr_user:
        try:
            business = hr_user.hr_profile.business
        except ObjectDoesNotExist:
            business = None

    return VerificationAccessLog.objects.create(
        citizen=citizen,
        hr_user=hr_user,
        business=business,
        otp_request=otp_request,
        national_id=citizen.national_id,
        source=source,
    )
