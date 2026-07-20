from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='user', nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    addresses = db.relationship('Address', backref='user', lazy='dynamic',
                                foreign_keys='Address.user_id')
    cart_items = db.relationship('CartItem', backref='user', lazy='dynamic')
    orders = db.relationship('Order', backref='customer', lazy='dynamic',
                             foreign_keys='Order.user_id')
    shop = db.relationship('Shop', backref='merchant', uselist=False, lazy=True)
    rider_orders = db.relationship('Order', backref='rider', lazy='dynamic',
                                   foreign_keys='Order.rider_id')
    reviews = db.relationship('Review', backref='author', lazy='dynamic')
    refunds = db.relationship('Refund', backref='requester', lazy='dynamic',
                              foreign_keys='Refund.user_id')
    rider_location = db.relationship('RiderLocation', backref='rider_ref', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_merchant(self):
        return self.role == 'merchant'

    @property
    def is_rider(self):
        return self.role == 'rider'

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
