"""Test fixtures for the food delivery system."""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.shop import Shop
from app.models.menu_item import MenuItem
from app.models.address import Address
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.cart_item import CartItem
from app.models.review import Review, ReviewReply
from app.models.refund import Refund


@pytest.fixture(scope='session')
def app():
    """Create the Flask application with testing config."""
    app = create_app('testing')
    return app


@pytest.fixture
def db(db_session):
    """Alias for db_session."""
    return db_session


@pytest.fixture
def client(app):
    """Test client that does NOT follow redirects by default."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Provide a database session within a transaction.
    All changes are rolled back after each test.
    """
    with app.app_context():
        _db.create_all()
        yield _db.session
        _db.session.rollback()
        _db.drop_all()


# ---- Sample Data Fixtures (all share the same session) ----

@pytest.fixture
def sample_users(app, db_session):
    """Create sample users of each role."""
    admin = User(username='admin', email='admin@test.com', name='Admin',
                 phone='13800000001', role='admin', is_approved=True)
    admin.set_password('admin123')

    merchant = User(username='merchant1', email='merchant1@test.com', name='Merchant',
                    phone='13800000002', role='merchant', is_approved=True)
    merchant.set_password('123456')

    rider = User(username='rider1', email='rider1@test.com', name='Rider',
                 phone='13800000003', role='rider', is_approved=True)
    rider.set_password('123456')

    user = User(username='user1', email='user1@test.com', name='User',
                phone='13800000004', role='user', is_approved=True)
    user.set_password('123456')

    db_session.add_all([admin, merchant, rider, user])
    db_session.commit()
    return {'admin': admin, 'merchant': merchant, 'rider': rider, 'user': user}


@pytest.fixture
def sample_shop(app, db_session, sample_users):
    """Create a sample shop with menu items."""
    shop = Shop(
        merchant_id=sample_users['merchant'].id,
        name='Test Shop',
        description='A test restaurant',
        address='123 Test Street',
        phone='010-12345678',
        status='approved',
        rating=4.5,
    )
    db_session.add(shop)
    db_session.flush()

    items = [
        MenuItem(shop_id=shop.id, name='Item A', price=10.0, stock=50, category='热菜'),
        MenuItem(shop_id=shop.id, name='Item B', price=20.0, stock=30, category='主食'),
        MenuItem(shop_id=shop.id, name='Item C', price=15.0, stock=0, category='饮品'),
    ]
    db_session.add_all(items)
    db_session.commit()
    return shop


@pytest.fixture
def sample_address(app, db_session, sample_users):
    """Create a sample address for the test user."""
    addr = Address(
        user_id=sample_users['user'].id,
        label='Home',
        address_detail='Test Address 123',
        is_default=True,
    )
    db_session.add(addr)
    db_session.commit()
    return addr


@pytest.fixture
def sample_order(app, db_session, sample_users, sample_shop, sample_address):
    """Create a sample PAID order with 2 order items."""
    order = Order(
        order_number='DD20260617TEST1',
        user_id=sample_users['user'].id,
        shop_id=sample_shop.id,
        address_id=sample_address.id,
        total_amount=50.0,
        status='PAID',
    )
    db_session.add(order)
    db_session.flush()

    menu_items = MenuItem.query.filter_by(shop_id=sample_shop.id).all()
    for item in menu_items[:2]:
        oi = OrderItem(
            order_id=order.id,
            menu_item_id=item.id,
            item_name=item.name,
            quantity=2,
            unit_price=item.price,
            subtotal=item.price * 2,
        )
        db_session.add(oi)

    db_session.commit()
    return order


# ---- Auth Helpers ----

def login(client, username, password):
    """Helper to log in a user. Returns the response."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def login_as(client, role, sample_users):
    """Login as a specific role. Uses sample_users fixture data."""
    creds = {
        'admin': ('admin', 'admin123'),
        'merchant': ('merchant1', '123456'),
        'rider': ('rider1', '123456'),
        'user': ('user1', '123456'),
    }
    username, password = creds[role]
    return login(client, username, password)


def logout(client):
    """Helper to log out."""
    return client.get('/auth/logout', follow_redirects=True)
