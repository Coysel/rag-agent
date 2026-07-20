"""Merchant dashboard, shop, and menu management views."""
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.merchant import merchant_bp
from app.blueprints.merchant.forms import ShopForm, MenuItemForm
from app.models.shop import Shop
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.utils.decorators import role_required
from sqlalchemy import func


@merchant_bp.before_request
@login_required
@role_required('merchant')
def check_merchant():
    if not current_user.is_approved:
        flash('您的商家账号尚未通过审核', 'warning')
        return redirect(url_for('main.index'))


@merchant_bp.route('/dashboard')
def dashboard():
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop:
        return redirect(url_for('merchant.shop'))

    pending_count = Order.query.filter_by(shop_id=shop.id, status='PAID').count()
    preparing_count = Order.query.filter_by(shop_id=shop.id, status='PREPARING').count()
    today_orders = Order.query.filter(
        Order.shop_id == shop.id,
        func.date(Order.created_at) == func.date(datetime.utcnow())
    ).count()
    today_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.shop_id == shop.id,
        Order.status.in_(['COMPLETED', 'DELIVERED']),
        func.date(Order.created_at) == func.date(datetime.utcnow())
    ).scalar() or 0

    recent_orders = Order.query.filter_by(shop_id=shop.id).order_by(
        Order.created_at.desc()).limit(5).all()

    return render_template('merchant_dashboard.html', shop=shop, pending_count=pending_count,
                           preparing_count=preparing_count, today_orders=today_orders,
                           today_revenue=today_revenue, recent_orders=recent_orders)


# --- Shop Management ---
@merchant_bp.route('/shop', methods=['GET', 'POST'])
def shop():
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    form = ShopForm()
    if form.validate_on_submit():
        if shop:
            shop.name = form.name.data
            shop.description = form.description.data
            shop.address = form.address.data
            shop.phone = form.phone.data
        else:
            shop = Shop(
                merchant_id=current_user.id,
                name=form.name.data,
                description=form.description.data,
                address=form.address.data,
                phone=form.phone.data,
                status='pending',
            )
            db.session.add(shop)
        db.session.commit()
        flash('店铺信息已更新', 'success')
        return redirect(url_for('merchant.shop'))
    elif request.method == 'GET' and shop:
        form.name.data = shop.name
        form.description.data = shop.description
        form.address.data = shop.address
        form.phone.data = shop.phone
    return render_template('shop_manage.html', form=form, shop=shop)


# --- Menu Management ---
@merchant_bp.route('/menu')
def menu():
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop:
        flash('请先创建店铺', 'warning')
        return redirect(url_for('merchant.shop'))
    menu_items = MenuItem.query.filter_by(shop_id=shop.id).order_by(
        MenuItem.category, MenuItem.name).all()
    form = MenuItemForm()
    return render_template('menu_manage.html', menu_items=menu_items, form=form)


@merchant_bp.route('/menu/add', methods=['POST'])
def menu_add():
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop:
        flash('请先创建店铺', 'warning')
        return redirect(url_for('merchant.shop'))
    form = MenuItemForm()
    if form.validate_on_submit():
        item = MenuItem(
            shop_id=shop.id,
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock=form.stock.data,
            category=form.category.data,
            is_available=(form.is_available.data == '1'),
        )
        db.session.add(item)
        db.session.commit()
        flash(f'"{item.name}" 已添加', 'success')
    return redirect(url_for('merchant.menu'))


@merchant_bp.route('/menu/edit/<int:item_id>', methods=['POST'])
def menu_edit(item_id):
    item = MenuItem.query.get_or_404(item_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop or item.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.menu'))
    form = MenuItemForm()
    if form.validate_on_submit():
        item.name = form.name.data
        item.description = form.description.data
        item.price = form.price.data
        item.stock = form.stock.data
        item.category = form.category.data
        item.is_available = (form.is_available.data == '1')
        db.session.commit()
        flash(f'"{item.name}" 已更新', 'success')
    return redirect(url_for('merchant.menu'))


@merchant_bp.route('/menu/toggle/<int:item_id>', methods=['POST'])
def menu_toggle(item_id):
    item = MenuItem.query.get_or_404(item_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop or item.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.menu'))
    item.is_available = not item.is_available
    db.session.commit()
    flash(f'"{item.name}" 已{"上架" if item.is_available else "下架"}', 'info')
    return redirect(url_for('merchant.menu'))


@merchant_bp.route('/menu/delete/<int:item_id>', methods=['POST'])
def menu_delete(item_id):
    item = MenuItem.query.get_or_404(item_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop or item.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.menu'))
    db.session.delete(item)
    db.session.commit()
    flash(f'"{item.name}" 已删除', 'info')
    return redirect(url_for('merchant.menu'))
