from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.core.validators import RegexValidator
from django.utils import timezone
import secrets


_phone_validator = RegexValidator(
    regex=r"^\+?\d{8,15}$",
    message="Enter a valid phone number (8-15 digits, optional +).",
)


class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("The phone number must be set")
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(
        max_length=11, unique=True, validators=[_phone_validator]
    )
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.phone_number


class Profile(models.Model):
    """User profile model for storing additional user information."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)

    def __str__(self):
        return f"Profile of {self.user.phone_number}"


class PasswordResetToken(models.Model):
    """
    Model for storing password reset tokens.
    Each token is associated with a user and expires after a set time.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name="password_reset_token"
    )
    token = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"

    def __str__(self):
        return f"Reset token for {self.user.phone_number}"

    @staticmethod
    def generate_token():
        """
        Generate a secure random token for password reset.

        Returns:
            str: 32-character hexadecimal token
        """
        return secrets.token_hex(16)

    def is_valid(self):
        """
        Check if the token is still valid (not expired and not used).

        Returns:
            bool: True if token is valid, False otherwise
        """
        return timezone.now() < self.expires_at and not self.is_used

    def mark_as_used(self):
        """Mark the token as used after password reset."""
        self.is_used = True
        self.save(update_fields=["is_used"])
