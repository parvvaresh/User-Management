from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import Profile, PasswordResetToken

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Validates phone number and password, creates a new user with profile.
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("phone_number", "username", "password", "password_confirm")
        extra_kwargs = {
            "username": {"required": False},
        }

    def validate(self, data):
        """
        Validate that passwords match.
        """
        if data["password"] != data.pop("password_confirm"):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def validate_phone_number(self, value):
        """
        Validate that phone number is not already registered.
        """
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value

    def create(self, validated_data):
        """
        Create user with password. Profile is automatically created by signal.
        """
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        # Profile is automatically created by post_save signal
        # No need to manually create it here

        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login with phone number and password.
    Returns JWT access and refresh tokens on successful authentication.
    """
    phone_number = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    def validate(self, data):
        """
        Validate phone number and password.
        """
        phone_number = data.get("phone_number")
        password = data.get("password")

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid phone number or password.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid phone number or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        data["user"] = user
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Serializer for initiating forgot password flow.
    Takes phone number and sends SMS with reset token.
    """
    phone_number = serializers.CharField()

    def validate_phone_number(self, value):
        """
        Validate that user with this phone number exists.
        """
        try:
            User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this phone number.")
        return value


class PasswordResetSerializer(serializers.Serializer):
    """
    Serializer for resetting password using reset token.
    Validates the token and updates user password.
    """
    phone_number = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    def validate(self, data):
        """
        Validate reset token and password confirmation.
        """
        # Check passwords match
        if data["new_password"] != data.pop("new_password_confirm"):
            raise serializers.ValidationError("Passwords do not match.")

        # Get user and token
        try:
            user = User.objects.get(phone_number=data["phone_number"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid phone number.")

        try:
            reset_token = PasswordResetToken.objects.get(
                user=user,
                token=data["token"]
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired reset token.")

        # Validate token
        if not reset_token.is_valid():
            raise serializers.ValidationError("Reset token has expired or already been used.")

        data["user"] = user
        data["reset_token"] = reset_token
        return data


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for displaying user profile information."""
    phone_number = serializers.CharField(source="user.phone_number", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Profile
        fields = ("phone_number", "username", "full_name", "bio", "avatar_url")


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information."""
    class Meta:
        model = Profile
        fields = ("full_name", "bio", "avatar_url")


class CredentialsUpdateSerializer(serializers.Serializer):
    """Serializer for updating user credentials (username, password)."""
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, write_only=True, min_length=8)

    def validate_username(self, value):
        """Validate that new username is not already taken."""
        user_model = self.context["request"].user.__class__
        if (
            value
            and user_model.objects.filter(username=value)
            .exclude(pk=self.context["request"].user.pk)
            .exists()
        ):
            raise serializers.ValidationError("Username already taken.")
        return value

    def update(self, instance, validated):
        """Update user credentials."""
        if "username" in validated:
            instance.username = validated["username"] or None
        if "password" in validated:
            instance.set_password(validated["password"])
        instance.save()
        return instance


class OTPStartSerializer(serializers.Serializer):
    """Serializer for initiating OTP-based login."""
    phone_number = serializers.CharField()


class OTPVerifySerializer(serializers.Serializer):
    """Serializer for verifying OTP code during login."""
    phone_number = serializers.CharField()
    otp = serializers.CharField()
