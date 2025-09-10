from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, CoachAthlete, TrainingPlan

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/all_plans", methods=["GET"])
@jwt_required()
def all_plans():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    plans = (
        db.session.query(TrainingPlan)
        .join(CoachAthlete, CoachAthlete.athlete_id == TrainingPlan.athlete_id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .order_by(TrainingPlan.start_date.desc())
        .all()
    )
    return render_template("coach/all_plans.html", plans=plans)