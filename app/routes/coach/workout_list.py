from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, CoachAthlete, WorkoutSession

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/workout_list", methods=["GET"])
@jwt_required()
def workout_list():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    workouts = (
        db.session.query(WorkoutSession)
        .join(CoachAthlete, CoachAthlete.athlete_id == WorkoutSession.athlete_id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .order_by(WorkoutSession.performed_at.desc())
        .all()
    )
    return render_template("coach/workout_list.html", workouts=workouts)