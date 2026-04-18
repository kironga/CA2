from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.models import User
from accounts.views import role_required
from job_alerts.forms import JobAlertForm
from job_alerts.models import JobAlert
from job_alerts.services import dispatch_job_alert


@role_required(User.Role.HR_MANAGER)
def job_alert_list(request):
    alerts = JobAlert.objects.select_related("created_by").all()
    return render(request, "job_alerts/list.html", {"alerts": alerts})


@role_required(User.Role.HR_MANAGER)
def job_alert_create(request):
    if request.method == "POST":
        form = JobAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.created_by = request.user
            alert.save()
            sent_count = dispatch_job_alert(alert)
            messages.success(request, f"Job alert created and sent to {sent_count} citizen(s).")
            return redirect("job_alert_list")
    else:
        form = JobAlertForm()
    return render(request, "job_alerts/form.html", {"form": form})


@role_required(User.Role.CITIZEN)
def citizen_job_alerts(request):
    alerts = JobAlert.objects.all()[:30]
    return render(request, "job_alerts/citizen_list.html", {"alerts": alerts})
