from django import forms

from citizens.models import CitizenProfile


class CitizenProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = CitizenProfile
        fields = ("national_id", "otp_email", "passport_photo")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name

    def clean_national_id(self):
        national_id = self.cleaned_data["national_id"].strip()
        qs = CitizenProfile.objects.filter(national_id=national_id).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This National ID is already linked to another account.")
        return national_id

    def clean_otp_email(self):
        email = self.cleaned_data["otp_email"].strip().lower()
        qs = CitizenProfile.objects.filter(otp_email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already linked to another account.")
        return email

    def clean_passport_photo(self):
        uploaded = self.cleaned_data.get("passport_photo")
        if not uploaded:
            return uploaded

        max_size = 4 * 1024 * 1024
        if uploaded.size > max_size:
            raise forms.ValidationError("Passport photo must be 4MB or less.")

        content_type = getattr(uploaded, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            raise forms.ValidationError("Please upload a valid image file.")
        return uploaded

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"].strip()
        self.user.last_name = self.cleaned_data["last_name"].strip()
        self.user.email = self.cleaned_data["otp_email"].strip().lower()
        if commit:
            self.user.save()
            profile.save()
        return profile
