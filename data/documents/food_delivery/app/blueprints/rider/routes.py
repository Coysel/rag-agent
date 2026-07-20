from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.rider import rider_bp
from app.blueprints.rider.forms import LocationForm
from app.models.order import Order
from app.models.user import User
from app.models.payment import Payment
from app.models.rider_location import RiderLocation
from app.services.order_service import transition_order, get_available_orders_for_rider
from app.services.dispatch_service import assign_rider_to_order
from app.utils.decorators import role_required
from sqlalchemy import func


@rider_bp.before_request
@login_required
@role_required('rider')
def check_rider():
    pass


@rider_bp.route('/dashboard')
def dashboard():
    available_orders = Order.query.filter_by(status='READY_FOR_PICKUP').count()
    active_deliveries = Order.query.filter(
        Order.rider_id == current_user.id,
        Order.status.in_(['DELIVERING'])
    ).count()
    today_deliveries = Order.query.filter(
        Order.rider_id == current_user.id,
        Order.status == 'COMPLETED',
        func.date(Order.updated_at) == func.date(datetime.utcnow()),
    ).count()

    form = LocationForm()
    return render_template('rider_dashboard.html', form=form,
                           available_orders=available_orders,
                           active_deliveries=active_deliveries,
                           today_deliveries=today_deliveries)


@rider_bp.route('/orders')
def available_orders():
    """View available orders to pick up."""
    page = request.args.get('page', 1, type=int)
    pagination = get_available_orders_for_rider(page=page)
    return render_template('rider_available_orders.html', orders=pagination.items, pagination=pagination)


@rider_bp.route('/orders/active')
def active_orders():
    """View currently delivering orders."""
    orders = Order.query.filter(
        Order.rider_id == current_user.id,
        Order.status.in_(['DELIVERING'])
    ).order_by(Order.created_at.desc()).all()
    return render_template('active_orders.html', orders=orders)


@rider_bp.route('/orders/<int:order_id>/accept', methods=['POST'])
def order_accept(order_id):
    """Accept a dispatch / pick up an order."""
    order = Order.query.get_or_404(order_id)
    if order.status == 'READY_FOR_PICKUP':
        assign_rider_to_order(order, current_user)
        transition_order(order, 'DELIVERING')
        flash(f'接单成功！请前往 {order.shop.name} 取餐', 'success')
    elif order.status == 'DELIVERING' and order.rider_id == current_user.id:
        flash('您已在配送此订单', 'info')
    else:
        flash('无法接单，订单状态不正确', 'danger')
    return redirect(url_for('rider.active_orders'))


@rider_bp.route('/orders/<int:order_id>/pickup', methods=['POST'])
def order_pickup(order_id):
    """Mark order as picked up from merchant."""
    order = Order.query.get_or_404(order_id)
    if order.rider_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('rider.active_orders'))
    # Keep status as DELIVERING but note pickup
    flash('已取餐，请尽快送达', 'info')
    return redirect(url_for('rider.order_detail', order_id=order.id))


@rider_bp.route('/orders/<int:order_id>/deliver', methods=['POST'])
def order_deliver(order_id):
    """Mark order as delivered."""
    order = Order.query.get_or_404(order_id)
    if order.rider_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('rider.active_orders'))
    try:
        transition_order(order, 'DELIVERED')
        # Clear rider's current order
        loc = RiderLocation.query.filter_by(rider_id=current_user.id).first()
        if loc:
            loc.order_id = None
            db.session.commit()
        flash('已送达！', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('rider.dashboard'))


@rider_bp.route('/orders/<int:order_id>')
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.rider_id and order.rider_id != current_user.id:
        flash('无权查看', 'danger')
        return redirect(url_for('rider.dashboard'))
    return render_template('rider_order_detail.html', order=order)


@rider_bp.route('/location/update', methods=['POST'])
def location_update():
    """Update rider's GPS location."""
    form = LocationForm()
    if form.validate_on_submit():
        loc = RiderLocation.query.filter_by(rider_id=current_user.id).first()
        if loc:
            loc.latitude = form.latitude.data
            loc.longitude = form.longitude.data
        else:
            loc = RiderLocation(
                rider_id=current_user.id,
                latitude=form.latitude.data,
                longitude=form.longitude.data,
            )
            db.session.add(loc)
        db.session.commit()
        flash('位置已更新', 'info')
    return redirect(url_for('rider.dashboard'))


@rider_bp.route('/history')
def history():
    page = request.args.get('page', 1, type=int)
    pagination = Order.query.filter(
        Order.rider_id == current_user.id,
        Order.status.in_(['DELIVERED', 'COMPLETED'])
    ).order_by(Order.updated_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    return render_template('history.html', orders=pagination.items, pagination=pagination)


@rider_bp.route('/earnings')
def earnings():
    period = request.args.get('period', 'today')
    if period == 'today':
        date_filter = func.date(Order.updated_at) == func.date(datetime.utcnow())
    elif period == 'week':
        date_filter = func.date(Order.updated_at) >= func.date(datetime.utcnow(), '-7 days')
    elif period == 'month':
        date_filter = func.date(Order.updated_at) >= func.date(datetime.utcnow(), '-30 days')
    else:
        date_filter = True

    completed = Order.query.filter(
        Order.rider_id == current_user.id,
        Order.status.in_(['COMPLETED', 'DELIVERED']),
        date_filter,
    ).count()

    # Simple earnings: ¥5 per delivery
    earning_per_delivery = 5.0
    total_earnings = completed * earning_per_delivery

    return render_template('earnings.html', completed=completed,
                           total_earnings=total_earnings, period=period,
                           earning_per_delivery=earning_per_delivery)
