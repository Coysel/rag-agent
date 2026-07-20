from datetime import datetime
from app.extensions import db


class Complaint(db.Model):
    __tablename__ = 'complaints'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_type = db.Column(db.String(20))
    target_id = db.Column(db.Integer)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    admin_reply = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship('Order', lazy='joined')
    user = db.relationship('User', foreign_keys=[user_id], lazy='joined')

    def __repr__(self):
        return f'<Complaint user={self.user_id} {self.status}>'
