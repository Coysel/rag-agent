"""User cart views."""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.user import user_bp
from app.models.cart_item import CartItem
from app.models.menu_item import MenuItem
from app.utils.decorators import role_required


@user_bp.route('/cart')
@login_required
@role_required('user')
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).order_by(
        CartItem.created_at.desc()).all()
    shop_groups = {}
    for item in cart_items:
        shop = item.menu_item.shop
        if shop.id not in shop_groups:
            shop_groups[shop.id] = {'shop': shop, 'items': []}
        shop_groups[shop.id]['items'].append(item)
    total = sum(item.subtotal for item in cart_items)
    return render_template('cart.html', shop_groups=shop_groups, total=total)


@user_bp.route('/cart/add', methods=['POST'])
@login_required
@role_required('user')
def cart_add():
    menu_item_id = request.form.get('menu_item_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    if not menu_item_id:
        if request.headers.get('Accept') == 'application/json':
            return jsonify(success=False, message='缺少菜品ID')
        flash('缺少菜品ID', 'danger')
        return redirect(request.referrer or url_for('main.index'))

    menu_item = MenuItem.query.get_or_404(menu_item_id)
    if menu_item.stock < quantity:
        msg = f'"{menu_item.name}" 库存不足'
        if request.headers.get('Accept') == 'application/json':
            return jsonify(success=False, message=msg)
        flash(msg, 'danger')
        return redirect(request.referrer or url_for('main.index'))

    existing = CartItem.query.filter_by(
        user_id=current_user.id, menu_item_id=menu_item_id).first()
    if existing:
        existing.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, menu_item_id=menu_item_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()

    if request.headers.get('Accept') == 'application/json':
        return jsonify(success=True, message=f'"{menu_item.name}" 已加入购物车')
    flash(f'"{menu_item.name}" 已加入购物车', 'success')
    return redirect(request.referrer or url_for('main.index'))


@user_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
@role_required('user')
def cart_update(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.cart'))
    quantity = request.form.get('quantity', 0, type=int)
    if quantity <= 0:
        db.session.delete(cart_item)
        flash('已从购物车移除', 'info')
    else:
        cart_item.quantity = min(quantity, cart_item.menu_item.stock)
        flash('购物车已更新', 'success')
    db.session.commit()
    return redirect(url_for('user.cart'))


@user_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
@role_required('user')
def cart_remove(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.user_id != current_user.id:
        flash('无权操作', 'danger')
        return redirect(url_for('user.cart'))
    db.session.delete(cart_item)
    db.session.commit()
    flash('已从购物车移除', 'info')
    return redirect(url_for('user.cart'))
