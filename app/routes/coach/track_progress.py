from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, WorkoutLog, HealthRecord, AthleteGoal

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/track_progress", methods=["GET"])
@jwt_required()
def track_progress():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("coach/track_progress.html", athletes=athletes)

@coach_bp.route("/progress_data/<int:athlete_id>", methods=["GET"])
@jwt_required()
def progress_data(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    range_param = request.args.get("range", "month")
    progress_type = request.args.get("type", "performance")

    end_date = datetime.utcnow()
    if range_param == "week":
        start_date = end_date - timedelta(days=7)
    elif range_param == "3months":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=30)

    data = {
        "total_sessions": WorkoutLog.query.filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.logged_at >= start_date,
            WorkoutLog.logged_at <= end_date
        ).count(),
        "compliance": 0,
        "labels": [],
        "values": [],
        "goals": []
    }

    total_planned = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date
    ).count()
    completed_logs = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date,
        WorkoutLog.compliance_status == "completed"
    ).count()
    data["compliance"] = round((completed_logs / total_planned * 100) if total_planned > 0 else 0, 1)

    if progress_type == "weight":
        progress_data = HealthRecord.query.filter(
            HealthRecord.athlete_id == athlete_id,
            HealthRecord.recorded_at >= start_date,
            HealthRecord.recorded_at <= end_date,
            HealthRecord.weight.isnot(None)
        ).order_by(HealthRecord.recorded_at).all()
        data["labels"] = [pd.recorded_at.strftime("%Y-%m-%d") for pd in progress_data]
        data["values"] = [pd.weight for pd in progress_data]
    elif progress_type == "nutrition":
        progress_data = HealthRecord.query.filter(
            HealthRecord.athlete_id == athlete_id,
            HealthRecord.recorded_at >= start_date,
            HealthRecord.recorded_at <= end_date,
            HealthRecord.calories_intake.isnot(None)
        ).order_by(HealthRecord.recorded_at).all()
        data["labels"] = [pd.recorded_at.strftime("%Y-%m-%d") for pd in progress_data]
        data["values"] = [pd.calories_intake for pd in progress_data]
    else:
        progress_data = WorkoutLog.query.filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.logged_at >= start_date,
            WorkoutLog.logged_at <= end_date
        ).order_by(WorkoutLog.logged_at).all()
        data["labels"] = [pd.logged_at.strftime("%Y-%m-%d") for pd in progress_data]
        data["values"] = [pd.metrics.get("performance_score", 0) for pd in progress_data]

    goals = AthleteGoal.query.filter_by(athlete_id=athlete_id).all()
    data["goals"] = [
        {
            "description": goal.description,
            "target_value": goal.target_value,
            "current_value": goal.current_value,
            "status": goal.status
        } for goal in goals
    ]

    return jsonify(data)