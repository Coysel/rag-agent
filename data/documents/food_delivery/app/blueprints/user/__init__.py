from flask import Blueprint

user_bp = Blueprint('user', __name__, template_folder='../../templates/user')

from app.blueprints.user import views_cart      # noqa
from app.blueprints.user import views_orders    # noqa
from app.blueprints.user import views_address   # noqa
from app.blueprints.user import views_reviews   # noqa
