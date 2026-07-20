"""User order views: checkout, orders, payment, cancel, confirm."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.user import user_bp
from app.blueprints.user.forms import CheckoutForm
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.address import Address
from app.services.order_service import (
    create_order_from_cart, transition_order, get_orders_for_user
)
from app.services.payment_service import process_payment
from app.utils.decorators import role_required


@user_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@role_required('user')
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('购物车为空', 'warning')
        return redirect(url_for('user.cart'))

    addresses = Address.query.filter_by(user_id=current_user.id).order_by(
        Address.is_default.desc()).all()
    form = CheckoutForm()
    form.address_id.choices = [(a.id, f'{a.label}: {a.address_detail}') for a in addresses]

    shop_groups = {}
    for item in cart_items:
        shop = item.menu_item.shop
        if shop.id not in shop_groups:
            shop_groups[shop.id] = {'shop': shop, 'items': []}
        shop_groups[shop.id]['items'].append(item)
    total = sum(item.subtotal for item in cart_items)

    if form.validate_on_submit():
        orders, error = create_order_from_cart(
            current_user, form.address_id.data, form.note.data)
        if error:
            flash(error, 'danger')
            return render_template('checkout.html', form=form, shop_groups=shop_groups,
                                   total=total)
        if len(orders) == 1:
            flash('订单已生成，请完成支付', 'success')
            return redirect(url_for('user.order_detail', order_id=orders[0].id))
        flash(f'已生成 {len(orders)} 个订单，请分别完成支付', 'success')
        return redirect(url_for('user.orders'))

    return render_template('checkout.html', form=form, shop_groups=shop_groups, total=total)


@user_bp.route('/orders')
@login_required
@role_required('user')
def orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = Order.query.filter_by(user_id=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False)
    return render_template('user_order_list.html', orders=pagination.items, pagination=pagination,
                           status_filter=status_filter)


@user_bp.route('/orders/<int:order_id>')
@login_required
@role_required('user')
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('无权查看该订单', 'danger')
        return redirect(url_for('user.orders'))
    return render_template('user_order_detail.html', order=order)


@user_bp.route('/orders/<int:order_id>/pay', methods=['POST'])
@login_required
@role_required('user')
def pay_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.orders'))
    payment, error = process_payment(order)
    if error:
        flash(error, 'danger')
    else:
        flash(f'支付成功！交易号: {payment.transaction_id}', 'success')
    return redirect(url_for('user.order_detail', order_id=order.id))


@user_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
@role_required('user')
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.orders'))
    try:
        transition_order(order, 'CANCELLED')
        flash('订单已取消', 'info')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('user.order_detail', order_id=order.id))


@user_bp.route('/orders/<int:order_id>/confirm', methods=['POST'])
@login_required
@role_required('user')
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.orders'))
    try:
        transition_order(order, 'COMPLETED')
        flash('已确认收货，感谢您的惠顾！', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('user.order_detail', order_id=order.id))
