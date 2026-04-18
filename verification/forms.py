from django import forms


class OTPRequestForm(forms.Form):
    national_id = forms.CharField(max_length=20)

    def clean_national_id(self):
        national_id = self.cleaned_data["national_id"].strip()
        if not national_id.isdigit():
            raise forms.ValidationError("National ID should contain numbers only.")
        return national_id


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(max_length=6, min_length=6, strip=True)

    def clean_otp(self):
        otp = self.cleaned_data["otp"].strip()
        if not otp.isdigit():
            raise forms.ValidationError("OTP must be six numeric digits.")
        return otp
