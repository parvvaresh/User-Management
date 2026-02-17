from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class AuthFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+491601234567", password="S3cur3pass!"
        )

    def test_password_login(self):
        url = reverse("token_obtain_pair")
        res = self.client.post(
            url,
            {"phone_number": "+491601234567", "password": "S3cur3pass!"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_register_and_profile_auto_create(self):
        url = reverse("register")
        res = self.client.post(
            url, {
                "phone_number": "09121111111",
                "username": "newbie",
                "password": "S3cur3pass!",
                "password_confirm": "S3cur3pass!",
            }, format="json"
        )
        print(res.data)
        self.assertEqual(res.status_code, 201)
        u = User.objects.get(phone_number="09121111111")
        self.assertTrue(hasattr(u, "profile"))


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+491601234567", password="S3cur3pass!", username="alice"
        )
        token = self.client.post(
            reverse("token_obtain_pair"),
            {"phone_number": "+491601234567", "password": "S3cur3pass!"},
        ).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_me_get_and_patch(self):
        res = self.client.get("/api/profiles/me/")
        self.assertEqual(res.status_code, 200)
        res = self.client.patch(
            "/api/profiles/me/", {"full_name": "Alice Doe"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["full_name"], "Alice Doe")

    def test_list_and_retrieve_profiles(self):
        other = User.objects.create_user(phone_number="+491602222222")
        res = self.client.get("/api/profiles/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 2)
        res = self.client.get(f"/api/profiles/{other.profile.id}/")
        self.assertEqual(res.status_code, 200)

    def test_update_credentials(self):
        res = self.client.patch(
            "/api/me/credentials/",
            {"username": "newalice", "password": "NewStr0ngPass!"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        # can log in with new password
        res = self.client.post(
            reverse("token_obtain_pair"),
            {"phone_number": "+491601234567", "password": "NewStr0ngPass!"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
