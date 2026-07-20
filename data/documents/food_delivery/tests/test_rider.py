"""Test rider blueprint."""
from app.extensions import db
from app.models.order import Order
from app.models.rider_location import RiderLocation


def login(client, username, password):
    """Helper to log in a user."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def logout(client):
    """Helper to log out."""
    return client.get('/auth/logout', follow_redirects=True)


class TestRider:
    """Tests for the rider blueprint."""

    def test_dashboard(self, client, sample_users):
        """GET /rider/dashboard returns 200."""
        login(client, 'rider1', '123456')
        resp = client.get('/rider/dashboard')
        assert resp.status_code == 200

    def test_available_orders(self, client, sample_users):
        """GET /rider/orders returns 200."""
        login(client, 'rider1', '123456')
        resp = client.get('/rider/orders')
        assert resp.status_code == 200

    def test_active_orders_empty(self, client, sample_users):
        """GET /rider/orders/active returns 200 with no active orders."""
        login(client, 'rider1', '123456')
        resp = client.get('/rider/orders/active')
        assert resp.status_code == 200

    def test_accept_order(self, client, db, sample_users, sample_order):
        """
        Transition order to READY_FOR_PICKUP as merchant,
        then accept as rider. Verify status=DELIVERING and rider assigned.
        """
        # Step 1: Login as merchant and transition to READY_FOR_PICKUP
        login(client, 'merchant1', '123456')
        client.post(f'/merchant/orders/{sample_order.id}/accept',
                     follow_redirects=True)
        client.post(f'/merchant/orders/{sample_order.id}/preparing',
                     follow_redirects=True)
        client.post(f'/merchant/orders/{sample_order.id}/ready',
                     follow_redirects=True)
        logout(client)

        # Step 2: Login as rider and accept
        login(client, 'rider1', '123456')
        resp = client.post(f'/rider/orders/{sample_order.id}/accept',
                           follow_redirects=True)
        assert resp.status_code == 200

        # Verify order state
        order = db.get(Order, sample_order.id)
        assert order.status == 'DELIVERING'
        assert order.rider_id == sample_users['rider'].id

    def test_pickup_order(self, client, db, sample_users, sample_order):
        """POST /rider/orders/<id>/pickup returns redirect (200)."""
        # Setup: transition to DELIVERING
        login(client, 'merchant1', '123456')
        client.post(f'/merchant/orders/{sample_order.id}/accept',
                     follow_redirects=True)
        client.post(f'/merchant/orders/{sample_order.id}/preparing',
                     follow_redirects=True)
        client.post(f'/merchant/orders/{sample_order.id}/ready',
                     follow_redirects=True)
        logout(client)

        login(client, 'rider1', '123456')
        client.post(f'/rider/orders/{sample_order.id}/accept',
                     follow_redirects=True)

        resp = client.post(f'/rider/orders/{sample_order.id}/pickup',
                           follow_redirects=True)
        assert resp.status_code == 200

    def test_deliver_order(self, client, db, sample_users, sample_order):
        """POST /rider/orders/<id>/deliver transitions status to DELIVERED."""
        # Setup: transition to DELIVERING
        login(client, 'merchant1', '123456')
        client.post(f'/merchant/orders/{sample_order.id}/accept',
                     follow_redirects=True)
        client.post(f'/merchant/orders/{sample_order.id}/preparing',
                     follow_redirects=True)
        client.post(f'/merchant/orders/{sample_order.id}/ready',
                     follow_redirects=True)
        logout(client)

        login(client, 'rider1', '123456')
        client.post(f'/rider/orders/{sample_order.id}/accept',
                     follow_redirects=True)

        resp = client.post(f'/rider/orders/{sample_order.id}/deliver',
                           follow_redirects=True)
        assert resp.status_code == 200

        order = db.get(Order, sample_order.id)
        assert order.status == 'DELIVERED'

    def test_order_detail(self, client, sample_users, sample_order):
        """GET /rider/orders/<id> returns 200."""
        login(client, 'rider1', '123456')
        resp = client.get(f'/rider/orders/{sample_order.id}')
        assert resp.status_code == 200

    def test_history(self, client, sample_users):
        """GET /rider/history returns 200."""
        login(client, 'rider1', '123456')
        resp = client.get('/rider/history')
        assert resp.status_code == 200

    def test_earnings(self, client, sample_users):
        """GET /rider/earnings returns 200."""
        login(client, 'rider1', '123456')
        resp = client.get('/rider/earnings')
        assert resp.status_code == 200

    def test_location_update(self, client, db, sample_users):
        """POST /rider/location/update stores rider location."""
        login(client, 'rider1', '123456')
        resp = client.post('/rider/location/update', data={
            'latitude': 39.9042,
            'longitude': 116.4074,
        }, follow_redirects=True)
        assert resp.status_code == 200

        loc = RiderLocation.query.filter_by(
            rider_id=sample_users['rider'].id
        ).first()
        assert loc is not None
        assert abs(loc.latitude - 39.9042) < 0.001
        assert abs(loc.longitude - 116.4074) < 0.001

    def test_rider_cannot_access_merchant(self, client, sample_users):
        """Rider accessing /merchant/dashboard returns 403."""
        login(client, 'rider1', '123456')
        resp = client.get('/merchant/dashboard')
        assert resp.status_code == 403
