"""
Comprehensive test suite for User Management System.
Tests cover all major features and edge cases.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache

from accounts.models import Profile, PasswordResetToken
from accounts.sms_service import sms_service

User = get_user_model()


class UserRegistrationTestCase(TestCase):
    """Test suite for user registration."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/register/"

    def test_successful_registration(self):
        """User can register with valid phone and password."""
        data = {
            "phone_number": "09101234567",
            "username": "testuser",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        }
        response = self.client.post(self.url, data, format="json")
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Registration failed with status {response.status_code}")
            print(f"Response data: {response.json()}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(phone_number=data["phone_number"]).exists())
        user = User.objects.get(phone_number=data["phone_number"])
        self.assertTrue(hasattr(user, "profile"))

    def test_registration_password_mismatch(self):
        """Registration fails when passwords don't match."""
        data = {
            "phone_number": "09101111111",
            "username": "testuser",
            "password": "SecurePass123!",
            "password_confirm": "DifferentPass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_duplicate_phone(self):
        """Registration fails when phone number already exists."""
        User.objects.create_user(phone_number="09101234567", password="Pass123!")
        
        data = {
            "phone_number": "09101234567",
            "username": "newuser",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_short_password(self):
        """Registration fails for passwords shorter than 8 chars."""
        data = {
            "phone_number": "09101234567",
            "username": "testuser",
            "password": "Short",
            "password_confirm": "Short",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTestCase(TestCase):
    """Test suite for user login."""

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/login/"
        self.user = User.objects.create_user(
            phone_number="09101234567",
            password="TestPass123!",
            username="testuser",
        )
        # Profile is auto-created by signal

    def test_successful_login(self):
        """User can login with correct credentials."""
        data = {
            "phone_number": "09101234567",
            "password": "TestPass123!",
        }
        response = self.client.post(self.url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_invalid_password(self):
        """Login fails with wrong password."""
        data = {
            "phone_number": "09101234567",
            "password": "WrongPass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user(self):
        """Login fails for non-existent phone."""
        data = {
            "phone_number": "09199999999",
            "password": "TestPass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user(self):
        """Login fails for inactive users."""
        self.user.is_active = False
        self.user.save()
        
        data = {
            "phone_number": "09101234567",
            "password": "TestPass123!",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetTestCase(TestCase):
    """Test suite for password reset."""

    def setUp(self):
        self.client = APIClient()
        self.forgot_url = "/api/auth/forgot-password/"
        self.reset_url = "/api/auth/reset-password/"
        
        self.user = User.objects.create_user(
            phone_number="09101234567",
            password="TestPass123!",
        )
        # Profile is auto-created by signal

    def test_forgot_password(self):
        """Forgot password creates reset token."""
        data = {"phone_number": "09101234567"}
        response = self.client.post(self.forgot_url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(user=self.user).exists())

    def test_reset_password_valid_token(self):
        """Password reset with valid token succeeds."""
        token = PasswordResetToken.generate_token()
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token=token,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        
        data = {
            "phone_number": "09101234567",
            "token": token,
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        }
        response = self.client.post(self.reset_url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass123!"))

    def test_reset_password_expired_token(self):
        """Password reset fails with expired token."""
        token = PasswordResetToken.generate_token()
        PasswordResetToken.objects.create(
            user=self.user,
            token=token,
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        
        data = {
            "phone_number": "09101234567",
            "token": token,
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        }
        response = self.client.post(self.reset_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileManagementTestCase(TestCase):
    """Test suite for profile management."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone_number="09101234567",
            password="TestPass123!",
        )
        # Profile is auto-created by signal
        
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_get_profile(self):
        """User can retrieve their profile."""
        response = self.client.get("/api/profiles/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_profile(self):
        """User can update their profile."""
        data = {"full_name": "John Doe"}
        response = self.client.patch("/api/profiles/me/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PasswordResetTokenModelTestCase(TestCase):
    """Test suite for PasswordResetToken model."""

    def setUp(self):
        self.user = User.objects.create_user(phone_number="09101234567")

    def test_generate_token(self):
        """Token generation creates valid 32-char hex."""
        token = PasswordResetToken.generate_token()
        self.assertEqual(len(token), 32)
        int(token, 16)  # Should not raise

    def test_token_validity(self):
        """Valid token passes validation."""
        token = PasswordResetToken.generate_token()
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token=token,
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        self.assertTrue(reset_token.is_valid())

    def test_token_invalid_when_expired(self):
        """Expired token fails validation."""
        token = PasswordResetToken.generate_token()
        reset_token = PasswordResetToken.objects.create(
            user=self.user,
            token=token,
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        self.assertFalse(reset_token.is_valid())
