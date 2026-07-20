import random
import string
from datetime import datetime


def generate_order_number():
    """Generate a unique order number like DD20260617XXXXX"""
    now = datetime.utcnow()
    date_part = now.strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.digits, k=5))
    return f'DD{date_part}{random_part}'


def format_currency(amount):
    """Format a float as CNY currency string."""
    return f'¥{amount:.2f}'


ORDER_STATUS_LABELS = {
    'PENDING_PAYMENT': '待支付',
    'PAID': '已支付',
    'ACCEPTED': '已接单',
    'PREPARING': '备餐中',
    'READY_FOR_PICKUP': '待取餐',
    'DELIVERING': '配送中',
    'DELIVERED': '已送达',
    'COMPLETED': '已完成',
    'CANCELLED': '已取消',
    'REFUND_REQUESTED': '退款中',
    'REFUNDED': '已退款',
}

ORDER_STATUS_COLORS = {
    'PENDING_PAYMENT': 'secondary',
    'PAID': 'info',
    'ACCEPTED': 'primary',
    'PREPARING': 'warning',
    'READY_FOR_PICKUP': 'warning',
    'DELIVERING': 'primary',
    'DELIVERED': 'success',
    'COMPLETED': 'success',
    'CANCELLED': 'dark',
    'REFUND_REQUESTED': 'danger',
    'REFUNDED': 'danger',
}


def get_status_label(status):
    return ORDER_STATUS_LABELS.get(status, status)


def get_status_color(status):
    return ORDER_STATUS_COLORS.get(status, 'secondary')
