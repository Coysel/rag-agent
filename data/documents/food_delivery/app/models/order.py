from datetime import datetime
from app.extensions import db


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shops.id'), nullable=False)
    rider_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default='PENDING_PAYMENT', index=True, nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='joined',
                            cascade='all, delete-orphan')
    payment = db.relationship('Payment', backref='order', uselist=False, lazy='joined')
    address = db.relationship('Address', lazy='joined')
    reviews = db.relationship('Review', backref='order', lazy='dynamic')
    refund = db.relationship('Refund', backref='order', uselist=False, lazy='joined')

    @property
    def status_label(self):
        from app.utils.helpers import get_status_label
        return get_status_label(self.status)

    @property
    def status_color(self):
        from app.utils.helpers import get_status_color
        return get_status_color(self.status)

    def __repr__(self):
        return f'<Order {self.order_number} [{self.status}]>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'))
    item_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    menu_item = db.relationship('MenuItem', lazy='joined')

    def __repr__(self):
        return f'<OrderItem {self.item_name} x{self.quantity}>'
