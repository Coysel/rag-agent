from flask import Blueprint

merchant_bp = Blueprint('merchant', __name__, template_folder='../../templates/merchant')

from app.blueprints.merchant import views_shop     # noqa
from app.blueprints.merchant import views_orders   # noqa
from app.blueprints.merchant import views_revenue  # noqa
