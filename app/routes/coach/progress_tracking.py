from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, WorkoutLog, HealthRecord

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/progress_tracking", methods=["GET"])
@jwt_required()
def progress_tracking():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("coach/progress_tracking.html", athletes=athletes)

@coach_bp.route("/progress_tracking_data/<int:athlete_id>", methods=["GET"])
@jwt_required()
def progress_tracking_data(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    data = {
        "sessions": WorkoutLog.query.filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.logged_at >= start_date,
            WorkoutLog.logged_at <= end_date
        ).count(),
        "weight_data": [],
        "calories_data": []
    }

    weight_records = HealthRecord.query.filter(
        HealthRecord.athlete_id == athlete_id,
        HealthRecord.recorded_at >= start_date,
        HealthRecord.recorded_at <= end_date,
        HealthRecord.weight.isnot(None)
    ).order_by(HealthRecord.recorded_at).all()
    data["weight_data"] = [
        {"date": r.recorded_at.strftime("%Y-%m-%d"), "value": r.weight} for r in weight_records
    ]

    calories_records = HealthRecord.query.filter(
        HealthRecord.athlete_id == athlete_id,
        HealthRecord.recorded_at >= start_date,
        HealthRecord.recorded_at <= end_date,
        HealthRecord.calories_intake.isnot(None)
    ).order_by(HealthRecord.recorded_at).all()
    data["calories_data"] = [
        {"date": r.recorded_at.strftime("%Y-%m-%d"), "value": r.calories_intake} for r in calories_records
    ]

    return jsonify(data)