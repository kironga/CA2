from django import forms

from job_alerts.models import JobAlert


class JobAlertForm(forms.ModelForm):
    class Meta:
        model = JobAlert
        fields = (
            "title",
            "organization",
            "location",
            "application_deadline",
            "description",
            "more_info_url",
            "application_url",
        )
        widgets = {
            "application_deadline": forms.DateInput(attrs={"type": "date"}),
            "more_info_url": forms.URLInput(attrs={"placeholder": "https://..."}),
            "application_url": forms.URLInput(attrs={"placeholder": "https://..."}),
        }
