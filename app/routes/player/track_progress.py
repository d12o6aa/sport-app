from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import User, WorkoutLog, HealthRecord, AthleteGoal, ReadinessScore
from sqlalchemy import func

from . import athlete_bp

def is_athlete(user_id):
    user = User.query.get(user_id)
    return user and user.role == "athlete"

@athlete_bp.route("/track_progress", methods=["GET"])
@jwt_required()
def track_progress():
    user_id = get_jwt_identity()
    readiness_scores = ReadinessScore.query.filter_by(athlete_id=user_id).order_by(ReadinessScore.date.desc()).limit(10).all()
    readiness = readiness_scores[0] if readiness_scores else None
    return render_template("athlete/track_progress.html", readiness=readiness, readiness_scores=[r.to_dict() for r in readiness_scores])

@athlete_bp.route("/progress_data", methods=["GET"])
@jwt_required()
def progress_data():
    identity = get_jwt_identity()
    if not is_athlete(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    range_param = request.args.get("range", "month")
    end_date = datetime.utcnow()
    if range_param == "week":
        start_date = end_date - timedelta(days=7)
    elif range_param == "3months":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=30)

    # Total Sessions and Compliance
    total_sessions = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == identity,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date
    ).count()
    completed_logs = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == identity,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date,
        WorkoutLog.compliance_status == "completed"
    ).count()
    compliance = round((completed_logs / total_sessions * 100) if total_sessions > 0 else 0, 1)

    # Latest Readiness Score
    latest_readiness = ReadinessScore.query.filter_by(athlete_id=identity).order_by(ReadinessScore.date.desc()).first()
    readiness = {
        "score": latest_readiness.score if latest_readiness else 0,
        "injury_risk": latest_readiness.injury_risk if latest_readiness else "low",
        "recovery_prediction": latest_readiness.recovery_prediction if latest_readiness else "N/A"
    } if latest_readiness else {
        "score": 0,
        "injury_risk": "low",
        "recovery_prediction": "N/A"
    }

    # Heart Best (New)
    latest_heart_rate = HealthRecord.query.filter(
        HealthRecord.athlete_id == identity,
        HealthRecord.heart_rate.isnot(None)
    ).order_by(HealthRecord.recorded_at.desc()).first()
    heart_rate_data = {
        "value": latest_heart_rate.heart_rate if latest_heart_rate else 0,
        "status": "Normal" if (latest_heart_rate and 60 <= latest_heart_rate.heart_rate <= 100) else "Abnormal"
    }

    # Weight Data
    weight_data = HealthRecord.query.filter(
        HealthRecord.athlete_id == identity,
        HealthRecord.recorded_at >= start_date,
        HealthRecord.recorded_at <= end_date,
        HealthRecord.weight.isnot(None)
    ).order_by(HealthRecord.recorded_at).all()
    weight_labels = [data_point.recorded_at.strftime("%Y-%m-%d") for data_point in weight_data]
    weight_values = [data_point.weight for data_point in weight_data]

    # Workout Activity
    workout_activity = db.session.query(
        func.date(WorkoutLog.logged_at).label("day"),
        func.count(WorkoutLog.id)
    ).filter(
        WorkoutLog.athlete_id == identity,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date
    ).group_by("day").all()
    activity_labels = [wa.day.strftime("%a") for wa in workout_activity]
    activity_values = [wa[1] for wa in workout_activity]

    # Calories Data
    calories_data_daily = db.session.query(
        func.date(HealthRecord.recorded_at).label("day"),
        func.sum(HealthRecord.calories_intake).label("intake"),
        func.sum(HealthRecord.calories_burned).label("burned")
    ).filter(
        HealthRecord.athlete_id == identity,
        HealthRecord.recorded_at >= start_date,
        HealthRecord.recorded_at <= end_date
    ).group_by("day").order_by("day").all()
    calories_labels = [cd.day.strftime("%a") for cd in calories_data_daily]
    calories_intake_values = [cd.intake if cd.intake is not None else 0 for cd in calories_data_daily]
    calories_burned_values = [cd.burned if cd.burned is not None else 0 for cd in calories_data_daily]
    avg_calories_intake = sum(calories_intake_values) / len(calories_intake_values) if calories_intake_values else 0
    
    # Macros
    avg_macros = db.session.query(
        func.avg(HealthRecord.protein).label("protein"),
        func.avg(HealthRecord.carbs).label("carbs"),
        func.avg(HealthRecord.fats).label("fats")
    ).filter(
        HealthRecord.athlete_id == identity,
        HealthRecord.recorded_at >= start_date,
        HealthRecord.recorded_at <= end_date
    ).first()
    macros = {
        "protein": round(avg_macros.protein, 1) if avg_macros and avg_macros.protein is not None else 0,
        "carbs": round(avg_macros.carbs, 1) if avg_macros and avg_macros.carbs is not None else 0,
        "fats": round(avg_macros.fats, 1) if avg_macros and avg_macros.fats is not None else 0
    }

    # Average Steps
    avg_steps_query = db.session.query(func.avg(HealthRecord.steps)).filter(
        HealthRecord.athlete_id == identity,
        HealthRecord.recorded_at >= start_date,
        HealthRecord.recorded_at <= end_date
    ).scalar() or 0
    avg_steps = avg_steps_query

    # Goals
    goals = AthleteGoal.query.filter_by(athlete_id=identity).all()
    goals_list = [
        {
            "description": goal.title,
            "target_value": goal.target_value,
            "current_value": goal.current_value,
            "progress": goal.progress,
            "status": goal.status
        } for goal in goals
    ]

    # Athlete Progress Summary
    progress_summary = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == identity,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date
    ).order_by(WorkoutLog.logged_at).all()
    progress_labels = [p.logged_at.strftime("%Y-%m-%d") for p in progress_summary]
    progress_values = [p.calories_burned if p.calories_burned is not None else 0 for p in progress_summary]

    return jsonify({
        "readiness": readiness,
        "heart_rate": heart_rate_data,
        "total_sessions": total_sessions,
        "compliance": compliance,
        "weight_labels": weight_labels,
        "weight_values": weight_values,
        "activity_labels": activity_labels,
        "activity_values": activity_values,
        "calories_labels": calories_labels,
        "calories_intake_values": calories_intake_values,
        "calories_burned_values": calories_burned_values,
        "avg_calories_intake": avg_calories_intake,
        "macros": macros,
        "avg_steps": avg_steps,
        "goals_list": goals_list,
        "progress_labels": progress_labels,
        "progress_values": progress_values
    })