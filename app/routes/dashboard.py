from flask import Blueprint,render_template, abort
from flask_jwt_extended import jwt_required,get_jwt
from app.models import TrainingPlan, Feedback, User
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@jwt_required()
def dashboard():
    claims = get_jwt()
    role = claims.get("role")

    if role == 'admin':
        stats = {
            "coaches": User.query.filter_by(role="coach").count(),
            "athletes": User.query.filter_by(role="athlete").count(),
            "plans": TrainingPlan.query.filter_by(status="active").count(),
            "feedbacks": Feedback.query.count()
        }

        activities = [
            {"user": "Coach John", "action": "added new plan for Athlete Ali", "time": "2h ago"},
            {"user": "Athlete Sara", "action": "completed workout", "time": "5h ago"},
        ]

        chart = {
            "athlete_labels": ["Jan", "Feb", "Mar", "Apr"],
            "athlete_data": [5, 10, 15, 20],
            "plan_data": [70, 30]  # 70% compliant
        }

        return render_template("dashboard/admin_dashboard.html", stats=stats, activities=activities, chart=chart)
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
        
