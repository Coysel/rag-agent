from flask import Blueprint

rider_bp = Blueprint('rider', __name__, template_folder='../../templates/rider')

from app.blueprints.rider import routes  # noqa
