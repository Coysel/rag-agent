"""Test review system."""
from app.extensions import db
from app.models.review import Review, ReviewReply


def login(client, username, password):
    """Helper to log in a user."""
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def logout(client):
    """Helper to log out."""
    return client.get('/auth/logout', follow_redirects=True)


class TestReview:
    """Tests for the review system."""

    def test_create_review(self, client, db, sample_users, sample_order,
                           sample_shop):
        """POST /user/reviews/create with valid data creates a review."""
        login(client, 'user1', '123456')

        resp = client.post('/user/reviews/create', data={
            'order_id': sample_order.id,
            'target_type': 'merchant',
            'target_id': sample_shop.id,
            'rating': 5,
            'comment': 'Great shop!',
        }, follow_redirects=True)
        assert resp.status_code == 200

        review = Review.query.filter_by(order_id=sample_order.id).first()
        assert review is not None, 'Review not created'
        assert review.rating == 5
        assert review.comment == 'Great shop!'
        assert review.target_type == 'merchant'
        assert review.target_id == sample_shop.id
        assert review.user_id == sample_users['user'].id

    def test_review_invalid_rating(self, client, db, sample_users,
                                   sample_order, sample_shop):
        """Rating 0 and rating 6 should be rejected."""
        login(client, 'user1', '123456')

        resp = client.post('/user/reviews/create', data={
            'order_id': sample_order.id,
            'target_type': 'merchant',
            'target_id': sample_shop.id,
            'rating': 0,
            'comment': 'Invalid low rating',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert Review.query.filter_by(order_id=sample_order.id).first() is None

        resp = client.post('/user/reviews/create', data={
            'order_id': sample_order.id,
            'target_type': 'merchant',
            'target_id': sample_shop.id,
            'rating': 6,
            'comment': 'Invalid high rating',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert Review.query.filter_by(order_id=sample_order.id).first() is None

    def test_duplicate_review(self, client, db, sample_users, sample_order,
                              sample_shop):
        """Creating a review for the same order+target twice should fail."""
        login(client, 'user1', '123456')

        client.post('/user/reviews/create', data={
            'order_id': sample_order.id,
            'target_type': 'merchant',
            'target_id': sample_shop.id,
            'rating': 4,
            'comment': 'Good',
        }, follow_redirects=True)
        assert Review.query.count() == 1

        resp = client.post('/user/reviews/create', data={
            'order_id': sample_order.id,
            'target_type': 'merchant',
            'target_id': sample_shop.id,
            'rating': 3,
            'comment': 'Duplicate',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert Review.query.count() == 1, 'Duplicate should not be created'

    def test_review_shop_rating_update(self, client, db, sample_users,
                                       sample_order, sample_shop):
        """After creating a merchant review, the shop rating is recalculated."""
        login(client, 'user1', '123456')

        client.post('/user/reviews/create', data={
            'order_id': sample_order.id,
            'target_type': 'merchant',
            'target_id': sample_shop.id,
            'rating': 5,
            'comment': 'Excellent!',
        }, follow_redirects=True)

        db.refresh(sample_shop)
        assert sample_shop.rating == 5.0, \
            f'Expected shop rating 5.0, got {sample_shop.rating}'

    def test_view_reviews_on_shop(self, client, db, sample_users,
                                  sample_order, sample_shop):
        """Reviews created show up on the shop detail page."""
        login(client, 'user1', '123456')

        client.post('/user/reviews/create', data={
            'order_id': sample_order.id,
            'target_type': 'merchant',
            'target_id': sample_shop.id,
            'rating': 4,
            'comment': 'Nice shop!',
        }, follow_redirects=True)

        resp = client.get(f'/shop/{sample_shop.id}')
        assert resp.status_code == 200
        assert 'Nice shop!'.encode('utf-8') in resp.data

    def test_merchant_reply(self, client, db, sample_users, sample_order,
                            sample_shop):
        """Merchant can reply to a review."""
        login(client, 'user1', '123456')

        client.post('/user/reviews/create', data={
            'order_id': sample_order.id,
            'target_type': 'merchant',
            'target_id': sample_shop.id,
            'rating': 4,
            'comment': 'Good food',
        }, follow_redirects=True)

        review = Review.query.filter_by(order_id=sample_order.id).first()
        assert review is not None

        logout(client)
        login(client, 'merchant1', '123456')

        resp = client.post(f'/merchant/reviews/{review.id}/reply', data={
            'review_id': review.id,
            'content': 'Thank you!',
        }, follow_redirects=True)
        assert resp.status_code == 200

        reply = ReviewReply.query.filter_by(review_id=review.id).first()
        assert reply is not None, 'Reply was not created'
        assert reply.content == 'Thank you!'
        assert reply.merchant_id == sample_users['merchant'].id
