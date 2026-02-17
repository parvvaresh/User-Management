import random
import logging
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics, permissions, status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ForgotPasswordSerializer,
    PasswordResetSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    CredentialsUpdateSerializer,
    OTPStartSerializer,
    OTPVerifySerializer,
)
from .models import Profile, PasswordResetToken
from .sms_service import sms_service

logger = logging.getLogger(__name__)
User = get_user_model()


# ---- JWT Configuration with phone_number ----
class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends JWT TokenObtainPairSerializer to include phone_number in token payload.
    """

    @classmethod
    def get_token(cls, user):
        """Add phone_number to JWT token claims."""
        token = super().get_token(user)
        token["phone_number"] = user.phone_number
        return token

    def validate(self, attrs):
        """Map phone_number field to expected username field."""
        if "phone_number" in self.initial_data and "username" not in attrs:
            attrs["username"] = self.initial_data.get("phone_number")
        return super().validate(attrs)


class PhoneTokenObtainPairView(TokenObtainPairView):
    """JWT token obtain view using phone_number and password."""
    permission_classes = [permissions.AllowAny]
    serializer_class = PhoneTokenObtainPairSerializer


# ---- User Registration ----
class RegisterView(generics.CreateAPIView):
    """
    API view for user registration.
    Accepts phone_number, username, password and creates a new user account.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        """Create new user and return in response."""
        response = super().create(request, *args, **kwargs)
        return Response(
            {
                "detail": "User registered successfully. You can now log in.",
                "user": response.data,
            },
            status=status.HTTP_201_CREATED,
        )


# ---- User Login with Phone and Password ----
class LoginView(generics.GenericAPIView):
    """
    API view for user login using phone_number and password.
    Returns JWT access and refresh tokens on successful authentication.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        """
        Handle login request.
        Validates credentials and returns JWT tokens.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "phone_number": user.phone_number,
                    "username": user.username,
                },
            },
            status=status.HTTP_200_OK,
        )


# ---- Forgot Password (via SMS) ----
class ForgotPasswordView(generics.GenericAPIView):
    """
    API view for initiating password reset process.
    Sends SMS with password reset token to user's registered phone number.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request, *args, **kwargs):
        """
        Handle forgot password request.
        Generates reset token and sends SMS to user.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]

        try:
            user = User.objects.get(phone_number=phone_number)

            # Delete any existing reset tokens for this user
            PasswordResetToken.objects.filter(user=user).delete()

            # Generate new reset token
            token_value = PasswordResetToken.generate_token()
            expires_at = timezone.now() + timedelta(minutes=15)

            reset_token = PasswordResetToken.objects.create(
                user=user,
                token=token_value,
                expires_at=expires_at,
            )

            # Send SMS with reset token
            success, message_id = sms_service.send_password_reset_sms(
                phone_number, token_value
            )

            if success:
                logger.info(
                    f"Password reset SMS sent to {phone_number} (ID: {message_id})"
                )
                return Response(
                    {
                        "detail": "Password reset code sent to your phone number.",
                        "message_id": message_id,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                # Log error but return success to avoid revealing SMS failures
                logger.error(
                    f"Failed to send SMS to {phone_number}: {message_id}"
                )
                return Response(
                    {
                        "detail": "Password reset code sent to your phone number.",
                    },
                    status=status.HTTP_200_OK,
                )

        except User.DoesNotExist:
            # Return generic success message for security
            return Response(
                {
                    "detail": "If an account exists with this phone number, a reset code has been sent.",
                },
                status=status.HTTP_200_OK,
            )


# ---- Reset Password with Token ----
class ResetPasswordView(generics.GenericAPIView):
    """
    API view for resetting password using reset token.
    Validates token and updates user's password.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetSerializer

    def post(self, request, *args, **kwargs):
        """
        Handle password reset request.
        Validates token and updates password.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        reset_token = serializer.validated_data["reset_token"]
        new_password = serializer.validated_data["new_password"]

        # Update password
        user.set_password(new_password)
        user.save()

        # Mark token as used
        reset_token.mark_as_used()

        logger.info(f"Password reset successful for {user.phone_number}")

        return Response(
            {
                "detail": "Password has been reset successfully. You can now log in with your new password.",
            },
            status=status.HTTP_200_OK,
        )


# ---- OTP-based Login (Alternative) ----
def _otp_key(phone: str) -> str:
    """Generate cache key for OTP code."""
    return f"otp:{phone}"


class OTPStartView(generics.GenericAPIView):
    """
    API view for initiating OTP-based login.
    Generates OTP code and sends to user's phone.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPStartSerializer

    def post(self, request):
        """
        Handle OTP start request.
        Generates and sends OTP code.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone_number"]
        otp = f"{random.randint(0, 999999):06d}"

        # Store OTP in cache for 5 minutes
        cache.set(_otp_key(phone), otp, timeout=300)

        # Send OTP via SMS
        sms_service.send_login_otp(phone, otp)

        # Log for development (remove in production)
        logger.warning(f"[DEV] OTP for {phone} is {otp}")

        return Response(
            {"detail": "OTP sent to your phone number."},
            status=status.HTTP_200_OK,
        )


class OTPVerifyView(generics.GenericAPIView):
    """
    API view for verifying OTP code.
    Validates OTP and returns JWT tokens on success.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPVerifySerializer

    def post(self, request):
        """
        Handle OTP verification.
        Validates OTP and returns JWT tokens.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]

        # Verify OTP
        expected_otp = cache.get(_otp_key(phone))
        if not expected_otp or expected_otp != otp:
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete used OTP
        cache.delete(_otp_key(phone))

        # Get or create user
        user, created = User.objects.get_or_create(phone_number=phone)

        if created:
            # Create profile for new user
            Profile.objects.create(user=user)
            logger.info(f"New user created via OTP: {phone}")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "phone_number": user.phone_number,
                    "username": user.username,
                },
            },
            status=status.HTTP_200_OK,
        )


