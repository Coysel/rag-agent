from datetime import datetime
from app.extensions import db
from app.models.refund import Refund
from app.services.order_service import transition_order
from app.services.payment_service import refund_payment


def request_refund(user_id, order_id, reason):
    """Submit a refund request. Returns (refund, error_message)."""
    existing = Refund.query.filter_by(order_id=order_id).first()
    if existing:
        return None, '该订单已有退款申请。'

    refund = Refund(
        order_id=order_id,
        user_id=user_id,
        reason=reason,
        amount=None,  # Will be set on approval
    )
    db.session.add(refund)

    from app.models.order import Order
    order = Order.query.get(order_id)
    if order:
        refund.amount = order.total_amount

    db.session.commit()
    return refund, None


def process_refund_approval(refund_id, processor_id):
    """Approve a refund. Returns (success, error_message)."""
    refund = Refund.query.get(refund_id)
    if not refund:
        return False, '退款申请不存在。'
    if refund.status != 'pending':
        return False, f'退款申请状态为 {refund.status}，无法处理。'

    order = refund.order
    transition_order(order, 'REFUNDED')
    refund_payment(order)
    refund.status = 'completed'
    refund.processed_by = processor_id
    refund.processed_at = datetime.utcnow()
    db.session.commit()
    return True, None


def process_refund_rejection(refund_id, processor_id):
    """Reject a refund. Returns (success, error_message)."""
    refund = Refund.query.get(refund_id)
    if not refund:
        return False, '退款申请不存在。'
    if refund.status != 'pending':
        return False, f'退款申请状态为 {refund.status}，无法处理。'

    order = refund.order
    transition_order(order, 'CANCELLED')
    refund.status = 'rejected'
    refund.processed_by = processor_id
    refund.processed_at = datetime.utcnow()
    db.session.commit()
    return True, None
