from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserAPITests(TestCase):
    """Test the users API (public)"""
    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_success(self):
        """Test creating user with valid payload successful"""
        payload = {
            'email': 'test@test.com',
            'password': 'testpass123',
            'name': 'Test name'
        }

        request = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(request.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(**request.data)
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', request.data)

    def test_user_exists(self):
        """Test creating user that already exists"""
        payload = {
            'email': 'test@test.com',
            'password': 'testpass123',
            'name': 'Test name'
        }
        create_user(**payload)

        request = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """Test that the password must be more than 5 characters"""
        payload = {
            'email': 'test@test.com',
            'password': 'test',
            'name': 'Test name'
        }

        request = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test that a token is created for a user"""
        payload = {
            'email': 'test@test.com',
            'password': 'testpassword'
        }
        create_user(**payload)
        request = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', request.data)
        self.assertEqual(request.status_code, status.HTTP_200_OK)

    def test_create_token_invalid_credentials(self):
        """Test that token is not created if invalid credentials are given"""
        create_user(email='test@test.com', password="testpass")
        payload = {
            'email': 'test@test.com',
            'password': 'wrongpass'
        }

        request = self.client.post(TOKEN_URL, payload)
        self.assertNotIn('token', request.data)
        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        """Test if token is no created if user doesn't exist"""
        payload = {
            'email': 'test@test.com',
            'password': 'testpassword'
        }

        request = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', request.data)
        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_missing_fields(self):
        """Test that email and password are required"""
        payload = {
            'email': 'test@test.com',
            'password': ''
        }
        request = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', request.data)
        self.assertEqual(request.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthrorized(self):
        """Test that authentication is required for user"""
        request = self.client.get(ME_URL)

        self.assertEqual(request.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserAPITests(TestCase):
    """Test API requests that require authentication"""

    def setUp(self):
        self.user = create_user(
            email='test@test.com',
            password='testpass',
            name='fname'
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieven profile for logged in used"""
        request = self.client.get(ME_URL)

        self.assertEqual(request.status_code, status.HTTP_200_OK)
        self.assertEqual(request.data, {
            'name': self.user.name,
            'email': self.user.email
        })

    def test_post_me_not_allowed(self):
        """Test that post is not allowed on the me url"""

        request = self.client.post(ME_URL, {})

        self.assertEqual(request.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_updated_user_profile(self):
        """Test updating the user profile for authenticated user"""
        payload = {'name': 'newname', 'password': 'newpassword'}

        request = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(self.user.name, payload['name'])
        self.assertEqual(request.status_code, status.HTTP_200_OK)
