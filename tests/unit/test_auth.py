"""
Unit tests for authentication endpoints
"""
import pytest


class TestUserRegistration:
    """Test user registration"""

    def test_user_registration_success(self, client, init_database):
        """Test successful user registration"""
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'password123',
            'full_name': 'New User'
        })

        assert response.status_code == 201
        assert 'access_token' in response.json
        assert 'user' in response.json
        assert response.json['user']['username'] == 'newuser'

    def test_user_registration_duplicate_email(self, client, init_database):
        """Test registration with duplicate email"""
        response = client.post('/api/auth/register', json={
            'username': 'newuser2',
            'email': 'admin@test.com',  # Already exists
            'password': 'password123'
        })

        assert response.status_code == 409
        assert 'error' in response.json

    def test_user_registration_duplicate_username(self, client, init_database):
        """Test registration with duplicate username"""
        response = client.post('/api/auth/register', json={
            'username': 'admin_test',  # Already exists
            'email': 'newuser@test.com',
            'password': 'password123'
        })

        assert response.status_code == 409
        assert 'error' in response.json

    def test_user_registration_missing_fields(self, client, init_database):
        """Test registration with missing required fields"""
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            # Missing email and password
        })

        assert response.status_code == 400
        assert 'error' in response.json

    def test_user_registration_invalid_email(self, client, init_database):
        """Test registration with invalid email format"""
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            'email': 'invalid-email',
            'password': 'password123'
        })

        assert response.status_code == 400
        assert 'error' in response.json


class TestUserLogin:
    """Test user login"""

    def test_user_login_success(self, client, init_database):
        """Test successful login"""
        response = client.post('/api/auth/login', json={
            'username': 'admin_test',
            'password': 'admin123'
        })

        assert response.status_code == 200
        assert 'access_token' in response.json
        assert 'user' in response.json

    def test_user_login_with_email(self, client, init_database):
        """Test login with email instead of username"""
        response = client.post('/api/auth/login', json={
            'username': 'admin@test.com',
            'password': 'admin123'
        })

        assert response.status_code == 200
        assert 'access_token' in response.json

    def test_user_login_invalid_credentials(self, client, init_database):
        """Test login with invalid credentials"""
        response = client.post('/api/auth/login', json={
            'username': 'admin_test',
            'password': 'wrongpassword'
        })

        assert response.status_code == 401
        assert 'error' in response.json

    def test_user_login_nonexistent_user(self, client, init_database):
        """Test login with non-existent user"""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'password123'
        })

        assert response.status_code == 401
        assert 'error' in response.json



class TestJWTToken:
    """Test JWT token functionality"""
    pass


class TestUserProfile:
    """Test user profile endpoints"""

    def test_update_profile_invalid_phone(self, client, admin_token, init_database):
        """Test updating profile with invalid phone"""
        headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

        response = client.put('/api/auth/profile',
            headers=headers,
            json={
                'phone': 'invalid_phone'
            }
        )

        assert response.status_code == 400
        assert 'error' in response.json


class TestAdminAuthorization:
    """Test admin authorization decorator"""
    pass
