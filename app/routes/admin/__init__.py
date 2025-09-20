from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

from . import dashboard, support_security, subscription_management, reports,admin,views, gym_management