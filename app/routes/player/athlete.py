from flask import Blueprint, jsonify

from app.models.user import User
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import render_template, abort, jsonify

athlete_bp = Blueprint("athlete", __name__)

@athlete_bp.route('/unassigned_athletes', methods=['GET'])
@jwt_required()
def get_unassigned_athletes():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    if user.role != 'admin':
        return jsonify({"msg": "Only admins can view unassigned athletes"}), 403

    athletes = User.query.filter_by(role='athlete', coach_id=None).all()
    result = [{"id": a.id, "email": a.email} for a in athletes]
    return jsonify(result)

@athlete_bp.route("/profile")
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != "athlete":
        return abort(403)

    return render_template("athlete/profile.html", user=user)

# Dashboard
@athlete_bp.route("/dashboard")
@jwt_required()
def dashboard():
    return render_template("athlete/dashboard.html")

# Training
@athlete_bp.route("/my_plans")
@jwt_required()
def my_plans():
    return render_template("athlete/my_plans.html")

@athlete_bp.route("/my_calendar")
@jwt_required()
def my_calendar():
    return render_template("athlete/my_calendar.html")

# Performance
@athlete_bp.route("/my_stats")
@jwt_required()
def my_stats():
    return render_template("athlete/my_stats.html")

@athlete_bp.route("/workout_history")
@jwt_required()
def workout_history():
    return render_template("athlete/workout_history.html")

# Feedback
@athlete_bp.route("/send_feedback")
@jwt_required()
def send_feedback():
    return render_template("athlete/send_feedback.html")

@athlete_bp.route("/view_coach_feedback")
@jwt_required()
def view_coach_feedback():
    return render_template("athlete/view_coach_feedback.html")
