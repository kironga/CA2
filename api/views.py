import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.models import User
from institutions.forms import CertificateRecordForm
from institutions.models import CertificateRecord
from verification.models import OTPRequest
from verification.services import can_request_otp, create_otp_request, log_verification_access, send_otp_email, validate_otp
from citizens.models import CitizenProfile


def _require_role(request, *roles):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)
    if request.user.role not in roles:
        return JsonResponse({"detail": "Forbidden."}, status=403)
    return None


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return None


@require_GET
def institution_certificates_list(request):
    denied = _require_role(request, User.Role.INSTITUTION_ADMIN)
    if denied:
        return denied
    institution = request.user.institution_profile.institution
    records = list(
        CertificateRecord.objects.filter(institution=institution).values(
            "id",
            "national_id",
            "full_name",
            "certificate_name",
            "award_level",
            "grade",
            "graduation_year",
            "registration_number",
        )
    )
    return JsonResponse({"count": len(records), "results": records})


@require_POST
def institution_certificate_create(request):
    denied = _require_role(request, User.Role.INSTITUTION_ADMIN)
    if denied:
        return denied
    payload = _json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    form = CertificateRecordForm(payload)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    record = form.save(commit=False)
    record.institution = request.user.institution_profile.institution
    record.created_by = request.user
    record.save()
    return JsonResponse({"id": record.id, "detail": "Created."}, status=201)


@require_POST
def hr_request_otp_api(request):
    denied = _require_role(request, User.Role.HR_MANAGER)
    if denied:
        return denied
    payload = _json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    national_id = str(payload.get("national_id", "")).strip()
    if not national_id.isdigit():
        return JsonResponse({"detail": "National ID must be numeric."}, status=400)

    try:
        citizen = CitizenProfile.objects.select_related("user").get(national_id=national_id)
    except CitizenProfile.DoesNotExist:
        return JsonResponse({"detail": "Citizen not found."}, status=404)

    allowed, reason = can_request_otp(citizen, request.user)
    if not allowed:
        return JsonResponse({"detail": reason}, status=429)

    otp_request, otp = create_otp_request(
        citizen,
        request.user,
        national_id,
        request_ip=request.META.get("REMOTE_ADDR", ""),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    send_otp_email(citizen, otp, national_id)
    return JsonResponse(
        {"otp_request_id": otp_request.id, "expires_at": otp_request.expires_at.isoformat(), "detail": "OTP sent."},
        status=201,
    )


@require_POST
def hr_verify_otp_api(request):
    denied = _require_role(request, User.Role.HR_MANAGER)
    if denied:
        return denied
    payload = _json_body(request)
    if payload is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)

    otp_request_id = payload.get("otp_request_id")
    otp = str(payload.get("otp", "")).strip()
    if not str(otp_request_id).isdigit():
        return JsonResponse({"detail": "otp_request_id must be numeric."}, status=400)
    if not otp.isdigit() or len(otp) != 6:
        return JsonResponse({"detail": "OTP must be six digits."}, status=400)

    try:
        otp_request = OTPRequest.objects.select_related("citizen", "citizen__user").get(
            id=int(otp_request_id), requested_by=request.user
        )
    except OTPRequest.DoesNotExist:
        return JsonResponse({"detail": "OTP request not found."}, status=404)

    is_valid, message = validate_otp(otp_request, otp)
    if not is_valid:
        return JsonResponse({"detail": message}, status=400)

    log_verification_access(otp_request.citizen, hr_user=request.user, otp_request=otp_request, source="API")

    records = list(
        CertificateRecord.objects.filter(national_id=otp_request.national_id)
        .select_related("institution")
        .values("institution__name", "certificate_name", "award_level", "grade", "graduation_year")
    )
    citizen = otp_request.citizen
    return JsonResponse(
        {
            "detail": message,
            "citizen": {
                "national_id": citizen.national_id,
                "full_name": citizen.user.get_full_name(),
                "email": citizen.otp_email,
            },
            "records": records,
        }
    )
