"""
Comprehensive test suite for User Management System.
Tests cover:
- User Registration
- User Login (password-based)
- Forgot Password
- Password Reset
- OTP-based Authentication
- Profile Management
- Credentials Update
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from .models import Profile, PasswordResetToken
from .sms_service import sms_service

User = get_user_model()


# ============================================================================
# USER REGISTRATION TESTS
# ============================================================================
class UserRegistrationTestCase(TestCase):
    """
    Test suite for user registration functionality.
    Covers successful registration and various validation failures.
    """

    def setUp(self):
        """Initialize test client and endpoint URLs."""
        self.client = APIClient()
        self.register_url = "/accounts/auth/register/"

    def test_successful_registration(self):
        """
        Test Case: User can successfully register with valid data.
        Expected: User account and profile are created, response status is 201.
        """
        data = {
            "phone_number": "+989101234567",
            "username": "testuser",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        }
        response = self.client.post(self.register_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert user was created
        self.assertTrue(
            User.objects.filter(phone_number=data["phone_number"]).exists()
        )

        # Assert profile was automatically created
        user = User.objects.get(phone_number=data["phone_number"])
        self.assertTrue(Profile.objects.filter(user=user).exists())

        # Assert response contains correct data
        self.assertIn("user", response.data)
        self.assertEqual(
            response.data["user"]["phone_number"], data["phone_number"]
        )

    def test_registration_password_mismatch(self):
        """
        Test Case: Registration fails when password and confirm don't match.
        Expected: Response status is 400, no user is created.
        """
        data = {
            "phone_number": "+989101234567",
            "username": "testuser",
            "password": "SecurePass123!",
            "password_confirm": "DifferentPass123!",
        }
        response = self.client.post(self.register_url, data, format="json")

        # Assert response status is 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert user was NOT created
        self.assertFalse(
            User.objects.filter(phone_number=data["phone_number"]).exists()
        )

    def test_registration_duplicate_phone_number(self):
        """
        Test Case: Registration fails when phone number is already registered.
        Expected: Response status is 400, no duplicate user is created.
        """
        # Create first user
        User.objects.create_user(
            phone_number="+989101234567", password="TestPass123!"
        )

        # Try to register with same phone number
        data = {
            "phone_number": "+989101234567",
            "username": "newuser",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        }
        response = self.client.post(self.register_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert only one user exists
        self.assertEqual(
            User.objects.filter(phone_number="+989101234567").count(), 1
        )

    def test_registration_short_password(self):
        """
        Test Case: Registration fails when password is too short.
        Expected: Response status is 400, validation error for min length.
        """
        data = {
            "phone_number": "+989101234567",
            "username": "testuser",
            "password": "Short",
            "password_confirm": "Short",
        }
        response = self.client.post(self.register_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_missing_phone_number(self):
        """
        Test Case: Registration fails when phone number is missing.
        Expected: Response status is 400, phone_number is required.
        """
        data = {
            "username": "testuser",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        }
        response = self.client.post(self.register_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_missing_password(self):
        """
        Test Case: Registration fails when password is missing.
        Expected: Response status is 400, password is required.
        """
        data = {
            "phone_number": "+989101234567",
            "username": "testuser",
            "password_confirm": "SecurePass123!",
        }
        response = self.client.post(self.register_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# USER LOGIN TESTS
# ============================================================================
class UserLoginTestCase(TestCase):
    """
    Test suite for user login functionality.
    Covers successful authentication and various failure scenarios.
    """

    def setUp(self):
        """Initialize test client, endpoint URLs, and test user."""
        self.client = APIClient()
        self.login_url = "/accounts/auth/login/"

        # Create test user with known credentials
        self.user = User.objects.create_user(
            phone_number="+989101234567",
            password="TestPass123!",
            username="testuser",
        )
        Profile.objects.create(user=self.user)

    def test_successful_login(self):
        """
        Test Case: User can log in with correct phone number and password.
        Expected: Response status is 200, JWT tokens are returned.
        """
        data = {
            "phone_number": "+989101234567",
            "password": "TestPass123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert JWT tokens are returned
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Assert user data is included
        self.assertIn("user", response.data)
        self.assertEqual(
            response.data["user"]["phone_number"], "+989101234567"
        )

    def test_login_invalid_password(self):
        """
        Test Case: Login fails with incorrect password.
        Expected: Response status is 400, no tokens are returned.
        """
        data = {
            "phone_number": "+989101234567",
            "password": "WrongPassword123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Assert no tokens in response
        self.assertNotIn("access", response.data)

    def test_login_nonexistent_user(self):
        """
        Test Case: Login fails when user doesn't exist.
        Expected: Response status is 400, generic error message for security.
        """
        data = {
            "phone_number": "+989199999999",
            "password": "TestPass123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user(self):
        """
        Test Case: Login fails for deactivated user accounts.
        Expected: Response status is 400, account is marked as inactive.
        """
        # Deactivate user account
        self.user.is_active = False
        self.user.save()

        data = {
            "phone_number": "+989101234567",
            "password": "TestPass123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_phone_number(self):
        """
        Test Case: Login fails when phone number is not provided.
        Expected: Response status is 400, phone_number required.
        """
        data = {
            "password": "TestPass123!",
        }
        response = self.client.post(self.login_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_password(self):
        """
        Test Case: Login fails when password is not provided.
        Expected: Response status is 400, password required.
        """
        data = {
            "phone_number": "+989101234567",
        }
        response = self.client.post(self.login_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# FORGOT PASSWORD TESTS
# ============================================================================
class ForgotPasswordTestCase(TestCase):
    """
    Test suite for forgot password functionality.
    Covers password reset token generation and SMS sending.
    """

    def setUp(self):
        """Initialize test client, endpoint URLs, and test user."""
        self.client = APIClient()
        self.forgot_password_url = "/accounts/auth/forgot-password/"

        # Create test user
        self.user = User.objects.create_user(
            phone_number="+989101234567",
            password="TestPass123!",
            username="testuser",
        )
        Profile.objects.create(user=self.user)

    def test_forgot_password_valid_phone(self):
        """
        Test Case: Forgot password request with valid phone number.
        Expected: Reset token is created, SMS is sent, response status is 200.
        """
        data = {"phone_number": "+989101234567"}
        response = self.client.post(self.forgot_password_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert reset token was created
        self.assertTrue(
            PasswordResetToken.objects.filter(user=self.user).exists()
        )

        # Assert response contains confirmation message
        self.assertIn("detail", response.data)

    def test_forgot_password_nonexistent_phone(self):
        """
        Test Case: Forgot password request with non-existent phone number.
        Expected: Response is generic (no account exists), status is 200 for security.
        """
        data = {"phone_number": "+989199999999"}
        response = self.client.post(self.forgot_password_url, data, format="json")

        # Assert response status is still 200 (for security - don't reveal if user exists)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_forgot_password_multiple_requests(self):
        """
        Test Case: Multiple forgot password requests from same user.
        Expected: Old token is deleted, new token is created.
        """
        # First request
        data = {"phone_number": "+989101234567"}
        response1 = self.client.post(self.forgot_password_url, data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        first_token = PasswordResetToken.objects.get(user=self.user).token

        # Second request
        response2 = self.client.post(self.forgot_password_url, data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        second_token = PasswordResetToken.objects.get(user=self.user).token

        # Assert tokens are different
        self.assertNotEqual(first_token, second_token)

        # Assert only one token exists
        self.assertEqual(
            PasswordResetToken.objects.filter(user=self.user).count(), 1
        )

    def test_forgot_password_missing_phone(self):
        """
        Test Case: Forgot password request without phone number.
        Expected: Response status is 400, phone_number required.
        """
        data = {}
        response = self.client.post(self.forgot_password_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# PASSWORD RESET TESTS
# ============================================================================
class PasswordResetTestCase(TestCase):
    """
    Test suite for password reset functionality.
    Covers token validation and password update.
    """

    def setUp(self):
        """Initialize test client, endpoint URLs, and test user."""
        self.client = APIClient()
        self.reset_password_url = "/accounts/auth/reset-password/"

        # Create test user
        self.user = User.objects.create_user(
            phone_number="+989101234567",
            password="TestPass123!",
            username="testuser",
        )
        Profile.objects.create(user=self.user)

    def test_successful_password_reset(self):
        """
        Test Case: User can successfully reset password with valid token.
        Expected: Password is updated, token is marked as used, response status is 200.
        """
        # Create valid reset token
        reset_token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=15)
        PasswordResetToken.objects.create(
            user=self.user,
            token=reset_token,
            expires_at=expires_at,
        )

        # Reset password
        data = {
            "phone_number": "+989101234567",
            "token": reset_token,
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!",
        }
        response = self.client.post(self.reset_password_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh user from database
        self.user.refresh_from_db()

        # Assert password was changed
        self.assertTrue(self.user.check_password("NewSecurePass123!"))

        # Assert token was marked as used
        token_obj = PasswordResetToken.objects.get(user=self.user)
        self.assertTrue(token_obj.is_used)

    def test_password_reset_invalid_token(self):
        """
        Test Case: Password reset fails with invalid token.
        Expected: Response status is 400, no password change occurs.
        """
        data = {
            "phone_number": "+989101234567",
            "token": "invalid-token-12345678",
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!",
        }
        response = self.client.post(self.reset_password_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Refresh user and assert password wasn't changed
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password("NewSecurePass123!"))

    def test_password_reset_expired_token(self):
        """
        Test Case: Password reset fails when token has expired.
        Expected: Response status is 400, token is no longer valid.
        """
        # Create expired reset token (15 minutes ago)
        reset_token = PasswordResetToken.generate_token()
        expires_at = timezone.now() - timedelta(minutes=5)
        PasswordResetToken.objects.create(
            user=self.user,
            token=reset_token,
            expires_at=expires_at,
        )

        data = {
            "phone_number": "+989101234567",
            "token": reset_token,
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!",
        }
        response = self.client.post(self.reset_password_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", response.data["detail"].lower())

    def test_password_reset_already_used_token(self):
        """
        Test Case: Password reset fails with already-used token.
        Expected: Response status is 400, tokens can only be used once.
        """
        # Create and use a token
        reset_token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=15)
        token_obj = PasswordResetToken.objects.create(
            user=self.user,
            token=reset_token,
            expires_at=expires_at,
        )
        token_obj.mark_as_used()

        data = {
            "phone_number": "+989101234567",
            "token": reset_token,
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!",
        }
        response = self.client.post(self.reset_password_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_password_mismatch(self):
        """
        Test Case: Password reset fails when passwords don't match.
        Expected: Response status is 400, no password change occurs.
        """
        # Create valid token
        reset_token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=15)
        PasswordResetToken.objects.create(
            user=self.user,
            token=reset_token,
            expires_at=expires_at,
        )

        data = {
            "phone_number": "+989101234567",
            "token": reset_token,
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "DifferentPass123!",
        }
        response = self.client.post(self.reset_password_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Refresh user and assert password wasn't changed
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password("NewSecurePass123!"))

    def test_password_reset_short_password(self):
        """
        Test Case: Password reset fails with password shorter than 8 characters.
        Expected: Response status is 400, validation error.
        """
        # Create valid token
        reset_token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=15)
        PasswordResetToken.objects.create(
            user=self.user,
            token=reset_token,
            expires_at=expires_at,
        )

        data = {
            "phone_number": "+989101234567",
            "token": reset_token,
            "new_password": "Short",
            "new_password_confirm": "Short",
        }
        response = self.client.post(self.reset_password_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# OTP AUTHENTICATION TESTS
# ============================================================================
class OTPAuthenticationTestCase(TestCase):
    """
    Test suite for OTP-based authentication.
    Covers OTP generation, verification, and user creation.
    """

    def setUp(self):
        """Initialize test client and endpoint URLs."""
        self.client = APIClient()
        self.otp_start_url = "/accounts/auth/otp/start/"
        self.otp_verify_url = "/accounts/auth/otp/verify/"

    def test_otp_start_success(self):
        """
        Test Case: OTP generation for valid phone number.
        Expected: OTP is sent, response status is 200.
        """
        data = {"phone_number": "+989101234567"}
        response = self.client.post(self.otp_start_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert success message
        self.assertIn("detail", response.data)

    def test_otp_verify_success_new_user(self):
        """
        Test Case: OTP verification creates new user account.
        Expected: User and profile are created, JWT tokens returned, status 200.
        """
        from django.core.cache import cache

        phone = "+989101234567"
        otp_code = "123456"

        # Set OTP in cache
        cache.set(f"otp:{phone}", otp_code, timeout=300)

        # Verify OTP
        data = {
            "phone_number": phone,
            "otp": otp_code,
        }
        response = self.client.post(self.otp_verify_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert JWT tokens are returned
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Assert user was created
        self.assertTrue(User.objects.filter(phone_number=phone).exists())

        # Assert profile was created
        user = User.objects.get(phone_number=phone)
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_otp_verify_success_existing_user(self):
        """
        Test Case: OTP verification logs in existing user.
        Expected: JWT tokens returned for existing account, status 200.
        """
        from django.core.cache import cache

        # Create existing user
        user = User.objects.create_user(phone_number="+989101234567")
        Profile.objects.create(user=user)

        phone = "+989101234567"
        otp_code = "123456"

        # Set OTP in cache
        cache.set(f"otp:{phone}", otp_code, timeout=300)

        # Verify OTP
        data = {
            "phone_number": phone,
            "otp": otp_code,
        }
        response = self.client.post(self.otp_verify_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert JWT tokens are returned
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_otp_verify_invalid_otp(self):
        """
        Test Case: OTP verification fails with incorrect OTP code.
        Expected: Response status is 400, no tokens returned.
        """
        from django.core.cache import cache

        phone = "+989101234567"
        correct_otp = "123456"

        # Set correct OTP in cache
        cache.set(f"otp:{phone}", correct_otp, timeout=300)

        # Try to verify with wrong OTP
        data = {
            "phone_number": phone,
            "otp": "999999",
        }
        response = self.client.post(self.otp_verify_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_otp_verify_expired_otp(self):
        """
        Test Case: OTP verification fails when OTP has expired.
        Expected: Response status is 400, OTP not in cache.
        """
        phone = "+989101234567"

        # Don't set OTP in cache (simulates expiration)
        data = {
            "phone_number": phone,
            "otp": "123456",
        }
        response = self.client.post(self.otp_verify_url, data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================================
# PROFILE MANAGEMENT TESTS
# ============================================================================
class ProfileManagementTestCase(TestCase):
    """
    Test suite for user profile management.
    Covers viewing and updating profile information.
    """

    def setUp(self):
        """Initialize test client and setup authenticated user."""
        self.client = APIClient()

        # Create test user and profile
        self.user = User.objects.create_user(
            phone_number="+989101234567",
            password="TestPass123!",
            username="testuser",
        )
        self.profile = Profile.objects.create(user=self.user)

        # Authenticate client with JWT token
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_get_user_profile(self):
        """
        Test Case: Authenticated user can retrieve their profile.
        Expected: Profile data returned, response status is 200.
        """
        response = self.client.get("/accounts/profiles/me/")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert profile data is correct
        self.assertEqual(response.data["phone_number"], "+989101234567")
        self.assertEqual(response.data["username"], "testuser")

    def test_update_user_profile(self):
        """
        Test Case: User can update profile information.
        Expected: Profile fields updated, response status is 200.
        """
        data = {
            "full_name": "John Doe",
            "bio": "Software Developer from Iran",
            "avatar_url": "https://example.com/avatar.jpg",
        }
        response = self.client.patch("/accounts/profiles/me/", data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh profile from database
        self.profile.refresh_from_db()

        # Assert all fields were updated
        self.assertEqual(self.profile.full_name, "John Doe")
        self.assertEqual(self.profile.bio, "Software Developer from Iran")
        self.assertEqual(self.profile.avatar_url, "https://example.com/avatar.jpg")

    def test_partial_profile_update(self):
        """
        Test Case: User can update only some profile fields.
        Expected: Only specified fields updated, others unchanged.
        """
        data = {"full_name": "Jane Doe"}
        response = self.client.patch("/accounts/profiles/me/", data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh from database
        self.profile.refresh_from_db()

        # Assert only full_name was updated
        self.assertEqual(self.profile.full_name, "Jane Doe")
        self.assertEqual(self.profile.bio, "")  # Should be empty

    def test_profile_requires_authentication(self):
        """
        Test Case: Profile endpoints require authentication.
        Expected: Unauthenticated requests return 401 Unauthorized.
        """
        # Create unauthenticated client
        unauth_client = APIClient()

        response = unauth_client.get("/accounts/profiles/me/")

        # Assert response status is 401
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ============================================================================
# CREDENTIALS UPDATE TESTS
# ============================================================================
class CredentialsUpdateTestCase(TestCase):
    """
    Test suite for updating user credentials.
    Covers username and password changes.
    """

    def setUp(self):
        """Initialize test client and setup authenticated user."""
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            phone_number="+989101234567",
            password="TestPass123!",
            username="testuser",
        )
        Profile.objects.create(user=self.user)

        # Authenticate client
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_update_password(self):
        """
        Test Case: User can update their password.
        Expected: Password changed, old password no longer works.
        """
        data = {"password": "NewSecurePass123!"}
        response = self.client.patch("/accounts/me/credentials/", data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh user
        self.user.refresh_from_db()

        # Assert new password works
        self.assertTrue(self.user.check_password("NewSecurePass123!"))

        # Assert old password doesn't work
        self.assertFalse(self.user.check_password("TestPass123!"))

    def test_update_username(self):
        """
        Test Case: User can update their username.
        Expected: Username changed, is unique.
        """
        data = {"username": "newusername"}
        response = self.client.patch("/accounts/me/credentials/", data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh user
        self.user.refresh_from_db()

        # Assert username was updated
        self.assertEqual(self.user.username, "newusername")

    def test_update_both_credentials(self):
        """
        Test Case: User can update both username and password at once.
        Expected: Both fields updated successfully.
        """
        data = {
            "username": "newusername",
            "password": "NewSecurePass123!",
        }
        response = self.client.patch("/accounts/me/credentials/", data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh user
        self.user.refresh_from_db()

        # Assert both were updated
        self.assertEqual(self.user.username, "newusername")
        self.assertTrue(self.user.check_password("NewSecurePass123!"))

    def test_update_duplicate_username(self):
        """
        Test Case: User cannot update to a username that already exists.
        Expected: Response status is 400, validation error.
        """
        # Create another user
        other_user = User.objects.create_user(
            phone_number="+989102222222", username="otheruser"
        )

        data = {"username": "otheruser"}
        response = self.client.patch("/accounts/me/credentials/", data, format="json")

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Refresh user and assert username unchanged
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "testuser")

    def test_credentials_update_requires_authentication(self):
        """
        Test Case: Credentials update requires authentication.
        Expected: Unauthenticated requests return 401 Unauthorized.
        """
        # Create unauthenticated client
        unauth_client = APIClient()

        data = {"password": "NewPass123!"}
        response = unauth_client.patch(
            "/accounts/me/credentials/", data, format="json"
        )

        # Assert response status
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ============================================================================
# PASSWORD RESET TOKEN MODEL TESTS
# ============================================================================
class PasswordResetTokenModelTestCase(TestCase):
    """
    Test suite for PasswordResetToken model.
    Covers token generation and validation logic.
    """

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            phone_number="+989101234567", password="TestPass123!"
        )

    def test_generate_token(self):
        """
        Test Case: Token generation produces valid hex string.
        Expected: Token is 32 characters, valid hexadecimal.
        """
        token = PasswordResetToken.generate_token()

        # Assert token is 32 characters
        self.assertEqual(len(token), 32)

        # Assert token is valid hexadecimal
        try:
            int(token, 16)
        except ValueError:
            self.fail("Generated token is not valid hexadecimal")

    def test_token_is_valid(self):
        """
        Test Case: Valid token passes validation.
        Expected: Token is not expired and not used.
        """
        token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=15)
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token=token,
            expires_at=expires_at,
        )

        # Assert token is valid
        self.assertTrue(reset_token.is_valid())

    def test_token_invalid_when_expired(self):
        """
        Test Case: Expired token fails validation.
        Expected: Token with past expiration time is invalid.
        """
        token = PasswordResetToken.generate_token()
        expires_at = timezone.now() - timedelta(minutes=5)
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token=token,
            expires_at=expires_at,
        )

        # Assert token is invalid
        self.assertFalse(reset_token.is_valid())

    def test_token_invalid_when_used(self):
        """
        Test Case: Used token fails validation.
        Expected: Token marked as used becomes invalid.
        """
        token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=15)
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token=token,
            expires_at=expires_at,
        )
        reset_token.mark_as_used()

        # Assert token is invalid
        self.assertFalse(reset_token.is_valid())

    def test_mark_token_as_used(self):
        """
        Test Case: Token can be marked as used.
        Expected: is_used field is updated in database.
        """
        token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timedelta(minutes=15)
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token=token,
            expires_at=expires_at,
        )

        # Assert token is initially not used
        self.assertFalse(reset_token.is_used)

        # Mark as used
        reset_token.mark_as_used()

        # Refresh from database
        reset_token.refresh_from_db()

        # Assert is_used is True
        self.assertTrue(reset_token.is_used)


# ============================================================================
# SMS SERVICE TESTS
# ============================================================================
class SMSServiceTestCase(TestCase):
    """
    Test suite for SMS service functionality.
    Covers SMS sending for OTP and password reset codes.
    """

    def test_send_sms_success(self):
        """
        Test Case: SMS can be sent successfully via mock provider.
        Expected: Response indicates success, message ID returned.
        """
        success, message_id = sms_service.send_sms(
            "+989101234567", "Test message"
        )

        # Assert sending was successful
        self.assertTrue(success)

        # Assert message ID is returned
        self.assertIsNotNone(message_id)

    def test_send_password_reset_sms(self):
        """
        Test Case: Password reset SMS with token sent successfully.
        Expected: SMS sent with reset token code.
        """
        success, message_id = sms_service.send_password_reset_sms(
            "+989101234567", "ABC123DEF456"
        )

        # Assert sending was successful
        self.assertTrue(success)

        # Assert message ID is returned
        self.assertIsNotNone(message_id)

    def test_send_login_otp_sms(self):
        """
        Test Case: Login OTP SMS sent successfully.
        Expected: SMS sent with OTP code.
        """
        success, message_id = sms_service.send_login_otp(
            "+989101234567", "123456"
        )

        # Assert sending was successful
        self.assertTrue(success)

        # Assert message ID is returned
        self.assertIsNotNone(message_id)
