from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.admin import admin_bp
from app.models.user import User
from app.models.shop import Shop
from app.models.order import Order
from app.models.complaint import Complaint
from app.services.statistics_service import (
    platform_summary, revenue_by_period, order_stats, user_growth
)
from app.utils.decorators import role_required


@admin_bp.before_request
@login_required
@role_required('admin')
def check_admin():
    pass


@admin_bp.route('/dashboard')
def dashboard():
    stats = platform_summary()
    orders = order_stats()
    return render_template('admin_dashboard.html', stats=stats, orders=orders)


# --- User Management ---
@admin_bp.route('/users')
def users():
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', '')
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)
    return render_template('users.html', users=pagination.items, pagination=pagination,
                           role_filter=role_filter)


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
def user_toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('不能禁用自己', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'用户 "{user.username}" 已{"启用" if user.is_active else "禁用"}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
def user_change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('不能修改自己的角色', 'danger')
        return redirect(url_for('admin.users'))
    new_role = request.form.get('role', 'user')
    if new_role not in ['user', 'merchant', 'rider', 'admin']:
        flash('无效的角色', 'danger')
        return redirect(url_for('admin.users'))
    user.role = new_role
    db.session.commit()
    flash(f'用户 "{user.username}" 角色已更新为 {new_role}', 'success')
    return redirect(url_for('admin.users'))


# --- Merchant Approval ---
@admin_bp.route('/merchants/pending')
def merchants_pending():
    pending = User.query.filter_by(role='merchant', is_approved=False, is_active=True).all()
    shops = Shop.query.filter_by(status='pending').all()
    return render_template('merchant_applications.html', pending_merchants=pending,
                           pending_shops=shops)


@admin_bp.route('/merchants/<int:user_id>/approve', methods=['POST'])
def merchant_approve(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'merchant':
        flash('该用户不是商家', 'danger')
        return redirect(url_for('admin.merchants_pending'))
    user.is_approved = True
    if user.shop:
        user.shop.status = 'approved'
    db.session.commit()
    flash(f'商家 "{user.name or user.username}" 已通过审核', 'success')
    return redirect(url_for('admin.merchants_pending'))


@admin_bp.route('/merchants/<int:user_id>/reject', methods=['POST'])
def merchant_reject(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'merchant':
        flash('该用户不是商家', 'danger')
        return redirect(url_for('admin.merchants_pending'))
    if user.shop:
        user.shop.status = 'rejected'
    db.session.commit()
    flash(f'商家 "{user.name or user.username}" 已拒绝', 'info')
    return redirect(url_for('admin.merchants_pending'))


# --- Shop Management ---
@admin_bp.route('/shops')
def shops():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = Shop.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    pagination = query.order_by(Shop.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)
    return render_template('shops.html', shops=pagination.items, pagination=pagination,
                           status_filter=status_filter)


@admin_bp.route('/shops/<int:shop_id>/status', methods=['POST'])
def shop_status(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    new_status = request.form.get('status', 'approved')
    if new_status not in ['approved', 'rejected', 'closed', 'pending']:
        flash('无效的状态', 'danger')
        return redirect(url_for('admin.shops'))
    shop.status = new_status
    db.session.commit()
    flash(f'店铺 "{shop.name}" 状态已更新为 {new_status}', 'success')
    return redirect(url_for('admin.shops'))


# --- Orders ---
@admin_bp.route('/orders')
def orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)
    return render_template('orders.html', orders=pagination.items, pagination=pagination,
                           status_filter=status_filter)


# --- Complaints ---
@admin_bp.route('/complaints')
def complaints():
    page = request.args.get('page', 1, type=int)
    pagination = Complaint.query.order_by(Complaint.created_at.desc()).paginate(
        page=page, per_page=15, error_out=False)
    return render_template('complaints.html', complaints=pagination.items, pagination=pagination)


@admin_bp.route('/complaints/<int:complaint_id>/resolve', methods=['POST'])
def complaint_resolve(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    complaint.status = 'resolved'
    complaint.admin_reply = request.form.get('admin_reply', '')
    complaint.resolved_at = datetime.utcnow()
    db.session.commit()
    flash('投诉已处理', 'success')
    return redirect(url_for('admin.complaints'))


# --- Statistics ---
@admin_bp.route('/statistics')
def statistics():
    period = request.args.get('period', 'month')
    summary = platform_summary()
    revenue = revenue_by_period(period)
    stats = order_stats()
    growth = user_growth()
    return render_template('statistics.html', summary=summary, revenue=revenue,
                           stats=stats, growth=growth, period=period)
