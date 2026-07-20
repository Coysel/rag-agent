"""Test authentication blueprint."""
from app.models.user import User
from tests.conftest import login


class TestAuthPages:
    """Tests for auth page rendering."""

    def test_login_page(self, client):
        """GET /auth/login returns 200 OK."""
        response = client.get('/auth/login')
        assert response.status_code == 200

    def test_register_page(self, client):
        """GET /auth/register returns 200 OK."""
        response = client.get('/auth/register')
        assert response.status_code == 200


class TestRegistration:
    """Tests for user registration."""

    def test_register_user_success(self, client, app, db):
        """POST valid registration data creates a user and redirects."""
        with app.app_context():
            response = client.post('/auth/register', data={
                'username': 'newuser',
                'email': 'newuser@test.com',
                'name': 'New User',
                'phone': '13900000001',
                'password': 'newpass123',
                'confirm_password': 'newpass123',
                'role': 'user',
            })
            # Non-merchant registration auto-logs in and redirects to main.index
            assert response.status_code == 302

            # Verify user was persisted to the database
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'newuser@test.com'
            assert user.name == 'New User'
            assert user.role == 'user'
            assert user.is_approved is True

    def test_register_duplicate_username(self, client, app, db, sample_users):
        """Registering with an existing username shows an error."""
        with app.app_context():
            response = client.post('/auth/register', data={
                'username': 'user1',  # Already exists from sample_users fixture
                'email': 'unique@test.com',
                'name': 'Duplicate',
                'phone': '13900000002',
                'password': 'pass123456',
                'confirm_password': 'pass123456',
                'role': 'user',
            })
            # Form validates but service returns error -> re-renders register page
            assert response.status_code == 200
            assert '用户名已存在'.encode('utf-8') in response.data

    def test_register_weak_password(self, client, app, db):
        """Registering with a password shorter than 6 characters shows an error."""
        with app.app_context():
            response = client.post('/auth/register', data={
                'username': 'weakpwuser',
                'email': 'weak@test.com',
                'name': 'Weak PW',
                'phone': '13900000003',
                'password': 'abc',  # Too short — fails WTForms Length(min=6)
                'confirm_password': 'abc',
                'role': 'user',
            })
            assert response.status_code == 200
            assert '密码长度不能少于6位'.encode('utf-8') in response.data

    def test_merchant_registration(self, client, app, db):
        """Registering as a merchant sets is_approved=False and redirects to login."""
        with app.app_context():
            response = client.post('/auth/register', data={
                'username': 'newmerchant',
                'email': 'newmerchant@test.com',
                'name': 'New Merchant',
                'phone': '13900000004',
                'password': 'merchant123',
                'confirm_password': 'merchant123',
                'role': 'merchant',
            })
            # Merchant registration redirects to login page (not auto-logged in)
            assert response.status_code == 302
            assert '/auth/login' in response.location

            # Verify user in database with is_approved=False
            user = User.query.filter_by(username='newmerchant').first()
            assert user is not None
            assert user.role == 'merchant'
            assert user.is_approved is False

            # Merchant should not be auto-authenticated
            profile_resp = client.get('/auth/profile', follow_redirects=False)
            assert profile_resp.status_code == 302
            assert '/auth/login' in profile_resp.location


class TestLogin:
    """Tests for user login."""

    def test_login_success(self, client, app, db, sample_users):
        """POST with valid credentials redirects and authenticates the user."""
        with app.app_context():
            response = client.post('/auth/login', data={
                'username': 'user1',
                'password': '123456',
            })
            assert response.status_code == 302

            # Verify the user is now authenticated by accessing a protected page
            profile_resp = client.get('/auth/profile')
            assert profile_resp.status_code == 200

    def test_login_wrong_password(self, client, app, db, sample_users):
        """POST with a wrong password shows an error message."""
        with app.app_context():
            response = client.post('/auth/login', data={
                'username': 'user1',
                'password': 'wrongpassword',
            }, follow_redirects=True)
            assert response.status_code == 200
            assert '密码错误'.encode('utf-8') in response.data

    def test_login_nonexistent_user(self, client, app, db):
        """POST with a non-existent username shows an error message."""
        with app.app_context():
            response = client.post('/auth/login', data={
                'username': 'nonexistent_user_xyz',
                'password': 'pass123',
            }, follow_redirects=True)
            assert response.status_code == 200
            assert '用户名或邮箱不存在'.encode('utf-8') in response.data


class TestLogout:
    """Tests for logout functionality."""

    def test_logout(self, client, app, db, sample_users):
        """After login, logging out clears the session and redirects."""
        with app.app_context():
            # Login first using the helper from conftest
            login(client, 'user1', '123456')

            # Logout
            response = client.get('/auth/logout')
            assert response.status_code == 302

            # Verify the user is no longer authenticated
            profile_resp = client.get('/auth/profile', follow_redirects=False)
            assert profile_resp.status_code == 302
            assert '/auth/login' in profile_resp.location


class TestProtectedPage:
    """Tests for unauthenticated access protection."""

    def test_protected_page_redirect(self, client, app, db):
        """Accessing /user/cart without login redirects to /auth/login."""
        with app.app_context():
            response = client.get('/user/cart', follow_redirects=False)
            assert response.status_code == 302
            assert '/auth/login' in response.location


class TestProfile:
    """Tests for the profile page and profile updates."""

    def test_profile_page(self, client, app, db, sample_users):
        """After login, GET /auth/profile returns 200 with user data."""
        with app.app_context():
            login(client, 'user1', '123456')

            response = client.get('/auth/profile')
            assert response.status_code == 200
            # The template shows the username in a disabled input field
            assert b'user1' in response.data

    def test_profile_update(self, client, app, db, sample_users):
        """POST updated profile fields persist to the database."""
        with app.app_context():
            login(client, 'user1', '123456')

            response = client.post('/auth/profile', data={
                'name': 'Updated Name',
                'phone': '13999999999',
                'email': 'updated@test.com',
            })
            assert response.status_code == 302

            # Verify changes persisted in the database
            user = User.query.filter_by(username='user1').first()
            assert user.name == 'Updated Name'
            assert user.phone == '13999999999'
            assert user.email == 'updated@test.com'

    def test_profile_change_password(self, client, app, db, sample_users):
        """Changing password invalidates the old password and the new one works."""
        with app.app_context():
            # Login with original password
            login(client, 'user1', '123456')

            # Submit profile form with new password
            response = client.post('/auth/profile', data={
                'name': 'User',
                'phone': '13800000004',
                'email': 'user1@test.com',
                'old_password': '123456',
                'new_password': 'newsecret456',
                'confirm_password': 'newsecret456',
            })
            assert response.status_code == 302

            # Logout
            client.get('/auth/logout', follow_redirects=True)

            # Old password should no longer work
            fail_resp = login(client, 'user1', '123456')
            assert '密码错误'.encode('utf-8') in fail_resp.data

            # Logout again before trying the new password
            client.get('/auth/logout', follow_redirects=True)

            # New password should work
            success_resp = client.post('/auth/login', data={
                'username': 'user1',
                'password': 'newsecret456',
            })
            assert success_resp.status_code == 302
