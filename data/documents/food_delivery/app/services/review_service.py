from app.extensions import db
from app.models.review import Review
from app.models.shop import Shop
from sqlalchemy import func


def create_review(user_id, order_id, target_type, target_id, rating, comment=''):
    """Create a review. Returns (review, error_message)."""
    existing = Review.query.filter_by(
        order_id=order_id, target_type=target_type, target_id=target_id
    ).first()
    if existing:
        return None, '您已经对此对象评价过了。'

    review = Review(
        order_id=order_id,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        rating=rating,
        comment=comment,
    )
    db.session.add(review)
    db.session.commit()
    return review, None


def update_shop_rating(shop_id):
    """Recalculate and update shop average rating."""
    avg_rating = db.session.query(func.avg(Review.rating)).filter_by(
        target_type='merchant', target_id=shop_id
    ).scalar()
    shop = Shop.query.get(shop_id)
    if shop:
        shop.rating = round(avg_rating, 1) if avg_rating else 0.0
        db.session.commit()


def get_shop_reviews(shop_merchant_id, limit=20):
    """Get reviews for a specific shop/merchant."""
    return Review.query.filter_by(
        target_type='merchant', target_id=shop_merchant_id
    ).order_by(Review.created_at.desc()).limit(limit).all()
