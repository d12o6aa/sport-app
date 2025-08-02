from flask import Blueprint,render_template, abort
from flask_jwt_extended import jwt_required,get_jwt

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@jwt_required()
def dashboard():
    claims = get_jwt()
    role = claims.get("role")

    if role == 'admin':
        return render_template('dashboard/admin_dashboard.html')
    elif role == 'coach':
        return render_template('dashboard/coach_dashboard.html')
    elif role == 'athlete':
        return render_template('dashboard/athlete_dashboard.html')
    else:
        abort(403)