import uuid
import random
from datetime import datetime
from flask import current_app
from app.extensions import db
from app.models.payment import Payment
from app.services.order_service import transition_order


def process_payment(order, method='balance'):
    """Simulate payment processing. Returns (payment, error_message)."""
    # Check if already paid
    existing = Payment.query.filter_by(order_id=order.id).first()
    if existing and existing.status == 'success':
        return existing, '该订单已支付。'

    if order.status != 'PENDING_PAYMENT':
        return None, f'订单状态为 "{order.status_label}"，无法支付。'

    # Determine success rate from config
    success_rate = current_app.config.get('PAYMENT_SUCCESS_RATE', 0.95)
    is_success = random.random() < success_rate

    if is_success:
        payment = Payment(
            order_id=order.id,
            method=method,
            amount=order.total_amount,
            status='success',
            transaction_id=f'TXN{uuid.uuid4().hex[:16].upper()}',
            paid_at=datetime.utcnow(),
        )
        db.session.add(payment)
        transition_order(order, 'PAID')
        db.session.commit()
        return payment, None
    else:
        payment = Payment(
            order_id=order.id,
            method=method,
            amount=order.total_amount,
            status='failed',
            transaction_id=f'TXN{uuid.uuid4().hex[:16].upper()}',
        )
        db.session.add(payment)
        db.session.commit()
        return payment, '支付失败，请重试。'


def refund_payment(order):
    """Process a refund for an order. Returns (success, error_message)."""
    payment = Payment.query.filter_by(order_id=order.id).first()
    if not payment:
        return False, '未找到支付记录。'
    if payment.status == 'refunded':
        return False, '该订单已退款。'
    if payment.status != 'success':
        return False, '只有支付成功的订单才能退款。'

    payment.status = 'refunded'
    db.session.commit()
    return True, None
