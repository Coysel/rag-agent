from datetime import datetime
from app.extensions import db


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'menu_item_id', name='uq_user_menu'),
    )

    menu_item = db.relationship('MenuItem', lazy='joined')

    @property
    def subtotal(self):
        return self.menu_item.price * self.quantity

    def __repr__(self):
        return f'<CartItem user={self.user_id} item={self.menu_item_id} x{self.quantity}>'
