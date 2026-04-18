from django.conf import settings
from django.core.mail import send_mail

from citizens.models import CitizenProfile
from job_alerts.models import JobAlertDelivery


def dispatch_job_alert(alert):
    recipients = CitizenProfile.objects.select_related("user").all()
    sent_count = 0

    for citizen in recipients:
        subject = f"CA² Job Alert: {alert.title}"
        message = (
            f"Dear {citizen.user.get_full_name() or 'Citizen'},\n\n"
            f"A new opportunity has been posted.\n\n"
            f"Title: {alert.title}\n"
            f"Organization: {alert.organization}\n"
            f"Location: {alert.location or 'Not specified'}\n"
            f"Deadline: {alert.application_deadline or 'Not specified'}\n\n"
            f"Description:\n{alert.description}\n\n"
            f"More Information Link: {alert.more_info_url or 'Not provided'}\n"
            f"Application Link: {alert.application_url or 'Not provided'}\n\n"
            "You are receiving this because your email is registered on CA²."
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[citizen.otp_email],
                fail_silently=False,
            )
            JobAlertDelivery.objects.create(alert=alert, citizen=citizen, email=citizen.otp_email, status="sent")
            sent_count += 1
        except Exception as exc:  # noqa: BLE001
            JobAlertDelivery.objects.create(
                alert=alert,
                citizen=citizen,
                email=citizen.otp_email,
                status="failed",
                error_message=str(exc)[:255],
            )

    alert.recipients_count = sent_count
    alert.save(update_fields=["recipients_count"])
    return sent_count
