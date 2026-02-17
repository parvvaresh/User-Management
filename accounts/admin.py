from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from .models import User, Profile, PasswordResetToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin interface for User model.
    Displays user list with phone number and status information.
    """
    list_display = ("id", "phone_number", "username", "is_staff", "is_active")
    ordering = ("phone_number",)

    fieldsets = (
        (None, {"fields": ("phone_number", "username", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"fields": ("phone_number", "password1", "password2")}),)
    search_fields = ("phone_number", "username")
    readonly_fields = ("last_login", "date_joined")
    list_filter = ("is_active", "is_staff", "is_superuser", "date_joined")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for Profile model.
    Displays user profiles with contact name and edit capabilities.
    """
    list_display = ("id", "user", "full_name")
    search_fields = ("user__phone_number", "full_name")
    readonly_fields = ("user",)
    fields = ("user", "full_name", "bio", "avatar_url")


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for PasswordResetToken model.
    Displays password reset requests and their status.
    """
    list_display = ("id", "user", "is_valid", "created_at", "expires_at", "is_used")
    search_fields = ("user__phone_number", "token")
    readonly_fields = ("token", "created_at", "expires_at", "user")
    fields = ("user", "token", "created_at", "expires_at", "is_used")
    list_filter = ("is_used", "created_at", "expires_at")
    ordering = ("-created_at",)

    def is_valid(self, obj):
        """Display token validity status as boolean."""
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = "Valid"

    def has_add_permission(self, request):
        """Prevent manual token creation through admin (tokens are generated via API)."""
        return False
