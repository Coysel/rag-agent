"""Test database models."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.shop import Shop
from app.models.menu_item import MenuItem
from app.models.address import Address
from app.models.cart_item import CartItem
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.review import Review
from app.models.refund import Refund


class TestUserModel:
    """Tests for the User model."""

    def test_user_creation(self, app, db):
        """Create a User and verify all fields are stored correctly."""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com',
                name='Test User',
                phone='13800138000',
                role='user',
                is_approved=True,
            )
            user.set_password('securepass')
            db.add(user)
            db.commit()

            assert user.id is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            assert user.name == 'Test User'
            assert user.phone == '13800138000'
            assert user.role == 'user'
            assert user.is_approved is True
            assert user.is_active is True

    def test_user_password_hashing(self, app, db):
        """set_password and check_password work correctly."""
        with app.app_context():
            user = User(username='pwhash', email='pw@test.com')
            user.set_password('mypassword')
            db.add(user)
            db.commit()

            assert user.check_password('mypassword') is True
            assert user.check_password('wrongpassword') is False
            # The stored hash should differ from the raw password
            assert user.password_hash != 'mypassword'

    def test_user_unique_username(self, app, db):
        """Creating a duplicate username raises IntegrityError."""
        with app.app_context():
            user1 = User(username='uniqueuser', email='first@test.com')
            user1.set_password('pass123')
            db.add(user1)
            db.commit()

            user2 = User(username='uniqueuser', email='second@test.com')
            user2.set_password('pass456')
            db.add(user2)
            with pytest.raises(IntegrityError):
                db.commit()

    def test_user_unique_email(self, app, db):
        """Creating a duplicate email raises IntegrityError."""
        with app.app_context():
            user1 = User(username='emailtest1', email='same@test.com')
            user1.set_password('pass123')
            db.add(user1)
            db.commit()

            user2 = User(username='emailtest2', email='same@test.com')
            user2.set_password('pass456')
            db.add(user2)
            with pytest.raises(IntegrityError):
                db.commit()

    def test_user_roles(self, app, db):
        """Verify different roles work: user, merchant, rider, admin."""
        with app.app_context():
            roles = ['user', 'merchant', 'rider', 'admin']
            users = []
            for i, role in enumerate(roles):
                u = User(
                    username=f'roleuser{i}',
                    email=f'role{i}@test.com',
                    role=role,
                )
                u.set_password('pass123')
                db.add(u)
                users.append(u)
            db.commit()

            assert users[0].role == 'user'
            assert users[1].role == 'merchant'
            assert users[2].role == 'rider'
            assert users[3].role == 'admin'
            # Test the convenience properties
            assert users[1].is_merchant is True
            assert users[2].is_rider is True
            assert users[3].is_admin is True
            # Non-admin users should return False
            assert users[0].is_admin is False
            assert users[0].is_merchant is False
            assert users[0].is_rider is False


class TestShopModel:
    """Tests for the Shop and MenuItem models."""

    def test_shop_creation(self, app, db):
        """Create a Shop linked to a merchant and verify fields."""
        with app.app_context():
            merchant = User(
                username='shopmgr',
                email='shopmgr@test.com',
                role='merchant',
                is_approved=True,
            )
            merchant.set_password('pass123')
            db.add(merchant)
            db.flush()

            shop = Shop(
                merchant_id=merchant.id,
                name='My Restaurant',
                description='Delicious home-style food',
                address='456 Food Street',
                phone='010-87654321',
                status='approved',
                rating=4.5,
            )
            db.add(shop)
            db.commit()

            assert shop.id is not None
            assert shop.name == 'My Restaurant'
            assert shop.description == 'Delicious home-style food'
            assert shop.address == '456 Food Street'
            assert shop.phone == '010-87654321'
            assert shop.status == 'approved'
            assert shop.rating == 4.5
            assert shop.total_sales == 0
            assert shop.merchant_id == merchant.id
            # Verify the back-reference from merchant
            assert merchant.shop is not None
            assert merchant.shop.id == shop.id

    def test_menu_item_creation(self, app, db):
        """Create a MenuItem linked to a shop."""
        with app.app_context():
            merchant = User(
                username='menumerch',
                email='menumerch@test.com',
                role='merchant',
            )
            merchant.set_password('pass')
            db.add(merchant)
            db.flush()

            shop = Shop(merchant_id=merchant.id, name='Menu Shop')
            db.add(shop)
            db.flush()

            item = MenuItem(
                shop_id=shop.id,
                name='Pizza',
                description='Cheese and pepperoni',
                price=12.99,
                stock=50,
                category='热菜',
                is_available=True,
            )
            db.add(item)
            db.commit()

            assert item.id is not None
            assert item.name == 'Pizza'
            assert item.price == 12.99
            assert item.stock == 50
            assert item.category == '热菜'
            assert item.is_available is True
            assert item.shop_id == shop.id
            # Verify relationship
            assert item.shop.name == 'Menu Shop'


class TestAddressModel:
    """Tests for the Address model."""

    def test_address_creation(self, app, db):
        """Create an Address linked to a user."""
        with app.app_context():
            user = User(username='addruser', email='addr@test.com')
            user.set_password('pass')
            db.add(user)
            db.flush()

            address = Address(
                user_id=user.id,
                label='Home',
                address_detail='789 Home Avenue, Apt 4B',
                is_default=True,
            )
            db.add(address)
            db.commit()

            assert address.id is not None
            assert address.label == 'Home'
            assert address.address_detail == '789 Home Avenue, Apt 4B'
            assert address.is_default is True
            assert address.user_id == user.id
            # Verify relationship
            assert address.user.username == 'addruser'


class TestCartItemModel:
    """Tests for the CartItem model."""

    def test_cart_item_creation(self, app, db):
        """Create a CartItem and verify unique constraint on (user_id, menu_item_id)."""
        with app.app_context():
            user = User(username='cartuser', email='cart@test.com')
            user.set_password('pass')
            db.add(user)
            db.flush()

            merchant = User(username='cartmerch', email='cartm@test.com', role='merchant')
            merchant.set_password('pass')
            db.add(merchant)
            db.flush()

            shop = Shop(merchant_id=merchant.id, name='Cart Shop')
            db.add(shop)
            db.flush()

            item = MenuItem(shop_id=shop.id, name='Burger', price=8.99, stock=20)
            db.add(item)
            db.flush()

            cart_item = CartItem(user_id=user.id, menu_item_id=item.id, quantity=3)
            db.add(cart_item)
            db.commit()

            assert cart_item.id is not None
            assert cart_item.quantity == 3
            assert cart_item.subtotal == 8.99 * 3

            # Same user + same menu_item should violate unique constraint
            duplicate = CartItem(user_id=user.id, menu_item_id=item.id, quantity=1)
            db.add(duplicate)
            with pytest.raises(IntegrityError):
                db.commit()


class TestOrderModel:
    """Tests for the Order and OrderItem models."""

    def test_order_creation(self, app, db):
        """Create an Order with OrderItems and verify the snapshot pattern."""
        with app.app_context():
            user = User(username='orduser', email='ord@test.com')
            user.set_password('pass')
            db.add(user)
            db.flush()

            merchant = User(username='ordmerch', email='ordm@test.com', role='merchant')
            merchant.set_password('pass')
            db.add(merchant)
            db.flush()

            shop = Shop(merchant_id=merchant.id, name='Order Shop')
            db.add(shop)
            db.flush()

            item1 = MenuItem(shop_id=shop.id, name='Noodle', price=5.99, stock=100)
            item2 = MenuItem(shop_id=shop.id, name='Rice', price=3.99, stock=100)
            db.add_all([item1, item2])
            db.flush()

            addr = Address(user_id=user.id, address_detail='Order Address')
            db.add(addr)
            db.flush()

            order = Order(
                order_number='DDTEST001',
                user_id=user.id,
                shop_id=shop.id,
                address_id=addr.id,
                total_amount=15.96,
                status='PAID',
            )
            db.add(order)
            db.flush()

            oi1 = OrderItem(
                order_id=order.id,
                menu_item_id=item1.id,
                item_name=item1.name,
                quantity=2,
                unit_price=item1.price,
                subtotal=item1.price * 2,
            )
            oi2 = OrderItem(
                order_id=order.id,
                menu_item_id=item2.id,
                item_name=item2.name,
                quantity=1,
                unit_price=item2.price,
                subtotal=item2.price,
            )
            db.add_all([oi1, oi2])
            db.commit()

            assert order.id is not None
            assert order.order_number == 'DDTEST001'
            assert order.total_amount == 15.96
            # Snapshot pattern: OrderItem stores a copy of the item data
            assert len(order.items) == 2
            assert order.items[0].item_name == 'Noodle'
            assert order.items[0].unit_price == 5.99
            assert order.items[0].quantity == 2
            assert order.items[0].subtotal == 11.98
            assert order.items[1].item_name == 'Rice'
            assert order.items[1].unit_price == 3.99
            assert order.items[1].quantity == 1

    def test_order_status_default(self, app, db):
        """A new Order defaults to PENDING_PAYMENT status."""
        with app.app_context():
            user = User(username='defuser', email='def@test.com')
            user.set_password('pass')
            db.add(user)
            db.flush()

            merchant = User(username='defmerch', email='defm@test.com', role='merchant')
            merchant.set_password('pass')
            db.add(merchant)
            db.flush()

            shop = Shop(merchant_id=merchant.id, name='Default Shop')
            db.add(shop)
            db.flush()

            addr = Address(user_id=user.id, address_detail='Default Address')
            db.add(addr)
            db.flush()

            order = Order(
                order_number='DDTESTDEF',
                user_id=user.id,
                shop_id=shop.id,
                address_id=addr.id,
                total_amount=0.0,
            )
            db.add(order)
            db.commit()

            assert order.status == 'PENDING_PAYMENT'


class TestPaymentModel:
    """Tests for the Payment model."""

    def test_payment_creation(self, app, db):
        """Create a Payment linked to an order."""
        with app.app_context():
            user = User(username='payuser', email='pay@test.com')
            user.set_password('pass')
            db.add(user)
            db.flush()

            merchant = User(username='paymerch', email='paym@test.com', role='merchant')
            merchant.set_password('pass')
            db.add(merchant)
            db.flush()

            shop = Shop(merchant_id=merchant.id, name='Pay Shop')
            db.add(shop)
            db.flush()

            addr = Address(user_id=user.id, address_detail='Pay Address')
            db.add(addr)
            db.flush()

            order = Order(
                order_number='DDTESTPAY',
                user_id=user.id,
                shop_id=shop.id,
                address_id=addr.id,
                total_amount=29.99,
                status='PENDING_PAYMENT',
            )
            db.add(order)
            db.flush()

            payment = Payment(
                order_id=order.id,
                method='alipay',
                amount=29.99,
                status='success',
                transaction_id='TXN123456',
            )
            db.add(payment)
            db.commit()

            assert payment.id is not None
            assert payment.order_id == order.id
            assert payment.method == 'alipay'
            assert payment.amount == 29.99
            assert payment.status == 'success'
            assert payment.transaction_id == 'TXN123456'
            # Verify one-to-one relationship from order
            assert order.payment is not None
            assert order.payment.transaction_id == 'TXN123456'


class TestReviewModel:
    """Tests for the Review model."""

    def test_review_creation(self, app, db):
        """Create a Review with unique constraint on (order_id, target_type, target_id)."""
        with app.app_context():
            user = User(username='revuser', email='rev@test.com')
            user.set_password('pass')
            db.add(user)
            db.flush()

            merchant = User(username='revmerch', email='revm@test.com', role='merchant')
            merchant.set_password('pass')
            db.add(merchant)
            db.flush()

            shop = Shop(merchant_id=merchant.id, name='Review Shop')
            db.add(shop)
            db.flush()

            addr = Address(user_id=user.id, address_detail='Review Address')
            db.add(addr)
            db.flush()

            order = Order(
                order_number='DDTESTREV',
                user_id=user.id,
                shop_id=shop.id,
                address_id=addr.id,
                total_amount=10.0,
                status='COMPLETED',
            )
            db.add(order)
            db.flush()

            review = Review(
                order_id=order.id,
                user_id=user.id,
                target_type='merchant',
                target_id=shop.id,
                rating=5,
                comment='Great food!',
            )
            db.add(review)
            db.commit()

            assert review.id is not None
            assert review.order_id == order.id
            assert review.target_type == 'merchant'
            assert review.target_id == shop.id
            assert review.rating == 5
            assert review.comment == 'Great food!'

            # Duplicate (order_id, target_type, target_id) should raise IntegrityError
            duplicate = Review(
                order_id=order.id,
                user_id=user.id,
                target_type='merchant',
                target_id=shop.id,
                rating=3,
                comment='Duplicate',
            )
            db.add(duplicate)
            with pytest.raises(IntegrityError):
                db.commit()


class TestRefundModel:
    """Tests for the Refund model."""

    def test_refund_creation(self, app, db):
        """Create a Refund linked to an order."""
        with app.app_context():
            user = User(username='refuser', email='ref@test.com')
            user.set_password('pass')
            db.add(user)
            db.flush()

            merchant = User(username='refmerch', email='refm@test.com', role='merchant')
            merchant.set_password('pass')
            db.add(merchant)
            db.flush()

            shop = Shop(merchant_id=merchant.id, name='Refund Shop')
            db.add(shop)
            db.flush()

            addr = Address(user_id=user.id, address_detail='Refund Address')
            db.add(addr)
            db.flush()

            order = Order(
                order_number='DDTESTREF',
                user_id=user.id,
                shop_id=shop.id,
                address_id=addr.id,
                total_amount=25.0,
                status='REFUND_REQUESTED',
            )
            db.add(order)
            db.flush()

            refund = Refund(
                order_id=order.id,
                user_id=user.id,
                reason='Item not as described',
                amount=25.0,
                status='pending',
            )
            db.add(refund)
            db.commit()

            assert refund.id is not None
            assert refund.order_id == order.id
            assert refund.user_id == user.id
            assert refund.reason == 'Item not as described'
            assert refund.amount == 25.0
            assert refund.status == 'pending'
            # Verify relationship from order
            assert order.refund is not None
            assert order.refund.reason == 'Item not as described'


class TestCascadeDelete:
    """Tests for cascade delete behavior."""

    def test_cascade_delete_shop(self, app, db):
        """Deleting a Shop cascades to its MenuItems."""
        with app.app_context():
            merchant = User(
                username='cascadem',
                email='cascade@test.com',
                role='merchant',
            )
            merchant.set_password('pass')
            db.add(merchant)
            db.flush()

            shop = Shop(merchant_id=merchant.id, name='Cascade Shop')
            db.add(shop)
            db.flush()

            items = [
                MenuItem(shop_id=shop.id, name='Item 1', price=10.0, stock=5),
                MenuItem(shop_id=shop.id, name='Item 2', price=15.0, stock=3),
            ]
            db.add_all(items)
            db.commit()

            item_ids = [item.id for item in items]
            # Verify items exist before delete
            assert MenuItem.query.get(item_ids[0]) is not None
            assert MenuItem.query.get(item_ids[1]) is not None

            # Delete the shop
            db.delete(shop)
            db.commit()

            # MenuItems should be cascade-deleted
            assert MenuItem.query.get(item_ids[0]) is None
            assert MenuItem.query.get(item_ids[1]) is None
