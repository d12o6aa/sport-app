from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, CoachAthlete, TrainingPlan, WorkoutLog, HealthRecord, AthleteGoal

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/athlete_details/<int:athlete_id>", methods=["GET"])
@jwt_required()
def athlete_details(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    athlete = User.query.get_or_404(athlete_id)
    plans = TrainingPlan.query.filter_by(athlete_id=athlete_id).order_by(TrainingPlan.start_date.desc()).limit(5).all()
    logs = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(WorkoutLog.logged_at.desc()).limit(5).all()
    health_records = HealthRecord.query.filter_by(athlete_id=athlete_id).order_by(HealthRecord.recorded_at.desc()).limit(5).all()
    goals = AthleteGoal.query.filter_by(athlete_id=athlete_id).order_by(AthleteGoal.created_at.desc()).limit(5).all()

    return render_template("coach/athlete_details.html", athlete=athlete, plans=plans, logs=logs, health_records=health_records, goals=goals)