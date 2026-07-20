from datetime import datetime
from app.extensions import db
from app.models.order import Order, OrderItem
from app.models.cart_item import CartItem
from app.models.menu_item import MenuItem
from app.utils.helpers import generate_order_number

# Legal state transitions
ORDER_TRANSITIONS = {
    'PENDING_PAYMENT': {'PAID', 'CANCELLED'},
    'PAID': {'ACCEPTED', 'CANCELLED', 'REFUND_REQUESTED'},
    'ACCEPTED': {'PREPARING', 'REFUND_REQUESTED'},
    'PREPARING': {'READY_FOR_PICKUP', 'REFUND_REQUESTED'},
    'READY_FOR_PICKUP': {'DELIVERING', 'REFUND_REQUESTED'},
    'DELIVERING': {'DELIVERED', 'REFUND_REQUESTED'},
    'DELIVERED': {'COMPLETED', 'REFUND_REQUESTED'},
    'COMPLETED': {'REFUND_REQUESTED'},
    'CANCELLED': set(),
    'REFUND_REQUESTED': {'REFUNDED', 'CANCELLED'},
    'REFUNDED': set(),
}


def create_order_from_cart(user, address_id, note=''):
    """Create an Order from the user's cart. Returns (order, error_message)."""
    cart_items = CartItem.query.filter_by(user_id=user.id).all()
    if not cart_items:
        return None, '购物车为空，无法下单。'

    # Group cart items by shop (one order = one shop)
    shop_ids = set(item.menu_item.shop_id for item in cart_items)

    orders = []
    for shop_id in shop_ids:
        shop_items = [ci for ci in cart_items if ci.menu_item.shop_id == shop_id]
        if not shop_items:
            continue

        # Calculate total
        total = sum(item.subtotal for item in shop_items)

        # Validate stock
        for ci in shop_items:
            if ci.menu_item.stock < ci.quantity:
                return None, f'"{ci.menu_item.name}" 库存不足（剩余 {ci.menu_item.stock} 份）。'

        # Create order
        order = Order(
            order_number=generate_order_number(),
            user_id=user.id,
            shop_id=shop_id,
            address_id=address_id,
            total_amount=total,
            status='PENDING_PAYMENT',
            note=note,
        )
        db.session.add(order)
        db.session.flush()

        # Create order items (snapshot pattern)
        for ci in shop_items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=ci.menu_item_id,
                item_name=ci.menu_item.name,
                quantity=ci.quantity,
                unit_price=ci.menu_item.price,
                subtotal=ci.subtotal,
            )
            db.session.add(order_item)
            # Decrement stock
            ci.menu_item.stock -= ci.quantity
            # Remove cart item
            db.session.delete(ci)

        orders.append(order)

    db.session.commit()
    return orders, None


def transition_order(order, new_status):
    """Transition an order to a new status. Raises ValueError on invalid transition."""
    allowed = ORDER_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise ValueError(
            f'无效的状态转换: {order.status} → {new_status}。'
            f'允许的目标状态: {", ".join(allowed) if allowed else "无（终结状态）"}'
        )
    order.status = new_status
    order.updated_at = datetime.utcnow()
    db.session.commit()
    return order


def get_orders_for_user(user_id, page=1, per_page=10):
    """Get paginated orders for a user."""
    return Order.query.filter_by(user_id=user_id).order_by(
        Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)


def get_orders_for_shop(shop_id, page=1, per_page=10, status=None):
    """Get paginated orders for a shop."""
    query = Order.query.filter_by(shop_id=shop_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)


def get_available_orders_for_rider(page=1, per_page=10):
    """Get orders ready for rider pickup."""
    return Order.query.filter_by(status='READY_FOR_PICKUP').order_by(
        Order.created_at.asc()).paginate(page=page, per_page=per_page, error_out=False)
