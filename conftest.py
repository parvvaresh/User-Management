"""
Pytest configuration and fixtures.
This file provides common test fixtures for pytest-django.
Django setup is handled automatically by pytest-django via pytest.ini.
"""

import os
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User, Profile

# Ensure Django settings module is set
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """Provide an API client for tests."""
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """
    Create and return an authenticated test user.
    Usage:
        def test_example(authenticated_user):
            assert authenticated_user.phone_number == "+989101234567"
    """
    user = User.objects.create_user(
        phone_number="+989101234567",
        password="TestPass123!",
        username="testuser"
    )
    Profile.objects.create(user=user)
    return user


@pytest.fixture
def authenticated_client(db, authenticated_user):
    """
    Provide an authenticated API client.
    Usage:
        def test_example(authenticated_client):
            response = authenticated_client.get("/accounts/profiles/me/")
    """
    client = APIClient()
    refresh = RefreshToken.for_user(authenticated_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def user_data():
    """
    Provide test user data.
    Usage:
        def test_example(user_data):
            print(user_data["phone_number"])  # +989101234568
    """
    return {
        "phone_number": "+989101234568",
        "username": "newuser",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
    }


@pytest.fixture
def login_data():
    """
    Provide test login credentials.
    Usage:
        def test_example(login_data):
            print(login_data["phone_number"])
    """
    return {
        "phone_number": "+989101234567",
        "password": "TestPass123!",
    }


# ============================================================================
# SMS Service Fixtures
# ============================================================================

@pytest.fixture
def mock_sms_send(mocker):
    """
    Mock SMS sending functionality.
    Usage:
        def test_example(mock_sms_send):
            response = client.post("/accounts/auth/forgot-password/", data)
            assert mock_sms_send.called
    """
    return mocker.patch("accounts.sms_service.sms_service.send_sms")


@pytest.fixture
def mock_password_reset_sms(mocker):
    """Mock password reset SMS sending."""
    return mocker.patch("accounts.sms_service.sms_service.send_password_reset_sms")


@pytest.fixture
def mock_login_otp_sms(mocker):
    """Mock login OTP SMS sending."""
    return mocker.patch("accounts.sms_service.sms_service.send_login_otp")


# ============================================================================
# Cache Fixtures
# ============================================================================

@pytest.fixture
def clear_cache(db):
    """
    Clear cache before each test.
    Usage:
        def test_example(clear_cache):
            # Cache is cleared for this test
    """
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom markers for organizing tests."""
    config.addinivalue_line(
        "markers", "slow: mark test as slow to run"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as authentication related"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security related"
    )
    # Allow async-unsafe operations in tests
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


def pytest_collection_modifyitems(config, items):
    """
    Pytest hook: Mark tests if not already marked.
    This helps organize tests by type.
    """
    for item in items:
        if "test_" in item.nodeid:
            # Mark all tests with correct markers based on name
            if "auth" in item.nodeid.lower():
                item.add_marker(pytest.mark.auth)
            if "security" in item.nodeid.lower():
                item.add_marker(pytest.mark.security)
