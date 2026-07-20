"""User reviews, refunds, and payments views."""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.blueprints.user import user_bp
from app.blueprints.user.forms import ReviewForm, RefundForm
from app.models.order import Order
from app.models.payment import Payment
from app.models.review import Review
from app.models.refund import Refund
from app.services.order_service import transition_order
from app.utils.decorators import role_required


# --- Reviews ---
@user_bp.route('/reviews')
@login_required
@role_required('user')
def reviews():
    reviews = Review.query.filter_by(user_id=current_user.id).order_by(
        Review.created_at.desc()).limit(50).all()
    return render_template('reviews.html', reviews=reviews)


@user_bp.route('/reviews/create', methods=['POST'])
@login_required
@role_required('user')
def review_create():
    form = ReviewForm()
    if form.validate_on_submit():
        existing = Review.query.filter_by(
            order_id=form.order_id.data,
            target_type=form.target_type.data,
            target_id=form.target_id.data,
        ).first()
        if existing:
            flash('您已经对此对象评价过了', 'warning')
            return redirect(url_for('user.order_detail', order_id=form.order_id.data))

        review = Review(
            order_id=form.order_id.data,
            user_id=current_user.id,
            target_type=form.target_type.data,
            target_id=form.target_id.data,
            rating=form.rating.data,
            comment=form.comment.data,
        )
        db.session.add(review)

        if form.target_type.data == 'merchant':
            from app.models.shop import Shop
            shop = Shop.query.get(form.target_id.data)
            if shop:
                avg = db.session.query(
                    db.func.avg(Review.rating)
                ).filter_by(target_type='merchant', target_id=shop.id).scalar() or 0
                shop.rating = round(avg, 1)

        db.session.commit()
        flash('评价提交成功！', 'success')
        return redirect(url_for('user.order_detail', order_id=form.order_id.data))
    flash('评价提交失败', 'danger')
    return redirect(request.referrer or url_for('user.orders'))


# --- Refunds ---
@user_bp.route('/refunds')
@login_required
@role_required('user')
def refunds():
    refunds_list = Refund.query.filter_by(user_id=current_user.id).order_by(
        Refund.created_at.desc()).all()
    return render_template('refunds.html', refunds=refunds_list)


@user_bp.route('/refunds/request', methods=['POST'])
@login_required
@role_required('user')
def refund_request():
    form = RefundForm()
    if form.validate_on_submit():
        order = Order.query.get_or_404(form.order_id.data)
        if order.user_id != current_user.id:
            flash('无权操作', 'danger')
            return redirect(url_for('user.orders'))

        existing = Refund.query.filter_by(order_id=order.id).first()
        if existing:
            flash('该订单已有退款申请', 'warning')
            return redirect(url_for('user.order_detail', order_id=order.id))

        try:
            transition_order(order, 'REFUND_REQUESTED')
            refund = Refund(
                order_id=order.id,
                user_id=current_user.id,
                reason=form.reason.data,
                amount=order.total_amount,
            )
            db.session.add(refund)
            db.session.commit()
            flash('退款申请已提交，请等待商家审核', 'info')
        except ValueError as e:
            flash(str(e), 'danger')
        return redirect(url_for('user.order_detail', order_id=order.id))
    flash('退款申请提交失败', 'danger')
    return redirect(url_for('user.orders'))


# --- Payments ---
@user_bp.route('/payments')
@login_required
@role_required('user')
def payments():
    payments_list = Payment.query.join(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).limit(50).all()
    return render_template('payments.html', payments=payments_list)
