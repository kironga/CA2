from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.GOVERNMENT_ADMIN)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        GOVERNMENT_ADMIN = "GOV_ADMIN", "Government Admin"
        INSTITUTION_ADMIN = "INST_ADMIN", "Institution Admin"
        HR_MANAGER = "HR_MANAGER", "HR Manager"
        CITIZEN = "CITIZEN", "Citizen"

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


class Business(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.code})"


class HRProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="hr_profile")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="hr_managers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("business__name", "user__email")

    def __str__(self):
        return f"{self.user.email} -> {self.business.code}"


class PasswordResetRequest(models.Model):
    """
    One-time code used to reset a user's password via email.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_requests")
    code_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def is_expired(self):
        from django.utils import timezone

        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Password reset for {self.user.email} at {self.created_at:%Y-%m-%d %H:%M}"
