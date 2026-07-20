from datetime import datetime
from app.extensions import db
from app.models.user import User
from app.models.shop import Shop
from app.models.order import Order
from app.models.payment import Payment
from app.models.review import Review
from sqlalchemy import func


def platform_summary():
    """Get platform-wide summary statistics."""
    total_users = User.query.filter_by(role='user').count()
    total_merchants = User.query.filter_by(role='merchant', is_approved=True).count()
    total_riders = User.query.filter_by(role='rider', is_approved=True).count()
    total_shops = Shop.query.filter_by(status='approved').count()
    pending_shops = Shop.query.filter_by(status='pending').count()
    total_orders = Order.query.count()
    completed_orders = Order.query.filter_by(status='COMPLETED').count()
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success').scalar() or 0

    return {
        'total_users': total_users,
        'total_merchants': total_merchants,
        'total_riders': total_riders,
        'total_shops': total_shops,
        'pending_shops': pending_shops,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
    }


def revenue_by_period(period='month'):
    """Get revenue statistics by time period."""
    if period == 'today':
        date_filter = func.date(Payment.paid_at) == func.date(datetime.utcnow())
    elif period == 'week':
        date_filter = func.date(Payment.paid_at) >= func.date(datetime.utcnow(), '-7 days')
    elif period == 'month':
        date_filter = func.date(Payment.paid_at) >= func.date(datetime.utcnow(), '-30 days')
    else:
        date_filter = True

    revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'success', date_filter).scalar() or 0
    count = db.session.query(func.count(Payment.id)).filter(
        Payment.status == 'success', date_filter).scalar() or 0

    return {'revenue': revenue, 'count': count}


def order_stats():
    """Get order status distribution."""
    stats = {}
    statuses = ['PENDING_PAYMENT', 'PAID', 'ACCEPTED', 'PREPARING', 'READY_FOR_PICKUP',
                'DELIVERING', 'DELIVERED', 'COMPLETED', 'CANCELLED', 'REFUND_REQUESTED', 'REFUNDED']
    for status in statuses:
        stats[status] = Order.query.filter_by(status=status).count()
    return stats


def user_growth():
    """Get user registration stats (last 7 days)."""
    results = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        func.date(User.created_at) >= func.date(datetime.utcnow(), '-7 days')
    ).group_by(func.date(User.created_at)).order_by('date').all()
    return [{'date': str(r.date), 'count': r.count} for r in results]
