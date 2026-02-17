from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    LoginView,
    PhoneTokenObtainPairView,
    ForgotPasswordView,
    ResetPasswordView,
    OTPStartView,
    OTPVerifyView,
    ProfileViewSet,
    CredentialsView,
)

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profiles")

urlpatterns = [
    # Authentication endpoints
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/", PhoneTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    # OTP-based authentication (alternative)
    path("auth/otp/start/", OTPStartView.as_view(), name="otp_start"),
    path("auth/otp/verify/", OTPVerifyView.as_view(), name="otp_verify"),
    # User profile and credentials management
    path("me/credentials/", CredentialsView.as_view(), name="me_credentials"),
    path("", include(router.urls)),
]