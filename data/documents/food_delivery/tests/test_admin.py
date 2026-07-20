"""Test admin blueprint."""
from app.extensions import db
from app.models.user import User


def login(client, username, password):
    """Helper to log in a user."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def logout(client):
    """Helper to log out."""
    return client.get('/auth/logout', follow_redirects=True)


class TestAdmin:
    """Tests for the admin blueprint."""

    def test_dashboard(self, client, sample_users):
        """GET /admin/dashboard returns 200 with stats."""
        login(client, 'admin', 'admin123')
        resp = client.get('/admin/dashboard')
        assert resp.status_code == 200

    def test_users_page(self, client, sample_users):
        """GET /admin/users returns 200."""
        login(client, 'admin', 'admin123')
        resp = client.get('/admin/users')
        assert resp.status_code == 200

    def test_users_filter(self, client, sample_users):
        """GET /admin/users?role=merchant returns 200."""
        login(client, 'admin', 'admin123')
        resp = client.get('/admin/users?role=merchant')
        assert resp.status_code == 200

    def test_toggle_user_active(self, client, db, sample_users):
        """POST /admin/users/<id>/toggle-active toggles is_active."""
        login(client, 'admin', 'admin123')
        target = sample_users['user']
        resp = client.post(f'/admin/users/{target.id}/toggle-active',
                           follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(target)
        assert target.is_active is False

    def test_change_user_role(self, client, db, sample_users):
        """POST /admin/users/<id>/change-role updates user role."""
        login(client, 'admin', 'admin123')
        target = sample_users['user']
        resp = client.post(f'/admin/users/{target.id}/change-role', data={
            'role': 'admin',
        }, follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(target)
        assert target.role == 'admin'

    def test_cannot_toggle_self(self, client, db, sample_users):
        """Admin toggling own account returns error and does not change."""
        login(client, 'admin', 'admin123')
        admin_user = sample_users['admin']
        resp = client.post(f'/admin/users/{admin_user.id}/toggle-active',
                           follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(admin_user)
        assert admin_user.is_active is True  # admin's own status unchanged

    def test_merchants_pending(self, client, sample_users):
        """GET /admin/merchants/pending returns 200."""
        login(client, 'admin', 'admin123')
        resp = client.get('/admin/merchants/pending')
        assert resp.status_code == 200

    def test_approve_merchant(self, client, db, sample_users):
        """POST /admin/merchants/<id>/approve sets is_approved=True."""
        # Create a merchant who is not yet approved
        new_merchant = User(
            username='pending_merchant',
            email='pending@test.com',
            name='Pending Merchant',
            phone='13800000999',
            role='merchant',
            is_approved=False,
        )
        new_merchant.set_password('123456')
        db.add(new_merchant)
        db.commit()

        login(client, 'admin', 'admin123')
        resp = client.post(f'/admin/merchants/{new_merchant.id}/approve',
                           follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(new_merchant)
        assert new_merchant.is_approved is True

    def test_shops_page(self, client, sample_users, sample_shop):
        """GET /admin/shops returns 200."""
        login(client, 'admin', 'admin123')
        resp = client.get('/admin/shops')
        assert resp.status_code == 200

    def test_change_shop_status(self, client, db, sample_users, sample_shop):
        """POST /admin/shops/<id>/status updates shop status."""
        login(client, 'admin', 'admin123')
        resp = client.post(f'/admin/shops/{sample_shop.id}/status', data={
            'status': 'closed',
        }, follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(sample_shop)
        assert sample_shop.status == 'closed'

    def test_orders_page(self, client, sample_users, sample_order):
        """GET /admin/orders returns 200."""
        login(client, 'admin', 'admin123')
        resp = client.get('/admin/orders')
        assert resp.status_code == 200

    def test_complaints_page(self, client, sample_users):
        """GET /admin/complaints returns 200."""
        login(client, 'admin', 'admin123')
        resp = client.get('/admin/complaints')
        assert resp.status_code == 200

    def test_statistics_page(self, client, sample_users):
        """GET /admin/statistics returns 200."""
        login(client, 'admin', 'admin123')
        resp = client.get('/admin/statistics')
        assert resp.status_code == 200

    def test_admin_access_denied_for_user(self, client, sample_users):
        """Regular user accessing /admin/dashboard returns 403."""
        login(client, 'user1', '123456')
        resp = client.get('/admin/dashboard')
        assert resp.status_code == 403
