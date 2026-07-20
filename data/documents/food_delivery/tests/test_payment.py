"""Test payment service."""
from app.extensions import db
from app.models.order import Order
from app.models.payment import Payment


def login(client, username, password):
    """Helper to log in a user."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


class TestPayment:
    """Tests for the payment system."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_pending_order(self, db, sample_users, sample_shop,
                               sample_address, suffix):
        """Create a fresh PENDING_PAYMENT order in the database."""
        order = Order(
            order_number=f'DDTESTPAY{suffix}',
            user_id=sample_users['user'].id,
            shop_id=sample_shop.id,
            address_id=sample_address.id,
            total_amount=50.0,
            status='PENDING_PAYMENT',
        )
        db.add(order)
        db.commit()
        return order

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_pay_order(self, client, db, sample_users, sample_shop,
                       sample_address):
        """
        Pay a PENDING_PAYMENT order.
        Verifies order becomes PAID and a payment record is created.
        """
        login(client, 'user1', '123456')
        order = self._create_pending_order(
            db, sample_users, sample_shop, sample_address, '001')

        resp = client.post(f'/user/orders/{order.id}/pay',
                           follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(order)
        assert order.status == 'PAID', \
            f'Expected PAID, got {order.status}'
        assert order.payment is not None, 'Payment record missing'
        assert order.payment.status == 'success', \
            f'Expected success, got {order.payment.status}'

    def test_cannot_double_pay(self, client, db, sample_users, sample_shop,
                               sample_address):
        """
        Pay the same order twice.
        Second attempt should be blocked; only one payment record exists.
        """
        login(client, 'user1', '123456')
        order = self._create_pending_order(
            db, sample_users, sample_shop, sample_address, '002')

        # First payment
        resp1 = client.post(f'/user/orders/{order.id}/pay',
                            follow_redirects=True)
        assert resp1.status_code == 200

        db.refresh(order)
        assert order.status == 'PAID'

        # Second payment attempt
        resp2 = client.post(f'/user/orders/{order.id}/pay',
                            follow_redirects=True)
        assert resp2.status_code == 200

        db.refresh(order)
        assert order.status == 'PAID', 'Status changed after double pay'

        payments = Payment.query.filter_by(order_id=order.id).all()
        assert len(payments) == 1, \
            f'Expected 1 payment record, found {len(payments)}'

    def test_pay_wrong_status(self, client, db, sample_users, sample_shop,
                              sample_address):
        """
        Try to pay an already CANCELLED order.
        Payment should be rejected and order status unchanged.
        """
        login(client, 'user1', '123456')

        order = Order(
            order_number='DDTESTPAY003',
            user_id=sample_users['user'].id,
            shop_id=sample_shop.id,
            address_id=sample_address.id,
            total_amount=50.0,
            status='CANCELLED',
        )
        db.add(order)
        db.commit()

        resp = client.post(f'/user/orders/{order.id}/pay',
                           follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(order)
        assert order.status == 'CANCELLED', \
            f'Expected CANCELLED, got {order.status}'

    def test_refund_payment(self, client, db, sample_users, sample_shop,
                            sample_address):
        """
        Refund a paid order.
        Verifies payment status becomes 'refunded'.
        """
        login(client, 'user1', '123456')
        order = self._create_pending_order(
            db, sample_users, sample_shop, sample_address, '004')

        # Pay the order first
        client.post(f'/user/orders/{order.id}/pay', follow_redirects=True)
        db.refresh(order)
        assert order.payment is not None

        # Refund via the payment service directly
        from app.services.payment_service import refund_payment
        success, error = refund_payment(order)
        assert success is True, f'Refund failed: {error}'
        assert error is None

        db.refresh(order.payment)
        assert order.payment.status == 'refunded', \
            f'Expected refunded, got {order.payment.status}'

    def test_payment_record_has_transaction_id(self, client, db,
                                               sample_users, sample_shop,
                                               sample_address):
        """
        After successful payment, the payment record has a transaction_id.
        """
        login(client, 'user1', '123456')
        order = self._create_pending_order(
            db, sample_users, sample_shop, sample_address, '005')

        client.post(f'/user/orders/{order.id}/pay', follow_redirects=True)

        db.refresh(order)
        assert order.payment is not None
        assert order.payment.transaction_id is not None, \
            'transaction_id is None'
        assert order.payment.transaction_id.startswith('TXN'), \
            f'Unexpected transaction_id: {order.payment.transaction_id}'
