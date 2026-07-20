from app.extensions import db
from app.models.user import User
from app.models.rider_location import RiderLocation


def find_available_riders():
    """Find riders who are not currently assigned to active deliveries."""
    active_order_ids = db.session.query(
        RiderLocation.order_id
    ).filter(RiderLocation.order_id.isnot(None)).all()
    active_rider_ids = {r.rider_id for r in db.session.query(
        RiderLocation.rider_id
    ).filter(RiderLocation.order_id.isnot(None)).all()}

    all_riders = User.query.filter_by(role='rider', is_active=True, is_approved=True).all()
    available = [r for r in all_riders if r.id not in active_rider_ids]
    return available


def dispatch_rider(order):
    """Assign an available rider to an order. Returns rider or None."""
    available = find_available_riders()
    if not available:
        return None

    # Simple round-robin: pick the first available rider
    rider = available[0]
    order.rider_id = rider.id

    # Create or update rider location
    loc = RiderLocation.query.filter_by(rider_id=rider.id).first()
    if loc:
        loc.order_id = order.id
    else:
        loc = RiderLocation(
            rider_id=rider.id,
            order_id=order.id,
            latitude=39.9042,  # Default: Beijing
            longitude=116.4074,
        )
        db.session.add(loc)

    db.session.commit()
    return rider


def assign_rider_to_order(order, rider):
    """Manually assign a rider to an order."""
    order.rider_id = rider.id

    loc = RiderLocation.query.filter_by(rider_id=rider.id).first()
    if loc:
        loc.order_id = order.id
    else:
        loc = RiderLocation(
            rider_id=rider.id,
            order_id=order.id,
            latitude=39.9042,
            longitude=116.4074,
        )
        db.session.add(loc)

    db.session.commit()
