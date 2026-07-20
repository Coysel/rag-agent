from flask import render_template, request
from app.blueprints.main import main_bp
from app.models.shop import Shop
from app.models.menu_item import MenuItem
from app.models.review import Review
from sqlalchemy import func


@main_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    query = Shop.query.filter_by(status='approved')
    pagination = query.order_by(Shop.rating.desc()).paginate(page=page, per_page=8, error_out=False)
    shops = pagination.items
    return render_template('index.html', shops=shops, pagination=pagination)


@main_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    if q:
        shops = Shop.query.filter(
            Shop.status == 'approved',
            Shop.name.contains(q)
        ).paginate(page=page, per_page=8, error_out=False)
        menu_items = MenuItem.query.filter(
            MenuItem.is_available == True,
            MenuItem.name.contains(q)
        ).all()
    else:
        shops = Shop.query.filter_by(status='approved').order_by(Shop.rating.desc()).paginate(
            page=page, per_page=8, error_out=False)
        menu_items = []
    return render_template('search.html', shops=shops, menu_items=menu_items, query=q, pagination=shops)


@main_bp.route('/shop/<int:shop_id>')
def shop_detail(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    if shop.status != 'approved':
        return render_template('errors/404.html'), 404

    category = request.args.get('category', '')
    if category:
        menu_items = shop.menu_items.filter(
            MenuItem.is_available == True,
            MenuItem.category == category
        ).order_by(MenuItem.category, MenuItem.name).all()
    else:
        menu_items = shop.menu_items.filter_by(is_available=True).order_by(
            MenuItem.category, MenuItem.name).all()

    # Group by category for display
    categories = {}
    for item in menu_items:
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)

    # Get reviews for this shop
    reviews = Review.query.filter_by(target_type='merchant', target_id=shop.id).order_by(
        Review.created_at.desc()).limit(10).all()

    return render_template('shop_detail.html', shop=shop, categories=categories,
                           reviews=reviews)
