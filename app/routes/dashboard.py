from flask import Blueprint,render_template, abort, redirect, url_for
from flask_jwt_extended import jwt_required,get_jwt
from app.models import TrainingPlan, Feedback, User
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@jwt_required()
def dashboard():
    claims = get_jwt()
    role = claims.get("role")

    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'coach':
        return render_template('dashboard/coach_dashboard.html')
    elif role == 'athlete':
        return render_template('dashboard/athlete_dashboard.html')
    else:
        abort(403)
        


##### sidebar #####
@dashboard_bp.route("/sidebar")
@jwt_required()
def sidebar():
    claims = get_jwt()
    role = claims.get("role")
    

    if role == 'admin':
        return render_template('shared/admin_sidebar.html')
    elif role == 'coach':
        return render_template('shared/coach_sidebar.html')
    elif role == 'athlete':
        return render_template('shared/athlete_sidebar.html')
    else:
        abort(403)


##### navbar #####
@dashboard_bp.route("/navbar")
@jwt_required()
def navbar():
    claims = get_jwt()
    role = claims.get("role")

    if role == 'admin':
        return render_template('shared/admin_navbar.html')
    elif role == 'coach':
        return render_template('shared/coach_navbar.html')
    elif role == 'athlete':
        return render_template('shared/athlete_navbar.html')
    else:
        abort(403)


@dashboard_bp.route("/header")
@jwt_required()
def header():
    claims = get_jwt()
    role = claims.get("role")

    if role == 'admin':
        return render_template('shared/admin_header.html')
    elif role == 'coach':
        return render_template('shared/coach_header.html')
    elif role == 'athlete':
        return render_template('shared/athlete_header.html')
    else:
        abort(403)
        

