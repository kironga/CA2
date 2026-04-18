from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, FileResponse, HttpResponseForbidden, Http404

from accounts.models import User
from accounts.views import role_required
from institutions.forms import CertificateRecordForm
from institutions.models import CertificateRecord
from citizens.models import CitizenProfile


@role_required(User.Role.INSTITUTION_ADMIN)
def certificate_list(request):
    institution = request.user.institution_profile.institution
    records = CertificateRecord.objects.filter(institution=institution)
    return render(request, "institutions/certificate_list.html", {"records": records, "institution": institution})


@role_required(User.Role.INSTITUTION_ADMIN)
def certificate_create(request):
    institution = request.user.institution_profile.institution
    if request.method == "POST":
        form = CertificateRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.institution = institution
            record.created_by = request.user
            record.save()
            messages.success(request, "Certificate record saved.")
            return redirect("institution_certificates")
    else:
        form = CertificateRecordForm()
    return render(request, "institutions/certificate_form.html", {"form": form, "action": "Add"})


@role_required(User.Role.INSTITUTION_ADMIN)
def certificate_update(request, pk):
    institution = request.user.institution_profile.institution
    record = get_object_or_404(CertificateRecord, pk=pk, institution=institution)
    if request.method == "POST":
        form = CertificateRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Certificate record updated.")
            return redirect("institution_certificates")
    else:
        form = CertificateRecordForm(instance=record)
    return render(request, "institutions/certificate_form.html", {"form": form, "action": "Edit"})


@role_required(User.Role.INSTITUTION_ADMIN)
def citizen_lookup(request):
    """
    Lightweight autocomplete for National ID -> name/email and most recent certificate (if any).
    """
    query = request.GET.get("q", "").strip()
    if len(query) < 3:
        return JsonResponse([], safe=False)

    results = (
        CitizenProfile.objects.select_related("user")
        .filter(national_id__startswith=query)
        .order_by("national_id")[:8]
    )
    payload = [
        _serialize_citizen_with_record(c)
        for c in results
    ]
    return JsonResponse(payload, safe=False)


def _serialize_citizen_with_record(citizen: CitizenProfile):
    latest_record = (
        CertificateRecord.objects.filter(national_id=citizen.national_id)
        .order_by("-created_at")
        .first()
    )
    record_data = None
    if latest_record:
        record_data = {
            "certificate_name": latest_record.certificate_name,
            "award_level": latest_record.award_level,
            "grade": latest_record.grade,
            "graduation_year": latest_record.graduation_year,
            "registration_number": latest_record.registration_number,
            "institution": latest_record.institution.name,
        }
    return {
        "national_id": citizen.national_id,
        "full_name": citizen.user.get_full_name() or citizen.user.email,
        "otp_email": citizen.otp_email,
        "record": record_data,
    }


@role_required(User.Role.HR_MANAGER)
def certificate_file_hr(request, pk):
    """
    HR can view inline (no download button) after OTP verification of this national_id.
    """
    record = get_object_or_404(CertificateRecord, pk=pk)
    if request.session.get("verified_national_id") != record.national_id:
        return HttpResponseForbidden("OTP verification required for this record.")
    if not record.certificate_file:
        raise Http404("No certificate file uploaded.")

    response = FileResponse(record.certificate_file.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="certificate.pdf"'
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Frame-Options"] = "SAMEORIGIN"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


@role_required(User.Role.CITIZEN)
def certificate_file_citizen(request, pk):
    """
    Citizen can download their own certificate.
    """
    record = get_object_or_404(CertificateRecord, pk=pk)
    profile = getattr(request.user, "citizen_profile", None)
    if not profile or profile.national_id != record.national_id:
        return HttpResponseForbidden("Not your certificate.")
    if not record.certificate_file:
        raise Http404("No certificate file uploaded.")

    response = FileResponse(record.certificate_file.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="certificate.pdf"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    return response
