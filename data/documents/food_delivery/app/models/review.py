from datetime import datetime
from app.extensions import db


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    replies = db.relationship('ReviewReply', backref='review', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('order_id', 'target_type', 'target_id',
                            name='uq_order_target'),
    )

    def __repr__(self):
        return f'<Review {self.target_type}={self.target_id} ★{self.rating}>'


class ReviewReply(db.Model):
    __tablename__ = 'review_replies'

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'), nullable=False)
    merchant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    merchant = db.relationship('User', lazy='joined')

    def __repr__(self):
        return f'<ReviewReply review={self.review_id}>'
