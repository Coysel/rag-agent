"""Test refund system."""
from app.extensions import db
from app.models.order import Order
from app.models.payment import Payment
from app.models.refund import Refund


def login(client, username, password):
    """Helper to log in a user."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def logout(client):
    """Helper to log out."""
    return client.get('/auth/logout', follow_redirects=True)


class TestRefund:
    """Tests for the refund system."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_paid_order(self, db, sample_users, sample_shop,
                           sample_address, suffix):
        """Create a PAID order with a successful payment record."""
        order = Order(
            order_number=f'DDTESTREF{suffix}',
            user_id=sample_users['user'].id,
            shop_id=sample_shop.id,
            address_id=sample_address.id,
            total_amount=50.0,
            status='PENDING_PAYMENT',
        )
        db.add(order)
        db.commit()

        payment = Payment(
            order_id=order.id,
            method='balance',
            amount=order.total_amount,
            status='success',
            transaction_id=f'TXNREFUND{suffix}',
        )
        db.add(payment)
        order.status = 'PAID'
        db.commit()
        return order

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_request_refund(self, client, db, sample_users, sample_shop,
                            sample_address):
        """
        POST /user/refunds/request on a PAID order.
        Verifies order becomes REFUND_REQUESTED and a refund record exists.
        """
        login(client, 'user1', '123456')
        order = self._create_paid_order(
            db, sample_users, sample_shop, sample_address, '001')

        resp = client.post('/user/refunds/request', data={
            'order_id': order.id,
            'reason': 'Not satisfied with the food',
        }, follow_redirects=True)
        assert resp.status_code == 200

        db.refresh(order)
        assert order.status == 'REFUND_REQUESTED', \
            f'Expected REFUND_REQUESTED, got {order.status}'

        refund = Refund.query.filter_by(order_id=order.id).first()
        assert refund is not None, 'Refund record not created'
        assert refund.reason == 'Not satisfied with the food'
        assert refund.amount == 50.0

    def test_duplicate_refund(self, client, db, sample_users, sample_shop,
                              sample_address):
        """
        Requesting a refund twice on the same order should fail.
        """
        login(client, 'user1', '123456')
        order = self._create_paid_order(
            db, sample_users, sample_shop, sample_address, '002')

        # First refund request
        resp1 = client.post('/user/refunds/request', data={
            'order_id': order.id,
            'reason': 'First request',
        }, follow_redirects=True)
        assert resp1.status_code == 200

        refunds = Refund.query.filter_by(order_id=order.id).all()
        assert len(refunds) == 1

        # Second refund request should fail
        resp2 = client.post('/user/refunds/request', data={
            'order_id': order.id,
            'reason': 'Second request',
        }, follow_redirects=True)
        assert resp2.status_code == 200

        db.refresh(order)
        assert order.status == 'REFUND_REQUESTED', \
            'Order status should remain REFUND_REQUESTED'

        refunds = Refund.query.filter_by(order_id=order.id).all()
        assert len(refunds) == 1, \
            'Duplicate refund request should not create another record'

    def test_merchant_approve_refund(self, client, db, sample_users,
                                    sample_shop, sample_address):
        """
        POST /merchant/refunds/<id>/approve approves refund.
        Verifies order becomes REFUNDED, payment refunded.
        """
        login(client, 'user1', '123456')
        order = self._create_paid_order(
            db, sample_users, sample_shop, sample_address, '003')

        # Request refund
        client.post('/user/refunds/request', data={
            'order_id': order.id,
            'reason': 'Please refund',
        }, follow_redirects=True)

        refund = Refund.query.filter_by(order_id=order.id).first()
        assert refund is not None

        # Login as merchant and approve
        logout(client)
        login(client, 'merchant1', '123456')

        resp = client.post(f'/merchant/refunds/{refund.id}/approve',
                           follow_redirects=True)
        assert resp.status_code == 200

        # Verify order is REFUNDED
        db.refresh(order)
        assert order.status == 'REFUNDED', \
            f'Expected REFUNDED, got {order.status}'

        # Verify refund status
        db.refresh(refund)
        assert refund.status == 'completed', \
            f'Expected completed, got {refund.status}'

        # Verify payment refunded
        db.refresh(order.payment)
        assert order.payment.status == 'refunded', \
            f'Expected refunded payment, got {order.payment.status}'

    def test_merchant_reject_refund(self, client, db, sample_users,
                                    sample_shop, sample_address):
        """
        POST /merchant/refunds/<id>/reject rejects refund.
        Verifies order becomes CANCELLED.
        """
        login(client, 'user1', '123456')
        order = self._create_paid_order(
            db, sample_users, sample_shop, sample_address, '004')

        # Request refund
        client.post('/user/refunds/request', data={
            'order_id': order.id,
            'reason': 'Change of mind',
        }, follow_redirects=True)

        refund = Refund.query.filter_by(order_id=order.id).first()
        assert refund is not None

        # Login as merchant and reject
        logout(client)
        login(client, 'merchant1', '123456')

        resp = client.post(f'/merchant/refunds/{refund.id}/reject',
                           follow_redirects=True)
        assert resp.status_code == 200

        # Verify order is CANCELLED
        db.refresh(order)
        assert order.status == 'CANCELLED', \
            f'Expected CANCELLED, got {order.status}'

        # Verify refund status
        db.refresh(refund)
        assert refund.status == 'rejected', \
            f'Expected rejected, got {refund.status}'

    def test_cannot_refund_pending_payment(self, client, db, sample_users,
                                           sample_shop, sample_address):
        """
        Trying to request a refund on a PENDING_PAYMENT order fails
        because the status transition is invalid.
        """
        login(client, 'user1', '123456')

        # Create a PENDING_PAYMENT order (not paid)
        order = Order(
            order_number='DDTESTREF005',
            user_id=sample_users['user'].id,
            shop_id=sample_shop.id,
            address_id=sample_address.id,
            total_amount=50.0,
            status='PENDING_PAYMENT',
        )
        db.add(order)
        db.commit()

        # Try to request a refund
        resp = client.post('/user/refunds/request', data={
            'order_id': order.id,
            'reason': 'Should not be possible',
        }, follow_redirects=True)
        assert resp.status_code == 200

        # Order status should remain PENDING_PAYMENT
        db.refresh(order)
        assert order.status == 'PENDING_PAYMENT', \
            f'Expected PENDING_PAYMENT, got {order.status}'

        # No refund record should exist
        refund = Refund.query.filter_by(order_id=order.id).first()
        assert refund is None, \
            'Refund record should not be created for PENDING_PAYMENT order'
