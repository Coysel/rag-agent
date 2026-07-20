"""Test merchant blueprint."""
from tests.conftest import login
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.review import Review, ReviewReply
from app.extensions import db as _db


def test_dashboard_access(client, db, sample_users, sample_shop):
    """GET /merchant/dashboard returns 200."""
    login(client, 'merchant1', '123456')
    resp = client.get('/merchant/dashboard', follow_redirects=True)
    assert resp.status_code == 200


def test_shop_page(client, db, sample_users, sample_shop):
    """GET /merchant/shop returns 200 (shop exists from sample_shop fixture)."""
    login(client, 'merchant1', '123456')
    resp = client.get('/merchant/shop', follow_redirects=True)
    assert resp.status_code == 200


def test_update_shop(client, db, sample_users, sample_shop):
    """POST /merchant/shop with updated data updates the shop."""
    login(client, 'merchant1', '123456')
    resp = client.post('/merchant/shop', data={
        'name': 'Updated Shop',
        'description': 'Updated description',
        'address': '456 New Street',
        'phone': '010-87654321',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert sample_shop.name == 'Updated Shop'
    assert sample_shop.address == '456 New Street'


def test_menu_page(client, db, sample_users, sample_shop):
    """GET /merchant/menu returns 200."""
    login(client, 'merchant1', '123456')
    resp = client.get('/merchant/menu', follow_redirects=True)
    assert resp.status_code == 200


def test_add_menu_item(client, db, sample_users, sample_shop):
    """POST /merchant/menu/add with valid data adds a menu item."""
    login(client, 'merchant1', '123456')
    resp = client.post('/merchant/menu/add', data={
        'name': 'New Dish',
        'description': 'A delicious new dish',
        'price': 25.0,
        'stock': 100,
        'category': '热菜',
        'is_available': '1',
    }, follow_redirects=True)
    assert resp.status_code == 200
    item = MenuItem.query.filter_by(shop_id=sample_shop.id, name='New Dish').first()
    assert item is not None
    assert item.price == 25.0
    assert item.is_available is True


def test_edit_menu_item(client, db, sample_users, sample_shop):
    """POST /merchant/menu/edit/<id> with updated data modifies the item."""
    login(client, 'merchant1', '123456')
    item = sample_shop.menu_items.first()
    resp = client.post(f'/merchant/menu/edit/{item.id}', data={
        'name': 'Edited Item',
        'description': 'Edited description',
        'price': 30.0,
        'stock': 20,
        'category': '主食',
        'is_available': '1',
    }, follow_redirects=True)
    assert resp.status_code == 200
    updated = MenuItem.query.get(item.id)
    assert updated.name == 'Edited Item'
    assert updated.price == 30.0


def test_toggle_menu_item(client, db, sample_users, sample_shop):
    """POST /merchant/menu/toggle/<id> toggles is_available."""
    login(client, 'merchant1', '123456')
    item = sample_shop.menu_items.first()
    original_available = item.is_available

    resp = client.post(f'/merchant/menu/toggle/{item.id}', follow_redirects=True)
    assert resp.status_code == 200
    toggled = MenuItem.query.get(item.id)
    assert toggled.is_available == (not original_available)

    # Toggle back
    client.post(f'/merchant/menu/toggle/{item.id}')
    restored = MenuItem.query.get(item.id)
    assert restored.is_available == original_available


def test_delete_menu_item(client, db, sample_users, sample_shop):
    """POST /merchant/menu/delete/<id> removes the item."""
    login(client, 'merchant1', '123456')
    item = sample_shop.menu_items.first()
    item_id = item.id

    resp = client.post(f'/merchant/menu/delete/{item_id}', follow_redirects=True)
    assert resp.status_code == 200
    deleted = MenuItem.query.get(item_id)
    assert deleted is None


def test_order_list(client, db, sample_users, sample_shop, sample_order):
    """GET /merchant/orders returns 200."""
    login(client, 'merchant1', '123456')
    resp = client.get('/merchant/orders', follow_redirects=True)
    assert resp.status_code == 200


def test_order_detail(client, db, sample_users, sample_shop, sample_order):
    """GET /merchant/orders/<id> returns 200."""
    login(client, 'merchant1', '123456')
    resp = client.get(f'/merchant/orders/{sample_order.id}', follow_redirects=True)
    assert resp.status_code == 200


def test_accept_order(client, db, sample_users, sample_shop, sample_order):
    """POST /merchant/orders/<id>/accept on a PAID order sets status to ACCEPTED."""
    login(client, 'merchant1', '123456')
    assert sample_order.status == 'PAID'

    resp = client.post(f'/merchant/orders/{sample_order.id}/accept', follow_redirects=True)
    assert resp.status_code == 200
    accepted = Order.query.get(sample_order.id)
    assert accepted.status == 'ACCEPTED'


def test_start_preparing(client, db, sample_users, sample_shop, sample_order):
    """POST /merchant/orders/<id>/preparing sets status to PREPARING."""
    login(client, 'merchant1', '123456')
    # Set order to ACCEPTED first
    sample_order.status = 'ACCEPTED'
    db.commit()

    resp = client.post(f'/merchant/orders/{sample_order.id}/preparing', follow_redirects=True)
    assert resp.status_code == 200
    preparing = Order.query.get(sample_order.id)
    assert preparing.status == 'PREPARING'


def test_mark_ready(client, db, sample_users, sample_shop, sample_order):
    """POST /merchant/orders/<id>/ready sets status to READY_FOR_PICKUP."""
    login(client, 'merchant1', '123456')
    # Set order to PREPARING first
    sample_order.status = 'PREPARING'
    db.commit()

    resp = client.post(f'/merchant/orders/{sample_order.id}/ready', follow_redirects=True)
    assert resp.status_code == 200
    ready = Order.query.get(sample_order.id)
    assert ready.status == 'READY_FOR_PICKUP'


def test_reject_order(client, db, sample_users, sample_shop, sample_order):
    """POST /merchant/orders/<id>/reject on a PAID order sets status to CANCELLED."""
    login(client, 'merchant1', '123456')
    assert sample_order.status == 'PAID'

    resp = client.post(f'/merchant/orders/{sample_order.id}/reject', follow_redirects=True)
    assert resp.status_code == 200
    rejected = Order.query.get(sample_order.id)
    assert rejected.status == 'CANCELLED'


def test_revenue_page(client, db, sample_users, sample_shop, sample_order):
    """GET /merchant/revenue returns 200."""
    login(client, 'merchant1', '123456')
    resp = client.get('/merchant/revenue', follow_redirects=True)
    assert resp.status_code == 200


def test_refunds_page(client, db, sample_users, sample_shop, sample_order):
    """GET /merchant/refunds returns 200."""
    login(client, 'merchant1', '123456')
    resp = client.get('/merchant/refunds', follow_redirects=True)
    assert resp.status_code == 200


def test_reviews_page(client, db, sample_users, sample_shop):
    """GET /merchant/reviews returns 200."""
    login(client, 'merchant1', '123456')
    resp = client.get('/merchant/reviews', follow_redirects=True)
    assert resp.status_code == 200


def test_review_reply(client, db, sample_users, sample_shop, sample_order):
    """POST /merchant/reviews/<id>/reply with content adds a reply."""
    login(client, 'merchant1', '123456')
    # Create a review to reply to
    review = Review(
        order_id=sample_order.id,
        user_id=sample_users['user'].id,
        target_type='merchant',
        target_id=sample_shop.id,
        rating=5,
        comment='Excellent!',
    )
    db.add(review)
    db.commit()

    resp = client.post(f'/merchant/reviews/{review.id}/reply', data={
        'review_id': review.id,
        'content': 'Thank you for your kind review!',
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Verify reply was created
    reply = ReviewReply.query.filter_by(review_id=review.id).first()
    assert reply is not None
    assert reply.content == 'Thank you for your kind review!'
    assert reply.merchant_id == sample_users['merchant'].id


def test_merchant_access_denied_for_user(client, sample_users):
    """Login as user, GET /merchant/dashboard returns 403."""
    login(client, 'user1', '123456')
    resp = client.get('/merchant/dashboard')
    assert resp.status_code == 403
