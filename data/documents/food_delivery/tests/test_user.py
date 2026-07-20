"""Test user blueprint (cart, orders, addresses)."""
from tests.conftest import login
from app.models.cart_item import CartItem
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.address import Address
from app.extensions import db as _db


def test_view_empty_cart(client, sample_users):
    """GET /user/cart returns 200 with empty cart message."""
    login(client, 'user1', '123456')
    resp = client.get('/user/cart', follow_redirects=True)
    assert resp.status_code == 200


def test_add_to_cart(client, db, sample_users, sample_shop):
    """POST /user/cart/add with menu_item_id and quantity adds to cart."""
    login(client, 'user1', '123456')
    menu_item = sample_shop.menu_items.first()
    resp = client.post('/user/cart/add', data={
        'menu_item_id': menu_item.id,
        'quantity': 2,
    }, follow_redirects=True)
    assert resp.status_code == 200
    cart_item = CartItem.query.filter_by(
        user_id=sample_users['user'].id,
        menu_item_id=menu_item.id,
    ).first()
    assert cart_item is not None
    assert cart_item.quantity == 2


def test_add_to_cart_json(client, db, sample_users, sample_shop):
    """POST /user/cart/add with Accept: application/json returns JSON."""
    login(client, 'user1', '123456')
    menu_item = sample_shop.menu_items.first()
    resp = client.post('/user/cart/add', data={
        'menu_item_id': menu_item.id,
        'quantity': 1,
    }, headers={'Accept': 'application/json'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert '已加入购物车' in data['message']


def test_update_cart_quantity(client, db, sample_users, sample_shop):
    """POST /user/cart/update/<id> with quantity=3 updates the cart item."""
    login(client, 'user1', '123456')
    # First add an item
    menu_item = sample_shop.menu_items.first()
    client.post('/user/cart/add', data={
        'menu_item_id': menu_item.id,
        'quantity': 1,
    })
    cart_item = CartItem.query.filter_by(
        user_id=sample_users['user'].id,
        menu_item_id=menu_item.id,
    ).first()
    assert cart_item is not None

    # Update quantity
    resp = client.post(f'/user/cart/update/{cart_item.id}', data={
        'quantity': 3,
    }, follow_redirects=True)
    assert resp.status_code == 200
    updated = CartItem.query.get(cart_item.id)
    assert updated.quantity == 3


def test_remove_from_cart(client, db, sample_users, sample_shop):
    """POST /user/cart/remove/<id> removes the cart item."""
    login(client, 'user1', '123456')
    # First add an item
    menu_item = sample_shop.menu_items.first()
    client.post('/user/cart/add', data={
        'menu_item_id': menu_item.id,
        'quantity': 1,
    })
    cart_item = CartItem.query.filter_by(
        user_id=sample_users['user'].id,
        menu_item_id=menu_item.id,
    ).first()
    assert cart_item is not None

    # Remove it
    resp = client.post(f'/user/cart/remove/{cart_item.id}', follow_redirects=True)
    assert resp.status_code == 200
    removed = CartItem.query.get(cart_item.id)
    assert removed is None


def test_cart_access_denied_for_merchant(client, sample_users):
    """Login as merchant, GET /user/cart returns 403."""
    login(client, 'merchant1', '123456')
    resp = client.get('/user/cart')
    assert resp.status_code == 403


def test_checkout_page(client, db, sample_users, sample_shop, sample_address):
    """Add item to cart, GET /user/checkout returns 200."""
    login(client, 'user1', '123456')
    menu_item = sample_shop.menu_items.first()
    client.post('/user/cart/add', data={
        'menu_item_id': menu_item.id,
        'quantity': 2,
    })
    resp = client.get('/user/checkout', follow_redirects=True)
    assert resp.status_code == 200


def test_checkout_empty_cart(client, sample_users):
    """GET /user/checkout with empty cart redirects."""
    login(client, 'user1', '123456')
    resp = client.get('/user/checkout', follow_redirects=True)
    assert resp.status_code == 200


def test_submit_order(client, db, sample_users, sample_shop, sample_address):
    """POST /user/checkout with valid address creates a PENDING_PAYMENT order."""
    login(client, 'user1', '123456')
    menu_item = sample_shop.menu_items.filter(MenuItem.stock > 0).first()
    # Add to cart
    client.post('/user/cart/add', data={
        'menu_item_id': menu_item.id,
        'quantity': 2,
    })
    # Submit checkout
    resp = client.post('/user/checkout', data={
        'address_id': sample_address.id,
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Verify order created
    order = Order.query.filter_by(user_id=sample_users['user'].id).first()
    assert order is not None
    assert order.status == 'PENDING_PAYMENT'
    assert order.address_id == sample_address.id


def test_view_orders(client, db, sample_users, sample_order):
    """GET /user/orders returns 200."""
    login(client, 'user1', '123456')
    resp = client.get('/user/orders', follow_redirects=True)
    assert resp.status_code == 200


def test_view_order_detail(client, db, sample_users, sample_order):
    """GET /user/orders/<id> returns 200."""
    login(client, 'user1', '123456')
    resp = client.get(f'/user/orders/{sample_order.id}', follow_redirects=True)
    assert resp.status_code == 200


def test_cancel_order(client, db, sample_users, sample_shop, sample_address):
    """POST /user/orders/<id>/cancel on PENDING_PAYMENT order cancels it."""
    login(client, 'user1', '123456')
    # Create a PENDING_PAYMENT order via checkout
    menu_item = sample_shop.menu_items.filter(MenuItem.stock > 0).first()
    client.post('/user/cart/add', data={
        'menu_item_id': menu_item.id,
        'quantity': 1,
    })
    client.post('/user/checkout', data={
        'address_id': sample_address.id,
    })
    order = Order.query.filter_by(
        user_id=sample_users['user'].id, status='PENDING_PAYMENT'
    ).first()
    assert order is not None

    # Cancel the order
    resp = client.post(f'/user/orders/{order.id}/cancel', follow_redirects=True)
    assert resp.status_code == 200
    cancelled = Order.query.get(order.id)
    assert cancelled.status == 'CANCELLED'


def test_confirm_receipt(client, db, sample_users, sample_order):
    """POST /user/orders/<id>/confirm on DELIVERED order sets status to COMPLETED."""
    login(client, 'user1', '123456')
    # Set order to DELIVERED
    sample_order.status = 'DELIVERED'
    db.commit()

    resp = client.post(f'/user/orders/{sample_order.id}/confirm', follow_redirects=True)
    assert resp.status_code == 200
    completed = Order.query.get(sample_order.id)
    assert completed.status == 'COMPLETED'


def test_add_address(client, db, sample_users):
    """POST /user/addresses/add with label and address_detail adds an address."""
    login(client, 'user1', '123456')
    resp = client.post('/user/addresses/add', data={
        'label': 'Work',
        'address_detail': '456 Office Road',
    }, follow_redirects=True)
    assert resp.status_code == 200
    addr = Address.query.filter_by(
        user_id=sample_users['user'].id, label='Work'
    ).first()
    assert addr is not None
    assert addr.address_detail == '456 Office Road'


def test_set_default_address(client, db, sample_users, sample_address):
    """POST /user/addresses/default/<id> sets the default address."""
    login(client, 'user1', '123456')
    # Create a second address first
    addr2 = Address(
        user_id=sample_users['user'].id,
        label='Office',
        address_detail='456 Office Road',
        is_default=False,
    )
    db.add(addr2)
    db.commit()

    # Set the new address as default
    resp = client.post(f'/user/addresses/default/{addr2.id}', follow_redirects=True)
    assert resp.status_code == 200
    # Check old default is no longer default
    old = Address.query.get(sample_address.id)
    assert old.is_default is False
    # Check new address is default
    new = Address.query.get(addr2.id)
    assert new.is_default is True


def test_delete_address(client, db, sample_users, sample_address):
    """POST /user/addresses/delete/<id> removes the address."""
    login(client, 'user1', '123456')
    # Create an extra address to delete
    addr = Address(
        user_id=sample_users['user'].id,
        label='Temp',
        address_detail='789 Temp Lane',
    )
    db.add(addr)
    db.commit()
    addr_id = addr.id

    resp = client.post(f'/user/addresses/delete/{addr_id}', follow_redirects=True)
    assert resp.status_code == 200
    deleted = Address.query.get(addr_id)
    assert deleted is None


def test_view_reviews(client, db, sample_users, sample_order):
    """GET /user/reviews returns 200."""
    login(client, 'user1', '123456')
    resp = client.get('/user/reviews', follow_redirects=True)
    assert resp.status_code == 200


def test_view_refunds(client, db, sample_users, sample_order):
    """GET /user/refunds returns 200."""
    login(client, 'user1', '123456')
    resp = client.get('/user/refunds', follow_redirects=True)
    assert resp.status_code == 200


def test_view_payments(client, db, sample_users, sample_order):
    """GET /user/payments returns 200."""
    login(client, 'user1', '123456')
    resp = client.get('/user/payments', follow_redirects=True)
    assert resp.status_code == 200
