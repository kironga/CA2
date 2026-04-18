from django import forms
from django.utils import timezone

from institutions.models import CertificateRecord


class CertificateRecordForm(forms.ModelForm):
    class Meta:
        model = CertificateRecord
        fields = (
            "national_id",
            "full_name",
            "certificate_name",
            "award_level",
            "grade",
            "graduation_year",
            "registration_number",
            "certificate_file",
        )

    def clean_national_id(self):
        national_id = self.cleaned_data["national_id"].strip()
        if not national_id.isdigit():
            raise forms.ValidationError("National ID should contain numbers only.")
        if not (6 <= len(national_id) <= 20):
            raise forms.ValidationError("National ID length is invalid.")
        return national_id

    def clean_graduation_year(self):
        year = self.cleaned_data["graduation_year"]
        current_year = timezone.now().year
        if year < 1950 or year > current_year + 1:
            raise forms.ValidationError("Graduation year is outside allowed range.")
        return year