# ---- Profile Management ----
class ProfileViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    ViewSet for managing user profiles.
    Allows authenticated users to view and update their profile.
    """
    queryset = Profile.objects.select_related("user").all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        """
        Get or update the current user's profile.
        GET /api/profiles/me/ - Get profile
        PATCH /api/profiles/me/ - Update profile
        """
        profile = request.user.profile
        if request.method == "GET":
            return Response(ProfileSerializer(profile).data)

        serializer = ProfileUpdateSerializer(
            instance=profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(ProfileSerializer(profile).data)


class CredentialsView(generics.GenericAPIView):
    """
    API view for updating user credentials.
    Allows authenticated users to change username and password.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CredentialsUpdateSerializer

    def patch(self, request):
        """Update user credentials (username, password)."""
        serializer = self.get_serializer(
            data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)

        return Response({"detail": "Credentials updated successfully."})
class OTPStartView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPStartSerializer

    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data["phone_number"]
        otp = f"{random.randint(0, 999999):06d}"
        cache.set(_otp_key(phone), otp, timeout=300)  # 5 minutes
        logger.warning("DEV OTP for %s is %s", phone, otp)  # shows in terminal
        return Response(
            {"detail": "OTP generated (check server terminal)."}, status=200
        )


class OTPVerifyView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OTPVerifySerializer

    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        phone = s.validated_data["phone_number"]
        otp = s.validated_data["otp"]
        expected = cache.get(_otp_key(phone))
        if not expected or expected != otp:
            return Response({"detail": "Invalid OTP."}, status=400)
        cache.delete(_otp_key(phone))
        user, _ = User.objects.get_or_create(phone_number=phone)
        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)}, status=200
        )


# ---- Registration + Profiles ----
class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class ProfileViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Profile.objects.select_related("user").all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    @action(detail=False, methods=["get", "patch"])  # /api/profiles/me/
    def me(self, request):
        profile = request.user.profile
        if request.method == "GET":
            return Response(ProfileSerializer(profile).data)
        s = ProfileUpdateSerializer(instance=profile, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(ProfileSerializer(profile).data)


class CredentialsView(generics.GenericAPIView):
    serializer_class = CredentialsUpdateSerializer

    def patch(self, request):
        s = self.get_serializer(
            data=request.data, partial=True, context={"request": request}
        )
        s.is_valid(raise_exception=True)
        s.update(request.user, s.validated_data)
        return Response({"detail": "Credentials updated."})
