"""Test the complete order lifecycle - integration test."""
from app.extensions import db
from app.models.order import Order
from app.models.user import User
from app.models.address import Address
from app.models.menu_item import MenuItem


def login(client, username, password):
    """Helper to log in a user."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def logout(client):
    """Helper to log out."""
    return client.get('/auth/logout', follow_redirects=True)


class TestOrderWorkflow:
    """Single integration test covering the full order lifecycle."""

    def test_full_order_lifecycle(self, client, db, sample_users, sample_shop):
        """
        Complete order lifecycle:
        register -> add to cart -> checkout -> pay ->
        merchant accept/prepare/ready -> rider accept/deliver ->
        user confirm -> verify invalid transitions.
        """

        # ---------------------------------------------------------------
        # Step 1: Register a new user
        # ---------------------------------------------------------------
        resp = client.post('/auth/register', data={
            'username': 'workflow_user',
            'email': 'workflow@test.com',
            'password': '123456',
            'confirm_password': '123456',
            'name': 'Workflow User',
            'phone': '13800000100',
            'role': 'user',
        }, follow_redirects=True)
        assert resp.status_code == 200, 'User registration failed'

        user = User.query.filter_by(username='workflow_user').first()
        assert user is not None, 'Registered user not found in database'

        # ---------------------------------------------------------------
        # Step 2: Add items to cart (2 items from sample_shop)
        # ---------------------------------------------------------------
        items = MenuItem.query.filter_by(shop_id=sample_shop.id).all()
        item_a = items[0]  # Item A, stock=50, price=10.0
        item_b = items[1]  # Item B, stock=30, price=20.0

        resp = client.post('/user/cart/add', data={
            'menu_item_id': item_a.id,
            'quantity': 2,
        }, follow_redirects=True)
        assert resp.status_code == 200, 'Failed to add item A to cart'

        resp = client.post('/user/cart/add', data={
            'menu_item_id': item_b.id,
            'quantity': 1,
        }, follow_redirects=True)
        assert resp.status_code == 200, 'Failed to add item B to cart'

        # ---------------------------------------------------------------
        # Step 3: Create an address then checkout
        # ---------------------------------------------------------------
        resp = client.post('/user/addresses/add', data={
            'label': 'Home',
            'address_detail': 'Workflow Test Address 789',
        }, follow_redirects=True)
        assert resp.status_code == 200, 'Failed to add address'

        addr = Address.query.filter_by(user_id=user.id).first()
        assert addr is not None, 'Address not found'

        resp = client.post('/user/checkout', data={
            'address_id': addr.id,
            'note': 'Integration test order',
        }, follow_redirects=True)
        assert resp.status_code == 200, 'Checkout failed'

        order = Order.query.filter_by(user_id=user.id).first()
        assert order is not None, 'Order not created after checkout'
        assert order.status == 'PENDING_PAYMENT', \
            f'Expected PENDING_PAYMENT, got {order.status}'

        # ---------------------------------------------------------------
        # Step 4: Pay the order -> should become PAID
        # ---------------------------------------------------------------
        resp = client.post(f'/user/orders/{order.id}/pay',
                           follow_redirects=True)
        assert resp.status_code == 200, 'Payment request failed'

        db.refresh(order)
        assert order.status == 'PAID', \
            f'Expected PAID after payment, got {order.status}'
        assert order.payment is not None, 'Payment record not created'
        assert order.payment.status == 'success', \
            f'Expected success payment, got {order.payment.status}'

        # ---------------------------------------------------------------
        # Step 5: Login as merchant, accept the order -> ACCEPTED
        # ---------------------------------------------------------------
        logout(client)
        login(client, 'merchant1', '123456')

        resp = client.post(f'/merchant/orders/{order.id}/accept',
                           follow_redirects=True)
        assert resp.status_code == 200, 'Merchant accept failed'

        db.refresh(order)
        assert order.status == 'ACCEPTED', \
            f'Expected ACCEPTED, got {order.status}'

        # ---------------------------------------------------------------
        # Step 6: Start preparing -> PREPARING
        # ---------------------------------------------------------------
        resp = client.post(f'/merchant/orders/{order.id}/preparing',
                           follow_redirects=True)
        assert resp.status_code == 200, 'Merchant preparing failed'

        db.refresh(order)
        assert order.status == 'PREPARING', \
            f'Expected PREPARING, got {order.status}'

        # ---------------------------------------------------------------
        # Step 7: Mark ready -> READY_FOR_PICKUP
        # ---------------------------------------------------------------
        resp = client.post(f'/merchant/orders/{order.id}/ready',
                           follow_redirects=True)
        assert resp.status_code == 200, 'Merchant ready failed'

        db.refresh(order)
        assert order.status == 'READY_FOR_PICKUP', \
            f'Expected READY_FOR_PICKUP, got {order.status}'

        # ---------------------------------------------------------------
        # Step 8: Login as rider, accept -> DELIVERING
        # ---------------------------------------------------------------
        logout(client)
        login(client, 'rider1', '123456')

        resp = client.post(f'/rider/orders/{order.id}/accept',
                           follow_redirects=True)
        assert resp.status_code == 200, 'Rider accept failed'

        db.refresh(order)
        assert order.status == 'DELIVERING', \
            f'Expected DELIVERING, got {order.status}'

        # ---------------------------------------------------------------
        # Step 9: Deliver -> DELIVERED
        # ---------------------------------------------------------------
        resp = client.post(f'/rider/orders/{order.id}/deliver',
                           follow_redirects=True)
        assert resp.status_code == 200, 'Rider deliver failed'

        db.refresh(order)
        assert order.status == 'DELIVERED', \
            f'Expected DELIVERED, got {order.status}'

        # ---------------------------------------------------------------
        # Step 10: Login as user, confirm receipt -> COMPLETED
        # ---------------------------------------------------------------
        logout(client)
        login(client, 'workflow_user', '123456')

        resp = client.post(f'/user/orders/{order.id}/confirm',
                           follow_redirects=True)
        assert resp.status_code == 200, 'User confirm failed'

        db.refresh(order)
        assert order.status == 'COMPLETED', \
            f'Expected COMPLETED, got {order.status}'

        # ---------------------------------------------------------------
        # Step 11: Verify invalid transitions
        # ---------------------------------------------------------------

        # 11a: Try to cancel a COMPLETED order -> should fail
        resp = client.post(f'/user/orders/{order.id}/cancel',
                           follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(order)
        assert order.status == 'COMPLETED', \
            'Cancelling a COMPLETED order should not change status'

        # 11b: Try to accept a non-PAID (COMPLETED) order -> should fail
        logout(client)
        login(client, 'merchant1', '123456')

        resp = client.post(f'/merchant/orders/{order.id}/accept',
                           follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(order)
        assert order.status == 'COMPLETED', \
            'Accepting a COMPLETED order should not change status'
