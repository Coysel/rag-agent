"""Merchant revenue, refund, and review management views."""
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.merchant import merchant_bp
from app.blueprints.merchant.forms import ReviewReplyForm
from app.models.shop import Shop
from app.models.order import Order
from app.models.review import Review, ReviewReply
from app.models.refund import Refund
from app.services.order_service import transition_order
from app.services.payment_service import refund_payment
from app.utils.decorators import role_required
from sqlalchemy import func


# --- Revenue ---
@merchant_bp.route('/revenue')
def revenue():
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if not shop:
        return redirect(url_for('merchant.shop'))

    period = request.args.get('period', 'today')
    if period == 'today':
        date_filter = func.date(Order.created_at) == func.date(datetime.utcnow())
    elif period == 'week':
        date_filter = func.date(Order.created_at) >= func.date(datetime.utcnow(), '-7 days')
    elif period == 'month':
        date_filter = func.date(Order.created_at) >= func.date(datetime.utcnow(), '-30 days')
    else:
        date_filter = True

    total_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.shop_id == shop.id,
        Order.status.in_(['COMPLETED', 'DELIVERED']),
        date_filter,
    ).scalar() or 0

    order_count = Order.query.filter(
        Order.shop_id == shop.id,
        Order.status.in_(['COMPLETED', 'DELIVERED']),
        date_filter,
    ).count()

    return render_template('revenue.html', shop=shop, total_revenue=total_revenue,
                           order_count=order_count, period=period)


# --- Refund Management ---
@merchant_bp.route('/refunds')
def refunds():
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    refund_requests = Refund.query.join(Order).filter(
        Order.shop_id == shop.id
    ).order_by(Refund.created_at.desc()).all()
    return render_template('refunds.html', refunds=refund_requests)


@merchant_bp.route('/refunds/<int:refund_id>/approve', methods=['POST'])
def refund_approve(refund_id):
    refund = Refund.query.get_or_404(refund_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if refund.order.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.refunds'))
    refund.status = 'completed'
    refund.processed_by = current_user.id
    refund.processed_at = datetime.utcnow()
    transition_order(refund.order, 'REFUNDED')
    refund_payment(refund.order)
    db.session.commit()
    flash('退款已批准', 'success')
    return redirect(url_for('merchant.refunds'))


@merchant_bp.route('/refunds/<int:refund_id>/reject', methods=['POST'])
def refund_reject(refund_id):
    refund = Refund.query.get_or_404(refund_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if refund.order.shop_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.refunds'))
    refund.status = 'rejected'
    refund.processed_by = current_user.id
    refund.processed_at = datetime.utcnow()
    transition_order(refund.order, 'CANCELLED')
    db.session.commit()
    flash('退款申请已拒绝', 'info')
    return redirect(url_for('merchant.refunds'))


# --- Review Management ---
@merchant_bp.route('/reviews')
def reviews():
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    reviews_list = Review.query.filter_by(target_type='merchant', target_id=shop.merchant_id).order_by(
        Review.created_at.desc()).limit(50).all()
    form = ReviewReplyForm()
    return render_template('reviews.html', reviews=reviews_list, form=form)


@merchant_bp.route('/reviews/<int:review_id>/reply', methods=['POST'])
def review_reply(review_id):
    review = Review.query.get_or_404(review_id)
    shop = Shop.query.filter_by(merchant_id=current_user.id).first()
    if review.target_type == 'merchant' and review.target_id != shop.id:
        flash('无权操作', 'danger')
        return redirect(url_for('merchant.reviews'))
    form = ReviewReplyForm()
    if form.validate_on_submit():
        reply = ReviewReply(
            review_id=review.id,
            merchant_id=current_user.id,
            content=form.content.data,
        )
        db.session.add(reply)
        db.session.commit()
        flash('回复已提交', 'success')
    return redirect(url_for('merchant.reviews'))
