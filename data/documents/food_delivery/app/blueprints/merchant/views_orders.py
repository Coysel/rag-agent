"""Merchant order management views."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.blueprints.merchant import merchant_bp
from app.models.shop import Shop
from app.models.order import Order
from app.services.order_service import transition_order, get_orders_for_shop
from app.services.payment_service import refund_payment
from app.services.dispatch_service import dispatch_rider
from app.utils.decorators import role_required


@merchant_bp.route('/orders')
def orders():
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop:
        return redirect(url_for('merchant.shop'))
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    pagination = get_orders_for_shop(shop.id, page=page, status=status or None)
    return render_template('merchant_order_list.html', orders=pagination.items, pagination=pagination,
                           status_filter=status)


@merchant_bp.route('/orders/<int:order_id>')
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop or order.shop_id != shop.id:
        flash('无权查看', 'danger')
        return redirect(url_for('merchant.orders'))
    return render_template('merchant_order_detail.html', order=order)


@merchant_bp.route('/orders/<int:order_id>/accept', methods=['POST'])
def order_accept(order_id):
    order = Order.query.get_or_404(order_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop or order.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.orders'))
    try:
        transition_order(order, 'ACCEPTED')
        flash('已接单，请尽快备餐', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('merchant.order_detail', order_id=order.id))


@merchant_bp.route('/orders/<int:order_id>/preparing', methods=['POST'])
def order_preparing(order_id):
    order = Order.query.get_or_404(order_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop or order.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.orders'))
    try:
        transition_order(order, 'PREPARING')
        flash('已开始备餐', 'info')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('merchant.order_detail', order_id=order.id))


@merchant_bp.route('/orders/<int:order_id>/ready', methods=['POST'])
def order_ready(order_id):
    order = Order.query.get_or_404(order_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop or order.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.orders'))
    try:
        transition_order(order, 'READY_FOR_PICKUP')
        rider = dispatch_rider(order)
        if rider:
            flash(f'备餐完成！已分配骑手 {rider.name}', 'success')
        else:
            flash('备餐完成！等待骑手接单', 'info')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('merchant.order_detail', order_id=order.id))


@merchant_bp.route('/orders/<int:order_id>/reject', methods=['POST'])
def order_reject(order_id):
    order = Order.query.get_or_404(order_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop or order.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.orders'))
    try:
        transition_order(order, 'CANCELLED')
        if order.payment and order.payment.status == 'success':
            refund_payment(order)
            flash('已拒绝订单并退款', 'info')
        else:
            flash('已拒绝订单', 'info')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('merchant.orders'))
