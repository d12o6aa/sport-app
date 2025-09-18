from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, TrainingPlan, WorkoutSession

from . import athlete_bp

def is_athlete(user_id):
    user = User.query.get(user_id)
    return user and user.role == "athlete"

@athlete_bp.route("/view_plans", methods=["GET"])
@jwt_required()
def view_plans():
    identity = get_jwt_identity()
    if not is_athlete(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    plans = TrainingPlan.query.filter_by(athlete_id=identity).order_by(TrainingPlan.start_date.desc()).all()
    sessions = WorkoutSession.query.filter_by(athlete_id=identity).all()
    return render_template("athlete/view_plans.html", plans=plans, sessions=sessions)