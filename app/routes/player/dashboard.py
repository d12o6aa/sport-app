# app/routes/player/dashboard.py
from flask import jsonify, request
import requests

from datetime import date
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, WorkoutLog, HealthRecord, AthleteGoal, TrainingPlan, ReadinessScore, MLInsight
from app.routes.prediction.service import predict_all 

from . import athlete_bp
from datetime import datetime, timedelta

@athlete_bp.route("/api/dashboard", methods=["GET"])
@jwt_required()
def dashboard_data():
    athlete_id = get_jwt_identity()
    goals_count = AthleteGoal.query.filter_by(athlete_id=athlete_id).count()
    plans_count = TrainingPlan.query.filter_by(athlete_id=athlete_id).count()
    workouts_count = WorkoutLog.query.filter_by(athlete_id=athlete_id).count()

    return jsonify({
        "goals": goals_count,
        "plans": plans_count,
        "workouts": workouts_count
    })


# -------- Dashboard Summary --------
@athlete_bp.route("/summary", methods=["GET"])
@jwt_required()
def athlete_summary():
    user_id = get_jwt_identity()
    athlete = User.query.get(user_id)

    # Goals
    active_goals = athlete.goals.filter_by(status="in progress").count()

    # Plans
    plans = TrainingPlan.query.filter_by(athlete_id=user_id, status="active").count()

    # Workouts this week
    start_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    week_workouts = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == user_id,
        WorkoutLog.date >= start_week
    ).count()

    # -------- Readiness (من الـ ML Model) --------
    hr = HealthRecord.query.filter_by(athlete_id=user_id).order_by(HealthRecord.recorded_at.desc()).first()
    last_log = WorkoutLog.query.filter_by(athlete_id=user_id).order_by(WorkoutLog.date.desc()).first()

    features = {
        "heart_rate": hr.heart_rate if (hr and hr.heart_rate is not None) else 0,
        "sleep_hours": hr.sleep_hours if (hr and hr.sleep_hours is not None) else 0,
        "dietary_intake": 0,  
        "training_days_per_week": 0,
        "recovery_days_per_week": 0,
        "Heart_Rate_(HR)": last_log.metrics.get("hr") if (last_log and "hr" in last_log.metrics) else 0,
        "Muscle_Tension_(MT)": last_log.metrics.get("mt") if (last_log and "mt" in last_log.metrics) else 0,
        "Training_Intensity_(TI)": last_log.session_type if (last_log and last_log.session_type) else "Unknown",
        "Training_Duration_(TD)": last_log.duration if (last_log and last_log.duration is not None) else 0,
        "Training_Type_(TT)": last_log.workout_details.get("type") if (last_log and last_log.workout_details) else "Unknown",
        "Time_Interval_(TI)": last_log.workout_details.get("time") if (last_log and last_log.workout_details) else "Unknown",
        "Phase_of_Training_(PT)": "Unknown"
    }


    try:
        readiness_data = predict_all(features)
        readiness_value = (
            readiness_data.get("injury_severity_prediction") or
            readiness_data.get("performance_class") or "--"
        )
    except Exception as e:
        readiness_value = f"Error: {str(e)}"

    # -------- Return --------
    return jsonify({
        "active_goals": active_goals,
        "plans": plans,
        "week_workouts": week_workouts,
        "readiness": readiness_value
    })


# -------- Recent Workouts --------
@athlete_bp.route("/athlete/workouts", methods=["GET"])
@jwt_required()
def athlete_workouts():
    user_id = get_jwt_identity()
    limit = int(request.args.get("limit", 5))
    workouts = WorkoutLog.query.filter_by(athlete_id=user_id)\
        .order_by(WorkoutLog.date.desc())\
        .limit(limit).all()

    return jsonify([
        {
            "id": w.id,
            "title": w.title,
            "type": w.type,
            "date": w.date.isoformat(),
            "intensity": w.intensity
        } for w in workouts
    ])

# -------- Active Goals --------
@athlete_bp.route("/athlete/goals", methods=["GET"])
@jwt_required()
def athlete_goals():
    user_id = get_jwt_identity()
    status = request.args.get("status", "active")

    goals = AthleteGoal.query.filter_by(athlete_id=user_id)
    if status == "active":
        goals = goals.filter(AthleteGoal.deadline >= date.today())
    goals = goals.order_by(AthleteGoal.deadline).all()

    return jsonify([
        {
            "id": g.id,
            "title": g.title,
            "due_date": g.deadline.isoformat() if g.deadline else None,
            "progress": (g.current_value / g.target_value * 100) if g.target_value else 0
        } for g in goals
    ])
    



@athlete_bp.route("/readiness", methods=["GET"])
@jwt_required()
def athlete_readiness():
    user_id = get_jwt_identity()

    hr = HealthRecord.query.filter_by(athlete_id=user_id).order_by(HealthRecord.recorded_at.desc()).first()
    last_log = WorkoutLog.query.filter_by(athlete_id=user_id).order_by(WorkoutLog.date.desc()).first()

    features = {
        "heart_rate": hr.heart_rate if hr else 70,
        "sleep_hours": hr.sleep_hours if hr else 7,
        "dietary_intake": 3,
        "training_days_per_week": 4,
        "recovery_days_per_week": 2,
        "Heart_Rate_(HR)": last_log.metrics.get("hr", 75) if last_log else 75,
        "Muscle_Tension_(MT)": last_log.metrics.get("mt", 0.5) if last_log else 0.5,
        "Training_Intensity_(TI)": last_log.session_type if last_log else "Medium",
        "Training_Duration_(TD)": last_log.duration if last_log else 30,
        "Training_Type_(TT)": last_log.workout_details.get("type","Cardio") if last_log else "Cardio",
        "Time_Interval_(TI)": last_log.workout_details.get("time","Morning") if last_log else "Morning",
        "Phase_of_Training_(PT)": "Build"
    }

    try:
        result = predict_all(features)  # استدعاء الموديل مباشرة
    except Exception as e:
        result = {"error": str(e)}

    return jsonify(result)
