from datetime import datetime
from app.extensions import db


class Shop(db.Model):
    __tablename__ = 'shops'

    id = db.Column(db.Integer, primary_key=True)
    merchant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(300))
    phone = db.Column(db.String(20))
    image_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending', index=True)
    rating = db.Column(db.Float, default=0.0)
    total_sales = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    menu_items = db.relationship('MenuItem', backref='shop', lazy='dynamic',
                                 cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='shop', lazy='dynamic')

    def __repr__(self):
        return f'<Shop {self.name}>'
